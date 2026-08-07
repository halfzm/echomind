import json
import asyncio
from pathlib import Path

import websockets
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from skill_loader import load_skill_instructions
from simp_skill import SimpSkill, DATA_DIR

app = FastAPI()
skill = SimpSkill()

# MiniCPM-o API 地址
API_HOST = "minicpmo45.modelbest.cn"
API_WS_URL = f"wss://{API_HOST}/v1/realtime?mode=chat"

# 启动时加载 Skill 指令
# SYSTEM_INSTRUCTION = load_skill_instructions()
# SYSTEM_INSTRUCTION = "在每次回答的最后面加上一个喵字"

# 挂载静态文件目录，URL 前缀为 /static
app.mount("/static", StaticFiles(directory="static"), name="static")


class SelfieRequest(BaseModel):
    name: str
    mbti: str
    strengths: str
    weaknesses: str


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
    pass


@app.post("/persona")
async def create_persona(requests):
    """根据填写的表单，解析聊天记录，创建个性化的 persona，调用解析聊天记录的函数"""
    """根据填写的表单，创建用户资料"""
    try:
        # 解析请求数据
        name = requests.name
        mbti = requests.mbti
        relation_stage = requests.strengths
        description = requests.description
        chats = requests.chats

        # 调用 skill 创建个人档案
        persona = skill.create(
            name=name,
            mbti=mbti,
            relation_stage=relation_stage,
            description=description,
            chats=chats,
        )
        print(f"已创建关系人档案: {persona.name} (slug: {persona.slug})")
        return {"status": "success", "profile": persona}
    except Exception as e:
        return {"error": str(e)}


@app.get("/search")
async def search():
    """根据关键词搜索相关的聊天信息"""
    pass


@app.get("/randomchat")
async def random_chat():
    """随机聊聊"""
    pass


@app.get("/scenariochat")
async def scenario_chat(scenario="random"):
    """场景聊天，根据场景加载不同的预设提示词"""
    pass


@app.get("/analysis")
async def analysis(scenario="random"):
    """分析聊天记录，生成统计数据和可视化图表"""
    pass


@app.websocket("/ws")
async def websocket_proxy(websocket: WebSocket):
    """每次都新加入 system 指令，避免被覆盖"""
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

                # 拦截 input.append 事件，注入 system 消息
                if data.get("type") == "input.append":
                    input_data = data.get("input", {})
                    messages = input_data.get("messages", [])
                    if messages is not None:
                        # 在最前面插入 system 消息
                        system_msg = {"role": "system", "content": SYSTEM_INSTRUCTION}
                        messages.insert(0, system_msg)
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
        except:
            pass
        try:
            await websocket.close()
        except:
            pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
