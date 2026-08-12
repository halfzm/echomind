import os
import json
import uuid
import base64
import shutil
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any

import websockets
from pydantic import BaseModel
from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
    UploadFile,
    File,
    Form,
    Query,
)
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from echo_mind import EchoMind
from utils import load_personas_from_file, save_personas_to_file
from models import SelfieRequest, TimelineEvent, ChatMessage, Attachment, Persona

app = FastAPI()
skill = EchoMind()

DATA_DIR = Path("./relations")
DATA_DIR.mkdir(exist_ok=True)
PERSONAS_FILE = os.path.join(DATA_DIR, "personas.json")

# MiniCPM-o API 地址
API_HOST = "minicpmo45.modelbest.cn"
API_WS_URL = f"wss://{API_HOST}/v1/realtime?mode=chat"

# 启动时加载 Skill 指令
# SYSTEM_INSTRUCTION = load_skill_instructions()
# SYSTEM_INSTRUCTION = "在每次回答的最后面加上一个喵字"

# 挂载静态文件目录，URL 前缀为 /static
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def get_index():
    """返回前端 HTML 页面（也可单独部署）"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/turnbased")
async def get_turnbased():
    """返回前端对话 HTML 页面（也可单独部署）"""
    with open("static/turnbased.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/selfie")
async def get_selfie():
    """获取当前用户的档案，若不存在则返回空"""
    # 查找 profile 目录下的所有 json 文件
    if not DATA_DIR.exists():
        return {"status": "not_found", "profile": None}
    json_files = f"{DATA_DIR}/selfie.json"
    if not Path(json_files).exists():
        return {"status": "not_found", "profile": None}
    with open(json_files, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 转换为前端期望的格式
    return {
        "status": "success",
        "profile": {
            "name": data.get("name", "我"),
            "mbti": data.get("mbti", "未知"),
            "strengths": data.get("strengths", ""),
            "weaknesses": data.get("weaknesses", ""),
        },
    }


@app.post("/selfie")
async def create_profile(requests: SelfieRequest):
    """根据填写的表单，创建用户资料"""
    try:
        # 解析请求数据
        name = requests.name
        mbti = requests.mbti
        strengths = requests.strengths
        weaknesses = requests.weaknesses

        # 调用 skill 创建个人档案
        profile = skill.selfie(name=name, mbti=mbti, pros=strengths, cons=weaknesses)
        print(f"已创建个人档案: {profile.name} (slug: {profile.slug})")
        return {"status": "success", "profile": profile}
    except Exception as e:
        return {"error": str(e)}


@app.get("/persona")
async def get_persona():
    """加载所有已创建的 persona，返回给前端"""
    personas = load_personas_from_file(PERSONAS_FILE)
    return {"personas": personas}


@app.post("/persona")
async def create_persona(persona_data: Dict[str, Any]):
    """
    根据填写信息创建档案，如果有聊天记录则分析聊天记录
    """
    # 读取现有数据
    personas = load_personas_from_file(PERSONAS_FILE)

    # 提取新字段（全部）
    name = persona_data.get("name", "新关系人")
    gender = persona_data.get("gender", "")
    age = persona_data.get("age", "")
    occupation = persona_data.get("occupation", "")
    city = persona_data.get("city", "")
    mbti = persona_data.get("mbti", "未知")
    personality_type = persona_data.get("personality_type", "感性型")
    how_met = persona_data.get("how_met", "")
    status = persona_data.get("status", "暗恋中")
    traits = persona_data.get("traits", "")
    attraction_tips = persona_data.get("attraction_tips", "")
    notes = persona_data.get("notes", "")
    # 原有字段（兼容旧版）
    desc = persona_data.get("personalityDesc", "")

    # 创建档案（此处调用 skill.create，可根据需要扩展参数）
    # 我们传入 notes 合并了 traits + notes 或单独传，视 skill 实现决定
    persona = skill.create(
        name=name,
        relation_stage=status,
        gender=gender,
        age=age,
        occupation=occupation,
        city=city,
        mbti=mbti,
        personality_type=personality_type,
        how_met=how_met,
        traits=traits,
        attraction_tips=attraction_tips,
        notes=notes or desc,  # 如果 notes 为空则使用 desc
    )

    persona_fp = DATA_DIR / f"{persona.slug}/memories"
    persona_fp.mkdir(parents=True, exist_ok=True)  # 确保目录存在

    # 处理附件（保持不变）
    attachments = persona_data.get("attachments", [])
    processed_attachments = []
    for att in attachments:
        orig_name = att.get("name", "unknown")
        att_type = att.get("type", "file")
        content = att.get("data", "")

        ext = os.path.splitext(orig_name)[1]
        if not ext:
            if att_type == "image":
                ext = ".jpg"
            elif att_type == "audio":
                ext = ".wav"
            else:
                ext = ".txt"
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(persona_fp, filename)

        if att_type in ("image", "audio"):
            if content.startswith("data:"):
                header, encoded = content.split(",", 1)
                if "base64" in header:
                    binary_data = base64.b64decode(encoded)
                else:
                    binary_data = encoded.encode()
            else:
                binary_data = content.encode()
            with open(filepath, "wb") as f:
                f.write(binary_data)
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

        processed_attachments.append(
            {
                "name": orig_name,
                "type": att_type,
                "data": filename,  # 存储文件名
            }
        )

    # 构建 Persona 对象（包含所有新字段）
    new_id = "p_" + str(uuid.uuid4())[:8]
    new_persona = Persona(
        id=new_id,
        name=name,
        avatar=persona_data.get("avatar", "默认头像 URL"),
        status=status,
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
        personalityDesc=desc,  # 保留旧字段，可为空
        tags=persona_data.get("tags", ["最新导入"]),
        heatScore=persona_data.get("heatScore", 0),
        defensiveLevel=persona_data.get("defensiveLevel", 100),
        timeline=persona_data.get("timeline", []),
        chatHistory=persona_data.get("chatHistory", []),
        attachments=processed_attachments,
    )

    personas.append(new_persona.model_dump())
    save_personas_to_file(personas, PERSONAS_FILE)
    return {"persona": new_persona}


@app.put("/persona/{persona_id}")
async def update_persona(persona_id: str, updated_data: Dict[str, Any]):
    """更新指定ID的关系人信息"""
    personas = load_personas_from_file(PERSONAS_FILE)

    # 查找目标 persona
    target_index = None
    for idx, p in enumerate(personas):
        if p.get("id") == persona_id:
            target_index = idx
            break

    if target_index is None:
        raise HTTPException(status_code=404, detail="Persona not found")

    # 获取现有数据
    existing = personas[target_index]

    # 允许更新的字段列表（所有可编辑字段）
    updatable_fields = [
        "name",
        "gender",
        "age",
        "occupation",
        "city",
        "mbti",
        "personality_type",
        "how_met",
        "status",
        "traits",
        "attraction_tips",
        "notes",
        "avatar",
        "tags",
        "heatScore",
        "defensiveLevel",
        "timeline",
        "chatHistory",
    ]

    # 更新字段
    for field in updatable_fields:
        if field in updated_data:
            existing[field] = updated_data[field]

    # 如果 personalityDesc 字段存在且未提供，可以保留旧值或忽略（此处保留）
    # 也可以从 traits/notes 组合生成，但按需求暂不处理

    # 保存回文件
    save_personas_to_file(personas, PERSONAS_FILE)

    # 返回更新后的 persona
    return {"persona": existing}


@app.websocket("/chat")
async def websocket_proxy(websocket: WebSocket):
    """
    模拟聊天
    场景分析

    需要把聊天结果放入chathistory?
    """
    await websocket.accept()

    try:
        # 连接外部 WebSocket
        external_ws = await websockets.connect(API_WS_URL)
    except Exception as e:
        await websocket.send_text(
            json.dumps(
                {"type": "error", "message": f"Failed to connect to external API: {e}"}
            )
        )
        await websocket.close()
        return

    async def forward_to_external():
        """接收前端消息 -> 修改 -> 转发给外部 API"""
        try:
            while True:
                msg = await websocket.receive_text()
                data = json.loads(msg)
                print(data)  # 探针--输出消息

                # 拦截 input.append 事件，注入 system 消息
                if data.get("type") == "input.append":
                    input_data = data.get("input", {})
                    messages = input_data.get("messages", [])
                    if messages is not None:
                        # 在最前面插入 system 消息
                        # system_msg = {"role": "system", "content": SYSTEM_INSTRUCTION}
                        # messages.insert(0, system_msg)
                        input_data["messages"] = messages
                        data["input"] = input_data

                # 转发修改后的消息
                await external_ws.send(json.dumps(data))
        except (WebSocketDisconnect, websockets.ConnectionClosed):
            pass

    async def forward_to_frontend():
        """接收外部 API 消息 -> 转发给前端"""
        try:
            async for msg in external_ws:
                await websocket.send_text(msg)
        except (websockets.ConnectionClosed, WebSocketDisconnect):
            pass

    # 并发执行两个转发任务
    try:
        await asyncio.gather(forward_to_external(), forward_to_frontend())
    except Exception as e:
        print(f"代理异常: {e}")
    finally:
        # 清理连接
        try:
            await external_ws.close()
        except Exception as e:
            print(f"关闭代理 external_ws {e}")
        try:
            await websocket.close()
        except Exception as e:
            print(f"关闭代理 websocket {e}")


@app.websocket("/analyze")
async def analyze_proxy(websocket: WebSocket):
    """
    分析聊天记录
    生成统计数据和可视化图表
    统计数据、图标之类的是之前的档案中建立
    只分析这一次上传的聊天记录，并给出策略什么的

    分析的话应该是不知道怎么办的意思？这是什么信号，我应该怎么处理？
    应该让AI直接给出答复

    同时要更新状态
    """

    await websocket.accept()

    try:
        # 连接外部 WebSocket
        external_ws = await websockets.connect(API_WS_URL)
    except Exception as e:
        await websocket.send_text(
            json.dumps(
                {"type": "error", "message": f"Failed to connect to external API: {e}"}
            )
        )
        await websocket.close()
        return

    async def forward_to_external():
        """接收前端消息 -> 修改 -> 转发给外部 API"""
        try:
            while True:
                msg = await websocket.receive_text()
                data = json.loads(msg)
                # print(data)  # 探针--输出消息

                # 拦截 input.append 事件，注入 system 消息
                if data.get("type") == "input.append":
                    input_data = data.get("input", {})
                    messages = input_data.get("messages", [])
                    if messages is not None:
                        # 在最前面插入 system 消息
                        # system_msg = {"role": "system", "content": SYSTEM_INSTRUCTION}
                        # messages.insert(0, system_msg)
                        input_data["messages"] = messages
                        data["input"] = input_data

                # 转发修改后的消息
                await external_ws.send(json.dumps(data))
        except (WebSocketDisconnect, websockets.ConnectionClosed):
            pass

    async def forward_to_frontend():
        """接收外部 API 消息 -> 转发给前端"""
        try:
            async for msg in external_ws:
                await websocket.send_text(msg)
        except (websockets.ConnectionClosed, WebSocketDisconnect):
            pass

    # 并发执行两个转发任务
    try:
        await asyncio.gather(forward_to_external(), forward_to_frontend())
    except Exception as e:
        print(f"代理异常: {e}")
    finally:
        # 清理连接
        try:
            await external_ws.close()
        except Exception as e:
            print(f"关闭代理 external_ws {e}")
        try:
            await websocket.close()
        except Exception as e:
            print(f"关闭代理 websocket {e}")


@app.get("/timeline")
async def get_timeline(name: str = Query(..., description="传入的名字参数")):
    """读取events.jsonl，返回到前端"""
    timeline = skill.get_timeline(name)
    return {"timeline_data": timeline}


@app.post("/timeline")
async def edit_timeline(event: TimelineEvent):
    """向events.jsonl增加事件"""
    try:
        # 调用业务逻辑函数，将事件写入文件
        # 注意：skill.edit_timeline 应接受 name, title, desc, data 四个参数
        data = {"tag": event.data or "里程碑"}
        skill.edit_timeline(
            name=event.name,
            title=event.title,
            desc=event.desc or "",
            data=data,
        )
        return {"status": "success", "message": "事件已记录"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"记录事件失败: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
