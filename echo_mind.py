#!/usr/bin/env python3
import json
import logging
from pathlib import Path
from typing import Any, List, Dict
from dataclasses import asdict
from datetime import datetime, timezone

from utils import parse_json_from_text
from models import CrushProfile, AnalysisResult

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


# ============================================================
# EchoMind 类 - 所有功能封装
# ============================================================
class EchoMind:
    """
    EchoMind 统一 API
    """

    def __init__(self, data_dir: str = "./relations"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # ---------- 私有辅助方法 ----------
    def _get_crush_dir(self, slug: str) -> Path:
        """获取心上人数据目录"""
        return self.data_dir / slug

    def _ensure_crush_dir(self, slug: str) -> Path:
        """确保心上人目录存在"""
        path = self._get_crush_dir(slug)
        path.mkdir(parents=True, exist_ok=True)
        (path / "memories").mkdir(exist_ok=True)
        (path / "analysis").mkdir(exist_ok=True)
        return path

    def _generate_slug(self, name: str) -> str:
        """生成 slug"""
        import hashlib

        return hashlib.md5(name.encode()).hexdigest()[:8]

    def _update_state(self, slug: str, result: AnalysisResult) -> None:
        """更新状态文件"""
        path = self._get_crush_dir(slug) / "state.md"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"""# 当前状态
                - 阶段: {result.stage}
                - 感情温度: {result.score}/100
                - 最近信号: {', '.join(result.signals)}
                - 下一步建议: {result.advice}
                """)

    def _append_event(self, slug: str, title: str, desc: str, data: dict) -> None:
        """追加事件到 events.jsonl"""
        path = self._get_crush_dir(slug) / "events.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                        "title": title,
                        "desc": desc,
                        **data,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    def _infer_stage(self, signals: List[str]) -> str:
        """根据信号推断阶段"""
        if not signals or signals == ["暂无明确信号"]:
            return "认识期"
        if "对方主动" in str(signals) or "暧昧" in str(signals):
            return "暧昧期"
        return "认识期"

    def _generate_advice(self, stage: str) -> str:
        """生成建议"""
        advice_map = {
            "认识期": "先多了解对方，找到共同话题，建立舒适的互动节奏。",
            "暧昧期": "可以适当推进关系，增加单独见面的机会，观察对方反应。",
            "热恋期": "保持真诚和温度，但也要给彼此空间。",
            "危机期": "先冷静分析问题所在，再决定如何应对。",
        }
        return advice_map.get(stage, "保持真诚，慢慢来。")

    # ---------- 公共 API 方法 ----------
    def get_slug(self, name):
        return self._generate_slug(name=name)

    def selfie(self, name: str, mbti: str, pros: str, cons: str) -> Dict[str, Any]:
        """创建用户自身档案"""
        slug = self._generate_slug(name)
        now = datetime.now(tz=timezone.utc)

        profile = {
            "name": name,
            "slug": slug,
            "mbti": mbti.upper() if mbti else "未知",
            "strengths": pros,
            "weaknesses": cons,
            "created_at": now.strftime("%Y-%m-%d"),
        }
        try:
            with open(self.data_dir / "selfie.json", "w", encoding="utf-8") as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(e)

        return profile

    def create(
        self,
        name: str,
        relation_stage: str,
        gender: str = "",
        age: str = "",
        occupation: str = "",
        city: str = "",
        mbti: str = "",
        personality_type: str = "",
        how_met: str = "",
        traits: str = "",
        attraction_tips: str = "",
        notes: str = "",
    ) -> CrushProfile:
        """
        建立心上人档案
        """
        slug = self._generate_slug(name)
        path = self._ensure_crush_dir(slug)

        profile = CrushProfile(
            name=name,
            slug=slug,
            gender=gender,
            age=age,
            occupation=occupation,
            city=city,
            mbti=mbti,
            personality_type=personality_type,
            how_met=how_met,
            traits=traits,
            attraction_tips=attraction_tips,
            notes=notes,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
        )

        now = datetime.now(tz=timezone.utc)
        # 写入 profile.md
        with open(path / "profile.md", "w", encoding="utf-8") as f:
            f.write(
                f"---\n"
                f"nickname: {name}\n"
                f"slug: {slug}\n"
                f"gender: {gender}\n"
                f"age: {age}\n"
                f"occupation: {occupation}\n"
                f"city: {city}\n"
                f"mbti: {mbti}\n"
                f"personality_type: {personality_type}\n"
                f"how_met: {how_met}\n"
                f"created_at: \"{now.strftime('%Y-%m-%d')}\"\n"
                f"---\n\n"
                f"## 性格画像\n\n"
                f"{traits}\n\n"
                f"## 最打动ta的方式\n\n"
                f"{attraction_tips}\n\n"
                f"## 注意事项\n\n"
                f"{notes}\n"
            )
        with open(path / "profile.json", "w", encoding="utf-8") as f:
            json.dump(asdict(profile), f, ensure_ascii=False, indent=2)

        # 初始化 events.jsonl
        with open(path / "events.jsonl", "w", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "timestamp": profile.created_at,
                        "title": "profile_created",
                        "desc": f"创建{name}档案",
                        "tag": "里程碑",
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

        logger.info("✅ 档案目录创建成功：%s/", path)
        logger.info("   ├── profile.md     （心上人基本信息）")
        logger.info("   ├── events.jsonl   （事件日志）")
        logger.info("   └── memories/      （放聊天记录）")

        return profile

    def analyze(self, name: str, ai_reply_message) -> AnalysisResult:
        """
        解读信号，判断当前阶段
        根据ai回复，更新部分结果

        Args:
            name: 心上人的 name
            ai_reply_message: ai给出的回复

        Returns:
            AnalysisResult: 分析结果
        """
        slug = self._generate_slug(name)
        path = self._get_crush_dir(slug)
        if not path.exists():
            raise ValueError(f"未找到档案: {slug}，请先运行 create()")
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_{timestamp}.json"
        filepath = path / "analysis" / filename

        parsed = parse_json_from_text(ai_reply_message)
        record = {
            "timestamp": timestamp,
            "persona_name": name,
            "subtext": parsed.get("subtext", ""),
            "plan": parsed.get("plan", ""),
            "raw_response": ai_reply_message,
        }
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            print(f"[Analyze] 分析结果已保存: {filepath}")
        except Exception as e:
            print(f"[Analyze] 保存文件失败: {e}")
            return

        # TODO 读取现有档案 state.json, profile.json, personas.json进行更新
        # with open(path/"state.json", "r", encoding="utf-8") as f:
        #     state = json.load(f)

        signals = ["暂无明确信号"]
        stage = self._infer_stage(signals)

        result = AnalysisResult(
            stage=stage,
            signals=signals,
            score=50 if stage == "暧昧期" else 30,
            advice=self._generate_advice(stage),
        )

        # 更新 state.md
        self._update_state(slug, result)

        # 记录事件
        self._append_event(
            slug,
            "analysis",
            "解读聊天记录",
            {"stage": result.stage, "signals": result.signals, "score": result.score},
        )

        return result

    def get_timeline(self, name: str):
        slug = self._generate_slug(name)
        timeline_fp = self._get_crush_dir(slug) / "events.jsonl"
        timelines = timeline_fp.read_text(encoding="utf-8").splitlines()
        timeline_data = [d.strip() for d in timelines if d.strip()]
        return timeline_data

    def edit_timeline(self, name: str, title: str, desc: str, data: Dict):
        slug = self._generate_slug(name)
        self._append_event(slug, title, desc, data)


# ============================================================
# 使用示例
# ============================================================
if __name__ == "__main__":
    # 初始化
    skill = EchoMind()

    skill._append_event("60ae073f", "a", "b", {"tag": "test"})

    # skill.selfie(
    #     name="myself",
    #     mbti="enfp",
    #     pros="善于同理与倾听，逻辑清晰，富有幽默感和洞察力",
    #     cons="面对冷漠回复容易产生情绪内耗，边界感较弱，过于追求完美沟通",
    # )

    # 1. 建立档案（注意参数顺序：name, mbti, relation_stage, description, tags可选）
    # profile = skill.create(
    #     name="小雨",
    #     relation_stage="认识期",
    #     gender="女",
    #     age="23",
    #     occupation="设计师",
    #     city="上海",
    #     mbti="ENFP",
    #     personality_type="感性型",
    #     how_met="同学介绍",
    #     traits="ta 话很多，喜欢用颜文字，情绪外露，容易被细节打动。\n见面时会不自觉靠近，但如果感觉被冷落会直接不回消息。",
    #     attraction_tips='具体的画面感 > 泛泛的夸奖。说"你刚才皱眉的样子"比"你很可爱"更有效。',
    #     notes='ta 对"套路感"敏感，一旦感觉被设计会直接拉远距离。',
    # )
    # print(f"已创建档案: {profile.name} (slug: {profile.slug})")
