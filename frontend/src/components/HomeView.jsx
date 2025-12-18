import React, { useState, useMemo } from 'react';

export default function HomeView({ connected, dayInfo, posts, comments, statusInfo, dms }) {
    const [chatCollapsed, setChatCollapsed] = useState(false);

    // 按天分組 DM
    const dmsByDay = useMemo(() => {
        const grouped = {};
        // 先將 dms 按時間排序 (舊 -> 新)
        const sortedDms = [...dms].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

        sortedDms.forEach(dm => {
            const day = dm.day || (dayInfo?.data?.day || 1);
            if (!grouped[day]) grouped[day] = [];
            grouped[day].push(dm);
        });
        return grouped;
    }, [dms, dayInfo]);

    return (
        <div className="flex-1 flex overflow-hidden rounded-l-3xl bg-white">
            {/* Left: Feed */}
            <main className="flex-1 overflow-y-auto hide-scrollbar bg-white relative">
                {/* Sticky Header */}
                <div className="sticky top-0 z-30 px-8 py-5 flex justify-between items-center glass">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Community Feed</h1>
                        <div className="flex items-center gap-2 mt-1">
                            <span className="px-2 py-0.5 rounded-full bg-gray-100 text-[10px] font-bold text-gray-500 uppercase tracking-wide">
                                {dayInfo ? `DAY ${dayInfo.data.day}` : 'STANDBY'}
                            </span>
                            {dayInfo?.data?.date && (
                                <span className="text-xs text-gray-400 font-medium">
                                    {dayInfo.data.date} ({dayInfo.data.weekday})
                                </span>
                            )}
                            {dayInfo && <span className="text-xs text-gray-500 font-medium truncate max-w-[200px]">{dayInfo.data.topic}</span>}
                        </div>
                    </div>
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-50 rounded-full border border-gray-100">
                        <span className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-500 status-dot' : 'bg-red-500'}`}></span>
                        <span className="text-xs font-semibold text-gray-600 uppercase">{connected ? 'Live' : 'Offline'}</span>
                    </div>
                </div>

                <div className="max-w-[680px] mx-auto py-8 px-6 space-y-10 pb-20">
                    {/* Feed Posts */}
                    <div className="space-y-6">
                        {posts.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-20 text-gray-400">
                                <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mb-4">
                                    <i className="fas fa-satellite-dish text-2xl animate-pulse"></i>
                                </div>
                                <p className="font-medium">Waiting for signals...</p>
                            </div>
                        ) : (
                            posts.map((post, idx) => (
                                <PostCard key={idx} post={post} comments={comments} />
                            ))
                        )}
                    </div>
                </div>
            </main>

            {/* Right: Collapsible Chat Panel */}
            <aside className={`bg-gray-50/50 border-l border-gray-100 flex flex-col h-full flex-shrink-0 transition-all duration-300 ${chatCollapsed ? 'w-16' : 'w-[360px]'
                }`}>
                {/* Chat Header */}
                <div className="px-6 py-5 border-b border-gray-100 flex justify-between items-center bg-white/50 backdrop-blur-sm">
                    {!chatCollapsed && (
                        <h2 className="font-bold text-gray-900 flex items-center gap-2">
                            <i className="fas fa-comments text-primary-500"></i> Live Chat
                        </h2>
                    )}
                    <div className="flex items-center gap-2">
                        {!chatCollapsed && (
                            <span className="text-xs font-bold bg-gray-200 text-gray-600 px-2 py-0.5 rounded-full">
                                {dms.length}
                            </span>
                        )}
                        <button
                            onClick={() => setChatCollapsed(!chatCollapsed)}
                            className="w-8 h-8 rounded-full hover:bg-gray-200 flex items-center justify-center transition-colors text-gray-600"
                            title={chatCollapsed ? '展開聊天' : '收起聊天'}
                        >
                            <i className={`fas fa-chevron-${chatCollapsed ? 'left' : 'right'} text-xs`}></i>
                        </button>
                    </div>
                </div>

                {/* Chat Content */}
                {!chatCollapsed && (
                    <div className="flex-1 overflow-y-auto px-5 py-6 space-y-6 hide-scrollbar">
                        {Object.keys(dmsByDay).length > 0 ? (
                            Object.keys(dmsByDay).sort((a, b) => Number(a) - Number(b)).map((day) => (
                                <div key={day}>
                                    {/* Day Divider */}
                                    <div className="flex items-center gap-3 my-4">
                                        <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-300 to-transparent"></div>
                                        <span className="text-xs font-bold text-gray-500 bg-white px-3 py-1 rounded-full border border-gray-200">
                                            Day {day}
                                        </span>
                                        <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-300 to-transparent"></div>
                                    </div>

                                    {/* Messages for this day */}
                                    <div className="space-y-4">
                                        {dmsByDay[day].map((dm, idx) => (
                                            <ChatBubble key={idx} dm={dm} isEven={idx % 2 === 0} />
                                        ))}
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="h-full flex flex-col items-center justify-center text-gray-300">
                                <i className="far fa-comments text-4xl mb-2 opacity-50"></i>
                                <p className="text-sm">No conversations yet</p>
                            </div>
                        )}
                    </div>
                )}

                {/* Collapsed State */}
                {chatCollapsed && (
                    <div className="flex-1 flex flex-col items-center justify-center py-4">
                        <i className="fas fa-comments text-gray-300 text-2xl rotate-90"></i>
                        <span className="text-xs font-bold text-gray-400 mt-4 writing-vertical">CHAT</span>
                        {dms.length > 0 && (
                            <div className="mt-4 w-6 h-6 bg-primary-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
                                {dms.length}
                            </div>
                        )}
                    </div>
                )}
            </aside>
        </div>
    );
}

function PostCard({ post, comments }) {
    const related = comments.filter(c => Math.abs(new Date(c.timestamp) - new Date(post.timestamp)) < 15000);

    return (
        <article className="animate-enter bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-soft transition-all duration-300 group overflow-hidden">
            <div className="p-5">
                {/* Header */}
                <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center text-gray-700 font-bold border border-gray-200">
                            {post.data.user[0]}
                        </div>
                        <div className="leading-tight">
                            <div className="font-bold text-sm text-gray-900 group-hover:text-primary-600 transition-colors">
                                {post.data.user}
                            </div>
                            <div className="text-xs text-gray-400">
                                {new Date(post.timestamp).toLocaleDateString([], { month: 'numeric', day: 'numeric' })} {new Date(post.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </div>
                        </div>
                    </div>
                    <button className="text-gray-300 hover:text-gray-600 transition"><i className="fas fa-ellipsis-h"></i></button>
                </div>

                {/* Content */}
                <div className="pl-[52px]">
                    {post.data.thought && (
                        <div className="inline-block bg-primary-50 text-blue-600 text-xs font-medium px-2.5 py-1 rounded-lg mb-2">
                            <i className="far fa-lightbulb mr-1"></i> {post.data.thought}
                        </div>
                    )}
                    <p className="text-gray-800 text-[15px] leading-relaxed mb-3">
                        {post.data.content}
                    </p>

                    {/* Actions */}
                    <div className="flex items-center gap-6 pt-2 text-gray-400 text-sm">
                        <button className="hover:text-pink-500 transition flex items-center gap-1.5 group/btn">
                            <i className="far fa-heart group-hover/btn:scale-110 transition-transform"></i>
                        </button>
                        <button className="hover:text-blue-500 transition flex items-center gap-1.5">
                            <i className="far fa-comment-alt"></i>
                            {related.length > 0 && <span className="text-xs">{related.length}</span>}
                        </button>
                        <button className="hover:text-green-500 transition ml-auto">
                            <i className="far fa-share-square"></i>
                        </button>
                    </div>
                </div>
            </div>

            {/* Comments */}
            {related.length > 0 && (
                <div className="bg-gray-50/50 p-4 pl-[72px] space-y-3 border-t border-gray-100/50">
                    {related.map((c, i) => (
                        <div key={i} className="flex gap-2 text-sm">
                            <span className="font-bold text-gray-900 flex-shrink-0">{c.data.user}</span>
                            <span className="text-gray-600">{c.data.content}</span>
                        </div>
                    ))}
                </div>
            )}
        </article>
    );
}

function ChatBubble({ dm, isEven }) {
    return (
        <div className={`flex flex-col ${isEven ? 'items-start' : 'items-end'}`}>
            <div className="flex items-center gap-2 mb-1 px-1">
                <span className={`text-[10px] font-bold uppercase tracking-wide ${isEven ? 'text-primary-600' : 'text-purple-600'}`}>
                    {dm.data.from}
                </span>
            </div>
            <div className={`
                max-w-[90%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed shadow-sm
                ${isEven ? 'bg-white border border-gray-100 rounded-tl-none text-gray-800' : 'bg-primary-600 text-white rounded-tr-none'}
            `}>
                {dm.data.message}
            </div>
            <div className="mt-1 px-1 text-[10px] text-gray-400">
                To: {dm.data.to}
            </div>
        </div>
    );
}
