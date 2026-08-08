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


class TimelineItem(BaseModel):
    date: str
    title: str
    desc: str
    tag: str


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
    status: str
    mbti: str
    tags: List[str]
    personalityDesc: str
    heatScore: int
    defensiveLevel: int
    timeline: List[TimelineItem]
    chatHistory: List[ChatMessage]
    attachments: Optional[List[Attachment]] = []
