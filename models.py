"""
各种用到的数据结构
"""

from enum import Enum
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone


class SelfieRequest(BaseModel):
    name: str
    mbti: str
    strengths: str
    weaknesses: str


class TimelineEvent(BaseModel):
    name: str  # 关系人姓名
    title: str  # 事件标题
    desc: Optional[str] = ""  # 详细信息，可选
    data: Optional[str] = "里程碑"  # 标签，默认里程碑


class ChatMessage(BaseModel):
    sender: str
    text: str
    image: Optional[str] = None
    audio: Optional[str] = None
    file: Optional[str] = None


class Attachment(BaseModel):
    name: str
    type: str
    data: str  # 文本内容或 DataURL


class Persona(BaseModel):
    id: str
    name: str
    avatar: str
    status: str  # 关系阶段: 暗恋中/追求中/交往中/已分手/前任

    # 新增 CrushProfile 字段
    gender: Optional[str] = ""
    age: Optional[str] = ""
    occupation: Optional[str] = ""
    city: Optional[str] = ""
    mbti: str = "未知"
    personality_type: str = "感性型"
    how_met: Optional[str] = ""
    traits: Optional[str] = ""  # 性格画像
    attraction_tips: Optional[str] = ""  # 最打动ta的方式
    notes: Optional[str] = ""  # 注意事项

    # 原有字段（保留兼容）
    personalityDesc: Optional[str] = ""  # 可作为 traits 或 notes 的组合
    tags: List[str] = []
    heatScore: int = 0
    defensiveLevel: int = 100
    timeline: List[Dict[str, Any]] = []
    chatHistory: List[Dict[str, Any]] = []
    attachments: List[Dict[str, Any]] = []  # 处理后的附件（文件名）


# ---------- 枚举定义 ----------
class PersonalityType(Enum):
    EMOTIONAL = "感性型"
    RATIONAL = "理性型"
    TSUNDERE = "傲娇型"
    GENTLE = "温柔型"


class Stage(str, Enum):
    """关系阶段枚举"""

    ICEBREAK = "破冰期"
    WARMING = "升温期"
    FLIRTING = "暧昧期"
    PRE_CONFESS = "表白前"
    CONFESS_SUCCESS = "表白后-成功"
    CONFESS_REJECTED = "表白后-被拒"
    FRIEND_ZONE = "友谊区"
    RESTART = "重启期"


class Trend(str, Enum):
    """分数趋势枚举"""

    UP = "up"
    DOWN = "down"
    STABLE = "stable"


@dataclass
class CrushProfile:
    """心上人档案，对应 profile.md 文件。"""

    name: str = ""  # 昵称
    slug: str = ""  # 唯一标识
    gender: str = ""  # 性别
    age: str = ""  # 年龄
    occupation: str = ""  # 职业
    city: str = ""  # 城市
    mbti: str = ""  # MBTI 类型
    personality_type: str = "感性型"  # 性格类型
    how_met: str = ""  # 认识途径
    traits: str = ""  # ## 性格画像
    attraction_tips: str = ""  # ## 最打动ta的方式
    notes: str = ""  # ## 注意事项
    created_at: str = field(
        default_factory=lambda: datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    )


@dataclass
class Strategy:
    current_stage: str = ""  # ## 当前阶段
    recommended_mode: str = ""  # ## 推荐模式
    stage_focus: str = ""  # ## 本阶段重点
    action_plan: str = ""  # ## 近期行动计划


@dataclass
class AnalysisResult:
    """分析结果"""

    stage: str  # 当前阶段: 认识期/暧昧期/热恋期/危机期
    signals: List[str]  # 识别到的信号
    score: int  # 感情温度 (0-100)
    advice: str  # 建议
