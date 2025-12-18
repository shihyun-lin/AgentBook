import React from 'react';

export default function DataView({ statusInfo, posts, relationshipsInfo }) {
    const users = statusInfo?.data?.users || [];
    const relationships = relationshipsInfo?.data?.relationships || [];

    return (
        <div className="flex-1 overflow-y-auto bg-white p-10 hide-scrollbar">
            <div className="max-w-4xl mx-auto space-y-8">
                <div>
                    <h1 className="text-3xl font-display font-bold text-gray-900">Analytics</h1>
                    <p className="text-gray-500">Real-time simulation metrics</p>
                </div>

                <div className="grid grid-cols-3 gap-6">
                    <StatBox label="Active Agents" val={users.length} />
                    <StatBox label="Total Posts" val={posts.length} />
                    <StatBox label="Avg Energy" val={users.length ? Math.round(users.reduce((a, b) => a + b.energy, 0) / users.length) + '%' : '0%'} />
                </div>

                {/* Agent Table */}
                <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
                    <table className="w-full text-sm text-left">
                        <thead className="bg-gray-50 text-gray-500 font-medium">
                            <tr>
                                <th className="px-6 py-4">Agent Name</th>
                                <th className="px-6 py-4">Model</th>
                                <th className="px-6 py-4">Status</th>
                                <th className="px-6 py-4 text-right">Followers</th>
                                <th className="px-6 py-4 text-right">Energy</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {users.sort((a, b) => b.followers - a.followers).map((u, i) => (
                                <tr key={i} className="hover:bg-gray-50/50">
                                    <td className="px-6 py-4 font-bold text-gray-900">{u.name}</td>
                                    <td className="px-6 py-4">
                                        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full font-medium">
                                            {u.model || 'Unknown'}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4"><span className="inline-flex w-2 h-2 rounded-full bg-green-500"></span></td>
                                    <td className="px-6 py-4 text-right">{u.followers}</td>
                                    <td className="px-6 py-4 text-right">
                                        <div className="w-20 ml-auto bg-gray-100 rounded-full h-1.5 overflow-hidden">
                                            <div className="bg-primary-500 h-full" style={{ width: u.energy + '%' }}></div>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            {users.length === 0 && <tr><td colSpan="5" className="px-6 py-8 text-center text-gray-400">No Data</td></tr>}
                        </tbody>
                    </table>
                </div>

                {/* Relationships Graph */}
                <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
                    <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
                        <h2 className="font-bold text-gray-900 flex items-center gap-2">
                            💕 人際關係圖譜
                            <span className="text-xs font-normal text-gray-500">
                                ({relationships.length} 人有連結)
                            </span>
                        </h2>
                    </div>

                    {relationships.length === 0 ? (
                        <div className="px-6 py-12 text-center text-gray-400">
                            <div className="text-4xl mb-2">🤝</div>
                            <p>尚無人際關係數據</p>
                            <p className="text-sm">等待模擬進行中...</p>
                        </div>
                    ) : (
                        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                            {relationships.map((rel, idx) => (
                                <div key={idx} className="bg-gray-50 rounded-xl p-5 border border-gray-100/60 hover:shadow-md transition-all duration-300">
                                    {/* User Node */}
                                    <div className="flex items-center gap-3 mb-4 pb-3 border-b border-gray-100">
                                        <div className="w-12 h-12 rounded-full bg-gray-900 flex items-center justify-center text-white font-bold text-lg shadow-sm">
                                            {rel.user[0]}
                                        </div>
                                        <div>
                                            <div className="font-bold text-gray-900 text-lg">{rel.user}</div>
                                            <div className="text-xs text-gray-500 font-medium">{rel.connections.length} connections</div>
                                        </div>
                                    </div>

                                    {/* Connections */}
                                    <div className="space-y-3">
                                        {rel.connections.map((conn, cidx) => (
                                            <div
                                                key={cidx}
                                                className="flex items-center gap-3 p-2.5 rounded-lg bg-white border border-gray-100 hover:border-primary-200 transition-colors group"
                                            >
                                                <div className="text-xl transform group-hover:scale-110 transition-transform">{conn.emoji}</div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex justify-between items-center mb-0.5">
                                                        <span className="font-bold text-gray-800 text-sm truncate">{conn.target}</span>
                                                        <span className={`text-xs font-bold ${conn.score > 20 ? 'text-pink-500' :
                                                            conn.score > 0 ? 'text-emerald-500' : 'text-gray-400'
                                                            }`}>
                                                            {conn.score > 0 ? '+' : ''}{conn.score}
                                                        </span>
                                                    </div>
                                                    <div className="flex justify-between items-center">
                                                        <div className="text-[10px] text-gray-400 font-medium truncate bg-gray-50 px-1.5 py-0.5 rounded">
                                                            {conn.impression}
                                                        </div>
                                                        {/* Visual Score Bar */}
                                                        <div className="w-16 h-1 bg-gray-100 rounded-full ml-2 overflow-hidden">
                                                            <div
                                                                className={`h-full rounded-full ${conn.score > 20 ? 'bg-pink-400' : 'bg-emerald-400'}`}
                                                                style={{ width: Math.min(100, Math.max(0, conn.score * 2)) + '%' }}
                                                            ></div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

const StatBox = ({ label, val }) => (
    <div className="p-6 rounded-2xl border border-gray-100 bg-gray-50/50">
        <div className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-1">{label}</div>
        <div className="text-3xl font-bold text-gray-900">{val}</div>
    </div>
);
