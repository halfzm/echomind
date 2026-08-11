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
    # 读取现有数据
    personas = load_personas_from_file(PERSONAS_FILE)

    name = persona_data.get("name", "新关系人")
    mbti = persona_data.get("mbti", "ENFJ")
    status = persona_data.get("status", "暗恋中")
    desc = persona_data.get("personalityDesc", "")

    # 创建档案
    persona = skill.create(name=name, mbti=mbti, relation_stage=status, notes=desc)
    persona_fp = DATA_DIR / f"{persona.slug}/memories"

    # TODO 创建之后自动的分析聊天记录，生成性格报告之类的

    new_id = "p_" + str(uuid.uuid4())[:8]

    # 处理附件：将内容保存为文件，替换 data 为文件名
    attachments = persona_data.get("attachments", [])
    processed_attachments = []
    for att in attachments:
        # 原始文件名和类型
        orig_name = att.get("name", "unknown")
        att_type = att.get("type", "file")
        content = att.get("data", "")

        # 生成唯一文件名（保留原扩展名）
        ext = os.path.splitext(orig_name)[1]
        if not ext:
            # 根据类型补默认扩展名
            if att_type == "image":
                ext = ".jpg"
            elif att_type == "audio":
                ext = ".wav"
            else:
                ext = ".txt"
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(persona_fp, filename)

        # 根据内容类型写入文件
        if att_type in ("image", "audio"):
            # 内容为 DataURL，例如 "data:image/png;base64,xxxx"
            # 提取 Base64 数据并解码
            if content.startswith("data:"):
                header, encoded = content.split(",", 1)
                if "base64" in header:
                    binary_data = base64.b64decode(encoded)
                else:
                    # 非 base64（少见），直接编码
                    binary_data = encoded.encode()
            else:
                # 可能是纯二进制内容（极端情况）
                binary_data = content.encode()
            with open(filepath, "wb") as f:
                f.write(binary_data)
        else:
            # 文本类文件（txt, json, csv），content 为纯文本
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

        # 替换 data 为文件名
        processed_att = {
            "name": orig_name,
            "type": att_type,
            "data": filename,  # 存储文件名
        }
        processed_attachments.append(processed_att)

    # 更新 persona 数据中的 attachments
    persona_data["attachments"] = processed_attachments

    # 构建 Persona 对象（其余字段不变）
    new_persona = Persona(
        id=new_id,
        name=persona_data.get("name", "新关系人"),
        avatar=persona_data.get("avatar", "默认头像 URL"),
        status=persona_data.get("status", "暗恋中"),
        mbti=persona_data.get("mbti", "ENFJ"),
        tags=persona_data.get("tags", ["最新导入"]),
        personalityDesc=persona_data.get("personalityDesc", ""),
        heatScore=persona_data.get("heatScore", 50),
        defensiveLevel=persona_data.get("defensiveLevel", 50),
        timeline=persona_data.get("timeline", []),
        chatHistory=persona_data.get("chatHistory", []),
        attachments=persona_data.get("attachments", []),
    )
    # 追加到列表并保存
    personas.append(new_persona.model_dump())
    save_personas_to_file(personas, PERSONAS_FILE)
    return {"persona": new_persona}


@app.websocket("/chat")
async def websocket_proxy(websocket: WebSocket):
    """模拟聊天函数"""
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
    """分析聊天记录，生成统计数据和可视化图表
    统计数据、图标之类的是之前的档案中建立
    只分析这一次上传的聊天记录，并给出策略什么的
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


@app.post("/analysis")
async def analysis():
    """分析聊天记录，生成统计数据和可视化图表
    统计数据、图标之类的是之前的档案中建立
    只分析这一次上传的聊天记录，并给出策略什么的
    """
    pass


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
