"""
AgentBook WebSocket Server (Updated with Days Selection & Logging)
实时推送模拟数据到前端，并保存日志
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import asyncio
import json
from typing import List
from datetime import datetime
import uvicorn

app = FastAPI()

# 配置 CORS (允許前端跨域請求)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生產環境建議改為具體的前端網域
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket 连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ 客户端已连接。当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"❌ 客户端已断开。当前连接数: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """广播消息给所有连接的客户端"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            if conn in self.active_connections:
                self.active_connections.remove(conn)

manager = ConnectionManager()

# 模拟事件队列
event_queue = asyncio.Queue()

@app.get("/")
async def get_html():
    html_content = """
    <!DOCTYPE html>
    <html><head><title>AgentBook Server</title></head>
    <body style="font-family: Arial; padding: 40px;">
        <h1>🚀 AgentBook Server Running</h1>
        <p>Frontend: <a href="http://localhost:5173">http://localhost:5173</a></p>
        <p>WebSocket: ws://localhost:8000/ws</p>
    </body></html>
    """
    return HTMLResponse(html_content)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/event")
async def receive_event(event: dict):
    """接收来自 Python 程序的事件并保存到日志"""
    try:
        import os
        os.makedirs("logs", exist_ok=True)
        
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = f"logs/events_{today}.json"
        
        events = []
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                try:
                    events = json.load(f)
                except:
                    events = []
        
        event["server_timestamp"] = datetime.now().isoformat()
        events.append(event)
        
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️  保存事件失败: {e}")
    
    await manager.broadcast(event)
    return {"status": "ok"}

# 全局进程管理
import subprocess
simulation_process = None

@app.post("/api/start")
async def start_simulation(days: int = 5):
    """启动 AgentBook 模拟"""
    global simulation_process
    
    if simulation_process and simulation_process.poll() is None:
        return {"status": "error", "message": "模拟已在运行中"}
    
    if days < 1 or days > 10:
        return {"status": "error", "message": "天數必須在 1-10 之間"}
    
    try:
        import os
        import sys
        # Use the same python interpreter that runs the server
        python_cmd = sys.executable
        
        # 獲取腳本絕對路徑
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, "AgentBook_DualLayer.py")
        
        # [NEW] 啟動前清除當日日誌，確保數據重置
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = os.path.join(script_dir, "logs", f"events_{today}.json")
            if os.path.exists(log_file):
                os.remove(log_file)
                print(f"🗑️ 已清除舊日誌: {log_file}")
        except Exception as e:
            print(f"⚠️ 清除日誌失敗: {e}")

        simulation_process = subprocess.Popen(
            [python_cmd, script_path, "--days", str(days)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=script_dir,
            env=os.environ.copy()
        )
        print(f"✅ 模擬已啟動: {days} 天, PID: {simulation_process.pid}")
        return {
            "status": "ok", 
            "message": f"模拟已启动 ({days} 天)", 
            "pid": simulation_process.pid,
            "days": days
        }
    except Exception as e:
        return {"status": "error", "message": f"启动失败: {str(e)}"}

@app.post("/api/stop")
async def stop_simulation():
    """停止 AgentBook 模拟"""
    global simulation_process
    
    if not simulation_process or simulation_process.poll() is not None:
        return {"status": "error", "message": "没有运行中的模拟"}
    
    try:
        simulation_process.terminate()
        simulation_process.wait(timeout=5)
        print("⛔ 模擬已停止")
        return {"status": "ok", "message": "模拟已停止"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/status")
async def get_status():
    """获取模拟状态"""
    global simulation_process
    
    if simulation_process and simulation_process.poll() is None:
        return {"running": True, "pid": simulation_process.pid}
    else:
        return {"running": False}

async def event_broadcaster():
    while True:
        event = await event_queue.get()
        await manager.broadcast(event)
        event_queue.task_done()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(event_broadcaster())
    print("🚀 AgentBook Server 已启动")
    print("📡 打开浏览器访问: http://localhost:8000")
    print("📋 前端开发服务器: http://localhost:5173")
    print("💾 日志保存位置: ./logs/")

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
