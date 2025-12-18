import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import HomeView from './components/HomeView';
import MessagesView from './components/MessagesView';
import DataView from './components/DataView';
import { useWebSocket } from './hooks/useWebSocket';

import { WS_BASE_URL } from './config';

export default function App() {
    const [activeView, setActiveView] = useState('home');

    // 使用 WebSocket Hook
    const { connected, messages, clearMessages } = useWebSocket(WS_BASE_URL);
    // 注意：这里的 URL 端口是前端端口 (5173)。Vite 的 proxy 配置会将 /ws 请求转发到后端 (8000)。
    // 如果直接写 8000，虽然也能通，但跨域需要后端支持。用 Proxy 比较标准。

    // 数据分类逻辑
    const posts = messages.filter(m => m.type === 'post');
    const comments = messages.filter(m => m.type === 'comment');
    const dms = messages.filter(m => m.type === 'dm');
    const dayInfo = messages.find(m => m.type === 'day_start');
    const statusInfo = messages.find(m => m.type === 'status');
    const relationshipsInfo = messages.find(m => m.type === 'relationships');

    return (
        <div className="h-screen flex bg-[#F8FAFC]">
            {/* 侧边栏 */}
            <Sidebar activeView={activeView} setActiveView={setActiveView} onStart={clearMessages} />

            {/* 主内容容器 */}
            <div className="flex-1 flex overflow-hidden relative shadow-2xl rounded-l-3xl bg-white my-2 mr-2 border border-gray-100">
                {activeView === 'home' && (
                    <HomeView
                        connected={connected}
                        dayInfo={dayInfo}
                        posts={posts}
                        comments={comments}
                        statusInfo={statusInfo}
                        dms={dms}
                    />
                )}

                {activeView === 'messages' && (
                    <MessagesView connected={connected} dms={dms} />
                )}

                {activeView === 'data' && (
                    <DataView statusInfo={statusInfo} posts={posts} relationshipsInfo={relationshipsInfo} />
                )}
            </div>
        </div>
    );
}
