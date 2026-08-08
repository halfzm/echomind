#!/usr/bin/env python3
"""
simp-skill API 封装
将 /simp 命令封装为可直接调用的 Python 函数
"""

import json
import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


# ============================================================
# 数据结构
# ============================================================
@dataclass
class CrushProfile:
    """心上人档案"""

    name: str
    slug: str
    created_at: str
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    mbti: Optional[str] = None


@dataclass
class AnalysisResult:
    """分析结果"""

    stage: str  # 当前阶段: 认识期/暧昧期/热恋期/危机期
    signals: List[str]  # 识别到的信号
    score: int  # 感情温度 (0-100)
    advice: str  # 建议


# ============================================================
# 配置
# ============================================================

DATA_DIR = Path("./relations")
DATA_DIR.mkdir(exist_ok=True)


def _get_crush_dir(slug: str) -> Path:
    """获取心上人数据目录"""
    return DATA_DIR / slug


def _ensure_crush_dir(slug: str) -> Path:
    """确保心上人目录存在"""
    path = _get_crush_dir(slug)
    path.mkdir(parents=True, exist_ok=True)
    (path / "memories").mkdir(exist_ok=True)
    (path / "memories" / "chats").mkdir(exist_ok=True)
    (path / "memories" / "social").mkdir(exist_ok=True)
    (path / "memories" / "photos").mkdir(exist_ok=True)
    (path / "versions").mkdir(exist_ok=True)
    (path / "snapshots").mkdir(exist_ok=True)
    return path


# ============================================================
# 核心命令封装
# ============================================================


def create(name, mbti, relation_stage, description) -> CrushProfile:
    """
    建立心上人档案
    对应命令: /simp create <名字>

    Args:
        name: 心上人名字
        mbti: MBTI 类型
        relation_stage: 关系阶段
        description: 描述信息,写下对方性格特征
        chats: 聊天记录

    Returns:
        CrushProfile: 创建的档案对象

    Example:
        >>> profile = create("小美", mbti="ENFJ", relation_stage="认识期", description="部门新来的同事")
    """
    slug = _generate_slug(name)
    path = _ensure_crush_dir(slug)

    profile = CrushProfile(
        name=name,
        slug=slug,
        created_at=datetime.now().isoformat(),
        tags=[],
        notes=description,
    )

    now = datetime.now()
    # 写入 profile.md
    with open(path / "profile.md", "w", encoding="utf-8") as f:
        f.write(
            f"---\n"
            f"nickname: {name}\n"
            f"slug: {slug}\n"
            f'gender: "[待填写]"\n'
            f'age: "[待填写]"\n'
            f'occupation: "[待填写]"\n'
            f'city: "[待填写]"\n'
            f"mbti: {mbti}\n"
            f'zodiac: "[待填写]"\n'
            f'personality_type: "[感性型/理性型/傲娇型/温柔型]"\n'
            f'how_met: "[待填写]"\n'
            f"created_at: \"{now.strftime('%Y-%m-%d')}\"\n"
            f"---\n\n"
            f"## 性格画像\n\n"
            f"[在这里描述ta的性格特征]\n\n"
            f"## 最打动ta的方式\n\n"
            f"[基于性格分析，什么样的话/行为最有效]\n\n"
            f"## 用户自身风格\n\n"
            f"[用户的说话风格、消息习惯、偏好模式]\n\n"
            f"## 注意事项\n\n"
            f"[ta特别在意或反感的事]\n"
        )

    # 初始化 state.md
    with open(path / "state.md", "w", encoding="utf-8") as f:
        f.write(
            f"---\n"
            f"current_stage: {relation_stage}\n"
            f"signal_score: null\n"
            f"last_signal_score: null\n"
            f"score_trend: stable\n"
            f"recommended_mode: hybrid\n"
            f"last_updated: \"{now.strftime('%Y-%m-%dT%H:%M:%S')}\"\n"
            f"milestones_done: 0\n"
            f"---\n\n"
            f"## 当前状态（一句话）\n\n"
            f"[运行 /simp analyze 后自动生成]\n\n"
            f"## 最近信号（最新3条）\n\n"
            f"[暂无信号记录]\n\n"
            f"## 当前策略方向\n\n"
            f"[运行 /simp analyze 后生成]\n\n"
            f"## 下一步建议\n\n"
            f"[运行 /simp analyze 后生成]\n",
        )

    # 初始化 events.jsonl
    with open(path / "events.jsonl", "w", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "type": "profile_created",
                    "timestamp": profile.created_at,
                    "name": name,
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    # 初始化 strategy.md
    with open(path / "strategy.md", "w", encoding="utf-8") as f:
        f.write(
            f"# 追求策略\n\n"
            f"> 由 simp-skill 生成  |  最后更新：{now.strftime('%Y-%m-%d')}\n\n"
            f"## 当前阶段\n\n"
            f"[待评估]\n\n"
            f"## 推荐模式\n\n"
            f"[纯情模式/策略模式/混合模式]\n\n"
            f"## 本阶段重点\n\n"
            f"[待生成]\n\n"
            f"## 近期行动计划\n\n"
            f"[待生成]\n",
        )

    # 初始化 events.jsonl
    with open(path / "meta.json", "w", encoding="utf-8") as f:
        meta = {
            "slug": slug,
            "nickname": name,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "version": "v1",
            "current_stage": relation_stage,
            "signal_score": None,
            "mode": "hybrid",
            "event_count": 0,
            "last_snapshot": None,
            "interaction_count": 0,
            "last_interaction": None,
            "consecutive_days": 0,
        }
        f.write(json.dumps(meta, ensure_ascii=False, indent=2))

        logger.info("✅ 档案目录创建成功：%s/", path)
        logger.info("   ├── profile.md     （心上人基本信息）")
        logger.info("   ├── state.md       （当前状态快照）")
        logger.info("   ├── events.jsonl   （事件日志）")
        logger.info("   ├── strategy.md    （追求策略）")
        logger.info("   ├── meta.json      （元数据）")
        logger.info("   ├── snapshots/     （定期快照）")
        logger.info("   └── memories/")
        logger.info("       ├── chats/     （放聊天记录）")
        logger.info("       ├── social/    （放社交媒体截图）")
        logger.info("       └── photos/    （放照片）")
        logger.info("")
        logger.info("下一步：")
        logger.info("  1. 编辑 %s/profile.md 填写心上人信息", path)
        logger.info("  2. 运行 /simp analyze 开始分析信号")
        logger.info(
            "  3. 把聊天记录放到 %s/memories/chats/ 并运行 chat_parser.py", path
        )

    return profile


def analyze(slug: str, context: Optional[str] = None) -> AnalysisResult:
    """
    解读信号，判断当前阶段
    对应命令: /simp analyze [描述]

    Args:
        slug: 心上人的 slug
        context: 可选的情境描述（聊天记录、近期互动等）

    Returns:
        AnalysisResult: 分析结果

    Example:
        >>> result = analyze("xiaomei", "她昨天主动给我发了晚安，今天又没消息了")
    """
    path = _get_crush_dir(slug)
    if not path.exists():
        raise ValueError(f"未找到档案: {slug}，请先运行 create()")

    # 读取现有档案
    profile = _load_profile(slug)

    # TODO: 这里应该调用 LLM 进行实际分析
    # 当前为示例实现
    signals = (
        ["对方主动发起对话"] if context and "主动" in context else ["暂无明确信号"]
    )
    stage = _infer_stage(signals)

    result = AnalysisResult(
        stage=stage,
        signals=signals,
        score=50 if stage == "暧昧期" else 30,
        advice=_generate_advice(stage, signals),
    )

    # 更新 state.md
    _update_state(slug, result)

    # 记录事件
    _append_event(
        slug,
        "analysis",
        {"stage": result.stage, "signals": result.signals, "score": result.score},
    )

    return result


def message(slug: str, situation: str, style: str = "hybrid") -> str:
    """
    生成情境专属消息/情话
    对应命令: /simp message <情境>

    Args:
        slug: 心上人的 slug
        situation: 当前情境描述
        style: 风格，可选 "sweet"(纯情), "strategic"(策略), "hybrid"(混合)

    Returns:
        str: 生成的消息内容

    Example:
        >>> msg = message("xiaomei", "她今天生病了", style="sweet")
        >>> print(msg)
        "听说你生病了，好心疼... 记得多喝热水，如果难受随时找我"
    """
    path = _get_crush_dir(slug)
    if not path.exists():
        raise ValueError(f"未找到档案: {slug}")

    profile = _load_profile(slug)

    # TODO: 调用 LLM 生成消息
    # 当前为示例实现
    templates = {
        "sweet": [
            f"你最近还好吗？我有点想你了。",
            f"听说{situation}，我一直在想你。",
        ],
        "strategic": [
            f"刚才看到{situation}，突然想到你。",
            f"你上次说的那件事，我想了很久。",
        ],
        "hybrid": [
            f"你还好吗？看到{situation}让我想起了你。",
            f"其实我一直在想，{situation}的时候你会在做什么。",
        ],
    }

    import random

    msgs = templates.get(style, templates["hybrid"])
    msg = random.choice(msgs)

    # 记录事件
    _append_event(
        slug,
        "message_generated",
        {"situation": situation, "style": style, "message": msg},
    )

    return msg


def confess(slug: str) -> Dict[str, Any]:
    """
    表白策略 + 表白词定制
    对应命令: /simp confess

    Args:
        slug: 心上人的 slug

    Returns:
        Dict: 包含策略和表白词

    Example:
        >>> result = confess("xiaomei")
        >>> print(result["strategy"])
        >>> print(result["words"])
    """
    path = _get_crush_dir(slug)
    if not path.exists():
        raise ValueError(f"未找到档案: {slug}")

    profile = _load_profile(slug)

    # TODO: 调用 LLM 生成表白策略
    # 当前为示例实现
    result = {
        "strategy": f"建议选择一个安静、私密的环境，当面表白。时机建议在你们相处愉快、氛围融洽的时候。",
        "words": f"{profile.name}，其实从认识你开始，我就一直很想告诉你——我喜欢你。不是一时冲动，而是越来越确定。",
        "tips": [
            "眼神要真诚，不要躲闪",
            "说完后给对方思考的空间，不要催促",
            "无论结果如何，都要保持风度",
        ],
    }

    # 记录事件
    _append_event(slug, "confess_prepared", {"words": result["words"][:50] + "..."})

    return result


def crisis(slug: str, situation: str) -> Dict[str, Any]:
    """
    危机处理
    对应命令: /simp crisis <情况>

    Args:
        slug: 心上人的 slug
        situation: 危机情况描述

    Returns:
        Dict: 包含危机类型、分析和应对方案

    Example:
        >>> result = crisis("xiaomei", "突然不回我消息了")
        >>> print(result["plan"])
    """
    path = _get_crush_dir(slug)
    if not path.exists():
        raise ValueError(f"未找到档案: {slug}")

    # TODO: 调用 LLM 分析危机
    # 当前为示例实现
    crisis_types = {
        "不回消息": {
            "type": "C-2",
            "analysis": "突然冷落/已读不回，可能对方在忙，也可能需要空间",
            "plan": "1. 停止追问，给对方空间\n2. 观察24-48小时\n3. 如果还没回复，发一条轻松的话题重新出现",
        },
        "被拒绝": {
            "type": "C-1",
            "analysis": "明确被拒，需要尊重对方选择",
            "plan": "1. 优雅接受，不纠缠\n2. 给自己一段时间调整\n3. 如果放不下，三个月后可以尝试重新建立联系",
        },
    }

    # 简单匹配
    result = None
    for key, value in crisis_types.items():
        if key in situation:
            result = value
            break

    if not result:
        result = {
            "type": "C-通用",
            "analysis": f"情况: {situation}。需要更多信息来判断危机类型。",
            "plan": "建议先冷静观察，不要急于行动。",
        }

    # 记录事件
    _append_event(
        slug, "crisis_handled", {"situation": situation, "crisis_type": result["type"]}
    )

    return result


def progress(slug: str) -> Dict[str, Any]:
    """
    进度评估与下一步建议
    对应命令: /simp progress

    Args:
        slug: 心上人的 slug

    Returns:
        Dict: 包含当前进度、分数和下一步建议

    Example:
        >>> result = progress("xiaomei")
        >>> print(result["stage"])
        >>> print(result["next_step"])
    """
    path = _get_crush_dir(slug)
    if not path.exists():
        raise ValueError(f"未找到档案: {slug}")

    # 读取 state.md 获取当前状态
    state_path = path / "state.md"
    if state_path.exists():
        with open(state_path, "r", encoding="utf-8") as f:
            content = f.read()
            # 简单解析
            stage = _extract_field(content, "阶段")
            score = _extract_field(content, "感情温度")
    else:
        stage = "认识期"
        score = "0/100"

    # TODO: 更精确的进度分析
    result = {
        "stage": stage or "认识期",
        "score": score or "0/100",
        "milestones": [
            "已建立档案",
            "已发送消息" if _has_events(slug) else "尚未发送消息",
        ],
        "next_step": "建议多创造互动机会，了解对方的兴趣和生活方式。",
    }

    return result


def quit(slug: str) -> Dict[str, Any]:
    """
    放弃判断器
    对应命令: /simp quit

    Args:
        slug: 心上人的 slug

    Returns:
        Dict: 包含分析和建议

    Example:
        >>> result = quit("xiaomei")
        >>> print(result["verdict"])
    """
    path = _get_crush_dir(slug)
    if not path.exists():
        raise ValueError(f"未找到档案: {slug}")

    # TODO: 调用 LLM 判断是否该放弃
    result = {
        "verdict": "需要更多信息来判断。建议回顾一下整体互动情况。",
        "indicators": [
            "对方是否主动联系你？",
            "你们的互动是否让你感到疲惫？",
            "你是在追求一段关系，还是在追逐一个幻想？",
        ],
        "advice": "如果三个问题中两个以上答案让你不安，建议给自己一些距离重新思考。",
    }

    return result


def mode(style: str) -> str:
    """
    切换风格模式
    对应命令: /simp mode sweet | strategic | hybrid

    Args:
        style: "sweet" | "strategic" | "hybrid"

    Returns:
        str: 切换结果

    Example:
        >>> mode("sweet")
        '已切换到纯情模式'
    """
    valid = ["sweet", "strategic", "hybrid"]
    if style not in valid:
        raise ValueError(f"无效模式: {style}，可选: {valid}")

    # 保存到全局配置
    config_path = DATA_DIR / ".config.json"
    config = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

    config["mode"] = style
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    return f"已切换到{ {'sweet':'纯情','strategic':'策略','hybrid':'混合'}.get(style, style) }模式"


# ============================================================
# 辅助函数
# ============================================================


def _generate_slug(name: str) -> str:
    """生成 slug"""
    import hashlib

    # 简单实现：拼音或 hash
    return hashlib.md5(name.encode()).hexdigest()[:8]


def _load_profile(slug: str) -> CrushProfile:
    """加载档案"""
    path = _get_crush_dir(slug) / "profile.md"
    if not path.exists():
        raise ValueError(f"档案不存在: {slug}")

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 解析 YAML frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1])
            return CrushProfile(
                name=frontmatter.get("name", slug),
                slug=frontmatter.get("slug", slug),
                created_at=frontmatter.get("created_at", datetime.now().isoformat()),
                tags=frontmatter.get("tags", []),
                mbti=frontmatter.get("mbti"),
                notes=parts[2].strip(),
            )

    return CrushProfile(name=slug, slug=slug, created_at=datetime.now().isoformat())


def _update_state(slug: str, result: AnalysisResult) -> None:
    """更新状态文件"""
    path = _get_crush_dir(slug) / "state.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"""# 当前状态

- 阶段: {result.stage}
- 感情温度: {result.score}/100
- 最近信号: {', '.join(result.signals)}
- 下一步建议: {result.advice}
""")


def _append_event(slug: str, event_type: str, data: Dict) -> None:
    """追加事件到 events.jsonl"""
    path = _get_crush_dir(slug) / "events.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {"type": event_type, "timestamp": datetime.now().isoformat(), **data}
            )
            + "\n"
        )


def _infer_stage(signals: List[str]) -> str:
    """根据信号推断阶段"""
    # 简单实现
    if not signals or signals == ["暂无明确信号"]:
        return "认识期"
    if "对方主动" in str(signals) or "暧昧" in str(signals):
        return "暧昧期"
    return "认识期"


def _generate_advice(stage: str, signals: List[str]) -> str:
    """生成建议"""
    advice_map = {
        "认识期": "先多了解对方，找到共同话题，建立舒适的互动节奏。",
        "暧昧期": "可以适当推进关系，增加单独见面的机会，观察对方反应。",
        "热恋期": "保持真诚和温度，但也要给彼此空间。",
        "危机期": "先冷静分析问题所在，再决定如何应对。",
    }
    return advice_map.get(stage, "保持真诚，慢慢来。")


def _extract_field(content: str, field: str) -> Optional[str]:
    """从 markdown 中提取字段值"""
    for line in content.split("\n"):
        if line.startswith(f"- {field}:"):
            return line.split(":", 1)[1].strip()
        if line.startswith(f"- {field}"):
            return line.split(":", 1)[1].strip() if ":" in line else None
    return None


def _has_events(slug: str) -> bool:
    """检查是否有事件记录"""
    path = _get_crush_dir(slug) / "events.jsonl"
    if not path.exists():
        return False
    with open(path, "r", encoding="utf-8") as f:
        return bool(f.read().strip())


def sefie(name, mbti, pros, cons):
    """创建用户自身档案"""
    slug = _generate_slug(name)

    now = datetime.now()

    profile = {
        "name": name,
        "slug": slug,
        "mbti": mbti.upper() if mbti else "未知",
        "strengths": pros,
        "weaknesses": cons,
        "created_at": now.strftime("%Y-%m-%d"),
    }

    # 写入 profile.md
    with open(DATA_DIR / "selfie.json", "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    return profile


# ============================================================
# 统一 API 类（推荐使用）
# ============================================================


class SimpSkill:
    """
    simp-skill 统一 API

    Usage:
        >>> skill = SimpSkill()
        >>> profile = skill.create("小美", tags=["同事"])
        >>> result = skill.analyze("xiaomei", "她今天主动找我聊天了")
        >>> msg = skill.message("xiaomei", "她今天心情不好")
    """

    def __init__(self, data_dir: str = "./relations"):
        global DATA_DIR
        DATA_DIR = Path(data_dir)
        DATA_DIR.mkdir(exist_ok=True)

    def selfie(self, name: str, mbti: str, pros: str, cons: str) -> CrushProfile:
        """创建用户自身档案"""
        return sefie(name, mbti, pros, cons)

    def create(
        self, name: str, mbti: str, relation_stage: str, description: str
    ) -> CrushProfile:
        return create(name, mbti, relation_stage, description)

    def analyze(self, slug: str, context: Optional[str] = None) -> AnalysisResult:
        return analyze(slug, context)

    def message(self, slug: str, situation: str, style: str = "hybrid") -> str:
        return message(slug, situation, style)

    def confess(self, slug: str) -> Dict[str, Any]:
        return confess(slug)

    def crisis(self, slug: str, situation: str) -> Dict[str, Any]:
        return crisis(slug, situation)

    def progress(self, slug: str) -> Dict[str, Any]:
        return progress(slug)

    def quit(self, slug: str) -> Dict[str, Any]:
        return quit(slug)

    def mode(self, style: str) -> str:
        return mode(style)

    def list_all(self) -> List[str]:
        """列出所有心上人档案"""
        return [
            d.name
            for d in DATA_DIR.iterdir()
            if d.is_dir() and (d / "profile.md").exists()
        ]


if __name__ == "__main__":
    # from simp_api import SimpSkill

    # 初始化
    skill = SimpSkill()

    # 1. 建立档案
    profile = skill.create("小美", tags=["同事", "ENFJ"], notes="部门新来的产品经理")
    print(f"已创建档案: {profile.name} (slug: {profile.slug})")

    # # 2. 分析信号
    # result = skill.analyze("xiaomei", "她昨天主动给我发了工作相关的消息，还加了表情")
    # print(f"当前阶段: {result.stage}")
    # print(f"信号: {result.signals}")
    # print(f"建议: {result.advice}")

    # # 3. 生成消息
    # msg = skill.message("xiaomei", "她今天生病了", style="sweet")
    # print(f"生成的消息: {msg}")

    # # 4. 查看进度
    # progress = skill.progress("xiaomei")
    # print(f"进度: {progress['stage']}, 分数: {progress['score']}")

    # # 5. 危机处理
    # crisis_plan = skill.crisis("xiaomei", "突然不回我消息了")
    # print(f"危机类型: {crisis_plan['type']}")
    # print(f"应对方案: {crisis_plan['plan']}")

    # # 6. 表白准备
    # confession = skill.confess("xiaomei")
    # print(f"表白策略: {confession['strategy']}")
    # print(f"表白词: {confession['words']}")

    # # 7. 切换模式
    # skill.mode("sweet")
