import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config';

export default function Sidebar({ activeView, setActiveView, onStart }) {
    const [simulating, setSimulating] = useState(false);
    const [loading, setLoading] = useState(false);
    const [days, setDays] = useState(5); // 默認 5 天

    useEffect(() => {
        const check = async () => {
            try {
                const res = await fetch(`${API_BASE_URL}/api/status`);
                const data = await res.json();
                setSimulating(data.running);
            } catch (e) { }
        };
        check();
        const timer = setInterval(check, 5000);
        return () => clearInterval(timer);
    }, []);

    const toggleSim = async () => {
        setLoading(true);
        try {
            if (simulating) {
                // 停止模擬
                const res = await fetch(`${API_BASE_URL}/api/stop`, { method: 'POST' });
                const d = await res.json();
                if (d.status === 'ok') setSimulating(false);
            } else {
                // 啟動模擬，傳遞天數
                // 清除舊資料
                if (onStart) onStart();

                const res = await fetch(`${API_BASE_URL}/api/start?days=${days}`, { method: 'POST' });
                const d = await res.json();
                if (d.status === 'ok') {
                    setSimulating(true);
                } else {
                    alert(d.message || 'Failed to start');
                }
            }
        } catch (e) {
            alert('Error: ' + e.message);
        } finally {
            setLoading(false);
        }
    };

    const NavBtn = ({ id, icon, label }) => (
        <button
            onClick={() => setActiveView(id)}
            className={`w-12 h-12 rounded-2xl flex items-center justify-center transition-all duration-300 relative group
                ${activeView === id ? 'bg-black text-white shadow-glow' : 'text-gray-400 hover:bg-gray-100 hover:text-gray-900'}`}
        >
            <i className={`fas ${icon} text-xl`}></i>
            <span className="absolute left-14 bg-gray-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                {label}
            </span>
        </button>
    );

    return (
        <aside className="w-[80px] flex flex-col items-center py-8 justify-between flex-shrink-0 bg-[#F8FAFC]">
            {/* Brand */}
            <div className="w-12 h-12 bg-black text-white rounded-2xl flex items-center justify-center text-xl font-bold shadow-soft mb-8">
                A
            </div>

            {/* Nav */}
            <div className="flex flex-col gap-6">
                <NavBtn id="home" icon="fa-stream" label="Feed" />
                <NavBtn id="messages" icon="fa-comments" label="Messages" />
                <NavBtn id="data" icon="fa-chart-pie" label="Analytics" />
            </div>

            {/* Controller */}
            <div className="mt-auto flex flex-col items-center gap-4">
                {/* Days Selector */}
                {!simulating && (
                    <div className="flex flex-col items-center gap-2 p-3 bg-white rounded-2xl shadow-sm border border-gray-100">
                        <div className="text-[10px] font-bold text-gray-500 uppercase tracking-wide">
                            Days
                        </div>
                        <div className="relative w-12">
                            <input
                                type="range"
                                min="1"
                                max="10"
                                value={days}
                                onChange={(e) => setDays(Number(e.target.value))}
                                disabled={loading}
                                className="w-full h-1 bg-gray-200 rounded-lg appearance-none cursor-pointer range-slider"
                                style={{
                                    background: `linear-gradient(to right, #000 0%, #000 ${(days - 1) * 11.11}%, #e5e7eb ${(days - 1) * 11.11}%, #e5e7eb 100%)`
                                }}
                            />
                        </div>
                        <div className="text-2xl font-bold text-black">
                            {days}
                        </div>
                    </div>
                )}

                {/* Start/Stop Button */}
                <button
                    onClick={toggleSim}
                    disabled={loading}
                    className={`w-14 h-14 rounded-full flex items-center justify-center transition-all duration-300 shadow-soft
                        ${simulating ? 'bg-white border-2 border-red-500 text-red-500 hover:bg-red-50' : 'bg-black text-white hover:bg-gray-800 hover:scale-105 shadow-glow'}
                        ${loading ? 'opacity-50 cursor-not-allowed' : ''}
                    `}
                >
                    {loading ? <i className="fas fa-spinner fa-spin text-xl"></i> :
                        simulating ? <i className="fas fa-stop text-xl"></i> :
                            <i className="fas fa-play text-xl ml-1"></i>}
                </button>
            </div>
        </aside>
    );
}
