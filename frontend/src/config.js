// 根據環境判斷 API URL
// 在開發環境 (Dev) 使用相對路徑，讓 Vite proxy 處理
// 在生產環境 (Prod) 必須使用環境變數 VITE_API_URL 指向後端

const isDev = import.meta.env.DEV;

export const API_BASE_URL = isDev
    ? ''
    : (import.meta.env.VITE_API_URL || 'http://localhost:8000');

export const WS_BASE_URL = isDev
    ? 'ws://localhost:5173/ws'
    : (import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws');
