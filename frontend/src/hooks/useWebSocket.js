import { useState, useEffect, useRef, useCallback } from 'react';

export function useWebSocket(url) {
    const [connected, setConnected] = useState(false);
    const [messages, setMessages] = useState([]);
    const wsRef = useRef(null);
    const seenIds = useRef(new Set()); // 用於去重
    const maxMsg = 500;

    useEffect(() => {
        // 如果已經連線，不重複連線
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            return;
        }

        const connectWS = () => {
            // 關閉現有連線
            if (wsRef.current) {
                wsRef.current.close();
            }

            const ws = new WebSocket(url);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('✅ WebSocket Connected');
                setConnected(true);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    // 生成唯一 ID 用於去重
                    const msgId = `${data.type}_${data.timestamp}_${JSON.stringify(data.data).slice(0, 50)}`;

                    // 檢查是否已經處理過這條消息
                    if (seenIds.current.has(msgId)) {
                        console.log('🔄 Duplicate message ignored');
                        return;
                    }

                    // 記錄這條消息
                    seenIds.current.add(msgId);

                    // 限制 seenIds 大小，避免記憶體洩漏
                    if (seenIds.current.size > 1000) {
                        const ids = Array.from(seenIds.current);
                        seenIds.current = new Set(ids.slice(-500));
                    }

                    setMessages(prev => {
                        const newMsg = [data, ...prev];
                        return newMsg.slice(0, maxMsg);
                    });
                } catch (e) {
                    console.error('Failed to parse message:', e);
                }
            };

            ws.onerror = (e) => {
                console.error('WS Error', e);
                setConnected(false);
            };

            ws.onclose = () => {
                console.log('❌ WebSocket Disconnected');
                setConnected(false);
                // 延遲重連
                setTimeout(connectWS, 3000);
            };
        };

        connectWS();

        return () => {
            // 防止組件卸載後的重連
            if (wsRef.current) {
                // 清除 onclose 防止觸發自動重連
                wsRef.current.onclose = null;
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, [url]);

    const clearMessages = useCallback(() => {
        setMessages([]);
        seenIds.current.clear();
    }, []);

    return { connected, messages, clearMessages };
}
