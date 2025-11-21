import React, { useState, useEffect } from 'react';
import { MessageSquare, Plus, PanelLeftClose, Bot } from 'lucide-react';

const Sidebar = ({ activeMode, onSetMode, onToggleSidebar, activeConversationId, onSelectChat }) => {
    const [conversations, setConversations] = useState([]);

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

    const handleNewChat = async () => {
        try {
            const res = await window.api.invoke('api-call', 'chat/new', { title: "New Chat" }, 'POST');
            if (res.id) {
                fetchHistory();
                // We should also tell the parent to switch to this chat
                // For now, just refresh list. The ChatWindow needs to know about the new ID.
                // We might need a global context or pass a callback for "onSelectChat"
                // For this iteration, let's just create it.
                onSetMode('chat'); // Ensure we are in chat mode
            }
        } catch (err) {
            console.error("Failed to create new chat", err);
        }
    };

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
                    <button
                        key={conv.id}
                        className={`history-item ${activeConversationId === conv.id ? 'active' : ''}`}
                        onClick={() => onSelectChat(conv.id)}
                    >
                        {conv.title || "New Chat"}
                    </button>
                ))}
            </div>

            <div className="sidebar-footer">
                <button
                    className="sidebar-item"
                    onClick={() => onSetMode('models')}
                    title="Manage Models"
                    style={{
                        width: '100%',
                        justifyContent: 'flex-start',
                        gap: '10px',
                        opacity: activeMode === 'models' ? 1 : 0.7
                    }}
                >
                    <Bot size={20} />
                    <span style={{ fontSize: '0.9rem' }}>Models</span>
                </button>
            </div>
        </div>
    );
};

export default Sidebar;
