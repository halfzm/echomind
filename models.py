'''
各种用到的数据结构
'''
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class SelfieRequest(BaseModel):
    name: str
    mbti: str
    strengths: str
    weaknesses: str


class TimelineEvent(BaseModel):
    name: str          # 关系人姓名
    title: str         # 事件标题
    desc: Optional[str] = ""   # 详细信息，可选
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
