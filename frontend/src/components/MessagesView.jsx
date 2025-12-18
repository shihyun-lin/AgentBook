import React from 'react';

export default function MessagesView({ connected, dms }) {
    // Grouping
    const convs = {};
    // Sort dms by old -> new
    const sortedDms = [...dms].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

    sortedDms.forEach(m => {
        const k = [m.data.from, m.data.to].sort().join('-');
        if (!convs[k]) convs[k] = { users: [m.data.from, m.data.to], msgs: [] };
        convs[k].msgs.push(m);
    });

    return (
        <div className="flex-1 overflow-y-auto bg-white p-8">
            <h1 className="text-2xl font-bold mb-6">Conversation History</h1>
            <div className="grid gap-6">
                {Object.entries(convs).map(([key, conv]) => (
                    <div key={key} className="border border-gray-100 rounded-2xl overflow-hidden shadow-sm">
                        <div className="bg-gray-50 px-4 py-3 border-b border-gray-100 flex justify-between">
                            <span className="font-bold text-sm text-gray-700">{conv.users[0]} ↔ {conv.users[1]}</span>
                            <span className="text-xs text-gray-400 bg-white px-2 py-0.5 rounded border border-gray-100">{conv.msgs.length} msgs</span>
                        </div>
                        <div className="p-4 space-y-3 bg-white max-h-[300px] overflow-y-auto">
                            {conv.msgs.map((m, i) => (
                                <div key={i} className="text-sm border-l-2 border-primary-200 pl-3 py-1">
                                    <div className="flex gap-2 text-xs text-gray-400 mb-0.5">
                                        <span className="font-bold text-gray-900">{m.data.from}</span>
                                        <span>{new Date(m.timestamp).toLocaleTimeString()}</span>
                                    </div>
                                    <p className="text-gray-700">{m.data.message}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
                {dms.length === 0 && <p className="text-gray-400">No messages found.</p>}
            </div>
        </div>
    );
}
