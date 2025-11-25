import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, Plus, PanelLeftClose, Bot, Pencil, Trash2, Check, X, Settings } from 'lucide-react';

const Sidebar = ({ activeMode, onSetMode, onToggleSidebar, activeConversationId, onSelectChat, refreshTrigger }) => {
    const [conversations, setConversations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [editingId, setEditingId] = useState(null);
    const [editTitle, setEditTitle] = useState("");
    const editInputRef = useRef(null);

    useEffect(() => {
        fetchHistory();
    }, [refreshTrigger]);

    useEffect(() => {
        fetchHistoryWithRetry();
        // Poll for history updates every 60s
        const interval = setInterval(() => fetchHistory(), 60000);
        return () => clearInterval(interval);
    }, []);

    const fetchHistoryWithRetry = async (retryCount = 0) => {
        try {
            const res = await window.api.invoke('api-call', 'chat/history', {}, 'GET');
            if (res && res.conversations) {
                setConversations(res.conversations);
                setLoading(false);
            } else if (res && res.error) {
                // Backend returned an error, retry
                if (retryCount < 10) {
                    setTimeout(() => fetchHistoryWithRetry(retryCount + 1), 1000);
                } else {
                    console.error("Chat history error after retries:", res.error);
                    setLoading(false);
                }
            }
        } catch (err) {
            // Network/connection error, retry
            if (retryCount < 10) {
                console.log(`Retrying chat history (${retryCount + 1}/10)...`);
                setTimeout(() => fetchHistoryWithRetry(retryCount + 1), 1000);
            } else {
                console.error("Failed to fetch history after retries:", err);
                setLoading(false);
            }
        }
    };

    const fetchHistory = async () => {
        try {
            const res = await window.api.invoke('api-call', 'chat/history', {}, 'GET');
            if (res && res.conversations) {
                setConversations(res.conversations);
            }
        } catch (err) {
            console.error("Failed to fetch history:", err);
        }
    };

    const handleNewChat = () => {
        onSelectChat(null); // Deselect current chat to start fresh
        onSetMode('chat');
    };

    const handleDelete = async (e, id) => {
        e.stopPropagation();
        if (!confirm("Are you sure you want to delete this chat?")) return;

        try {
            await window.api.invoke('api-call', `chat/${id}`, {}, 'DELETE');
            fetchHistory();
            if (activeConversationId === id) {
                onSelectChat(null); // Deselect if active
            }
        } catch (err) {
            console.error("Failed to delete chat", err);
        }
    };

    const startEditing = (e, conv) => {
        e.stopPropagation();
        setEditingId(conv.id);
        setEditTitle(conv.title || "New Chat");
    };

    const cancelEditing = (e) => {
        if (e) e.stopPropagation();
        setEditingId(null);
        setEditTitle("");
    };

    const saveTitle = async (e) => {
        if (e) e.stopPropagation();
        if (!editTitle.trim()) return cancelEditing();

        try {
            await window.api.invoke('api-call', `chat/${editingId}/title`, { title: editTitle }, 'PUT');
            fetchHistory();
            setEditingId(null);
        } catch (err) {
            console.error("Failed to rename chat", err);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') {
            saveTitle();
        } else if (e.key === 'Escape') {
            cancelEditing();
        }
    };

    useEffect(() => {
        if (editingId && editInputRef.current) {
            editInputRef.current.focus();
        }
    }, [editingId]);

    return (
        <div className="sidebar">
            <div style={{ height: '20px' }}></div> {/* Spacer if needed, or just remove */}

            <div className="sidebar-actions">
                <button className="new-chat-btn" onClick={handleNewChat}>
                    <Plus size={18} />
                    <span>New Chat</span>
                </button>
            </div>

            <div className="history-list">
                <div className="history-section-label">Recent</div>
                {loading ? (
                    <div className="history-loading">
                        <div className="loading-spinner"></div>
                        <span>Loading conversations...</span>
                    </div>
                ) : conversations.length === 0 ? (
                    <div className="history-empty">No conversations yet</div>
                ) : (
                    conversations.map((conv) => (
                        <div key={conv.id} className={`history-item-wrapper ${activeConversationId === conv.id ? 'active' : ''}`}>
                            {editingId === conv.id ? (
                                <div className="history-edit-container">
                                    <input
                                        ref={editInputRef}
                                        className="history-input"
                                        value={editTitle}
                                        onChange={(e) => setEditTitle(e.target.value)}
                                        onKeyDown={handleKeyDown}
                                        onBlur={saveTitle}
                                        onClick={(e) => e.stopPropagation()}
                                    />
                                    <button className="icon-btn small" onMouseDown={saveTitle}><Check size={14} /></button>
                                    <button className="icon-btn small" onMouseDown={cancelEditing}><X size={14} /></button>
                                </div>
                            ) : (
                                <button
                                    className="history-item"
                                    onClick={() => onSelectChat(conv.id)}
                                >
                                    <span className="history-title">{conv.title || "New Chat"}</span>
                                    <div className="history-actions">
                                        <span className="action-icon" onClick={(e) => startEditing(e, conv)} title="Rename">
                                            <Pencil size={14} />
                                        </span>
                                        <span className="action-icon delete" onClick={(e) => handleDelete(e, conv.id)} title="Delete">
                                            <Trash2 size={14} />
                                        </span>
                                    </div>
                                </button>
                            )}
                        </div>
                    ))
                )}
            </div>

            <div className="sidebar-footer">
                <button
                    className="sidebar-item settings-icon-only"
                    onClick={() => onSetMode('settings')}
                    title="Settings"
                >
                    <Settings size={20} />
                </button>
            </div>
        </div>
    );
};

export default Sidebar;
