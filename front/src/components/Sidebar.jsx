import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, Plus, PanelLeftClose, Bot, Pencil, Trash2, Check, X, Settings } from 'lucide-react';

const Sidebar = ({ activeMode, onSetMode, onToggleSidebar, activeConversationId, onSelectChat }) => {
    const [conversations, setConversations] = useState([]);
    const [editingId, setEditingId] = useState(null);
    const [editTitle, setEditTitle] = useState("");
    const editInputRef = useRef(null);

    useEffect(() => {
        fetchHistory();
        // Poll for history updates every 5s
        const interval = setInterval(fetchHistory, 5000);
        return () => clearInterval(interval);
    }, []);

    const fetchHistory = async () => {
        try {
            const res = await window.api.invoke('api-call', 'chat/history', {}, 'GET');
            if (res.conversations) {
                setConversations(res.conversations);
            }
        } catch (err) {
            console.error("Failed to fetch history", err);
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
                {conversations.map((conv) => (
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
                ))}
            </div>

            <div className="sidebar-footer">
                <button
                    className="sidebar-item"
                    onClick={() => onSetMode('settings')}
                    title="Settings"
                    style={{
                        width: '100%',
                        justifyContent: 'flex-start',
                        gap: '10px',
                        opacity: activeMode === 'settings' ? 1 : 0.7
                    }}
                >
                    <Settings size={20} />
                    <span style={{ fontSize: '0.9rem' }}>Settings</span>
                </button>
            </div>
        </div>
    );
};

export default Sidebar;
