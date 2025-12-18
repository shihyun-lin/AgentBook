"""
AgentBook 事件发送器
将模拟事件发送到 WebSocket 服务器
"""

import requests
import json
from typing import Dict, Optional
from datetime import datetime

import os

class EventEmitter:
    """事件发送器"""
    
    def __init__(self, server_url: str = None):
        if server_url is None:
            port = os.environ.get("PORT", "8000")
            self.server_url = f"http://localhost:{port}"
        else:
            self.server_url = server_url
            
        self.enabled = self._check_server_available()
    
    def _check_server_available(self) -> bool:
        """检测服务器是否可用"""
        try:
            response = requests.get(f"{self.server_url}/api/status", timeout=1)
            print(f"✅ WebSocket 服务器已连接 ({self.server_url})")
            return True
        except Exception:
            print(f"⚠️  WebSocket 服务器未运行，模拟将以独立模式运行（无实时可视化）")
            return False
    
    def emit(self, event_type: str, data: Dict, timestamp: str = None):
        """发送事件到服务器"""
        if not self.enabled:
            return
        
        try:
            payload = {
                "type": event_type,
                "data": data,
                "timestamp": timestamp or datetime.now().isoformat()
            }
            requests.post(
                f"{self.server_url}/api/event",
                json=payload,
                timeout=0.5
            )
        except Exception as e:
            # 静默失败，不影响模拟运行
            pass
    
    def emit_day_start(self, day: int, topic: str, start_date: str = None):
        """发送「新一天开始」事件"""
        from datetime import datetime, timedelta
        
        # 計算模擬日期（Day 1 = 啟動當天）
        if start_date:
            base_date = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            base_date = datetime.now()
        
        sim_date = base_date + timedelta(days=day - 1)
        date_str = sim_date.strftime("%Y/%m/%d")
        weekday = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"][sim_date.weekday()]
        
        sim_timestamp_str = sim_date.isoformat()
        
        self.emit("day_start", {
            "day": day,
            "topic": topic,
            "date": date_str,
            "weekday": weekday
        }, timestamp=sim_timestamp_str)
    
    def emit_post(self, user_name: str, content: str, thought: str = "", timestamp: str = None):
        """发送「发文」事件"""
        self.emit("post", {
            "user": user_name,
            "content": content,
            "thought": thought
        }, timestamp)
    
    def emit_comment(self, user_name: str, content: str, target_post: str = "", timestamp: str = None):
        """发送「留言」事件"""
        self.emit("comment", {
            "user": user_name,
            "content": content,
            "target": target_post
        }, timestamp)
    
    def emit_dm(self, from_user: str, to_user: str, message: str, timestamp: str = None):
        """发送「私讯」事件"""
        self.emit("dm", {
            "from": from_user,
            "to": to_user,
            "message": message
        }, timestamp)
    
    def emit_status(self, users: list):
        """发送「状态更新」事件"""
        self.emit("status", {
            "users": users
        })
    
    def emit_day_end(self, day: int, diaries: list):
        """发送「一天结束」事件"""
        self.emit("day_end", {
            "day": day,
            "diaries": diaries
        })
    
    def emit_relationships(self, relationships: list):
        """发送「人际关系」事件"""
        self.emit("relationships", {
            "relationships": relationships
        })

# 全局事件发送器实例
emitter = EventEmitter()
