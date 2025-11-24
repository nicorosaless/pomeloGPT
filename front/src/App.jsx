import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import ModelSelector from './components/ModelSelector';
import DocumentPanel from './components/DocumentPanel';
import SettingsPage from './components/SettingsPage';
import './App.css';

import { PanelLeftClose, PanelLeftOpen } from 'lucide-react';

function App() {
    const [activeMode, setActiveMode] = useState('chat');
    const [sidebarVisible, setSidebarVisible] = useState(true);
    const [activeConversationId, setActiveConversationId] = useState(null);

    return (
        <div className="app-container">
            <div className={`general-header ${sidebarVisible ? 'sidebar-open' : ''}`}>
                <button
                    className="sidebar-toggle-btn"
                    onClick={() => setSidebarVisible(!sidebarVisible)}
                    title={sidebarVisible ? "Hide Sidebar" : "Show Sidebar"}
                >
                    {sidebarVisible ? <PanelLeftClose size={20} /> : <PanelLeftOpen size={20} />}
                </button>
            </div>

            <div className="app-body">
                {sidebarVisible && (
                    <Sidebar
                        activeMode={activeMode}
                        onSetMode={setActiveMode}
                        activeConversationId={activeConversationId}
                        onSelectChat={(id) => {
                            setActiveConversationId(id);
                            setActiveMode('chat');
                        }}
                    />
                )}

                <div className="main-content">
                    <div className="workspace">
                        {activeMode === 'chat' && (
                            <>
                                <ChatWindow
                                    conversationId={activeConversationId}
                                    onConversationCreated={setActiveConversationId}
                                />
                            </>
                        )}

                        {activeMode === 'rag' && (
                            <div className="rag-view">
                                <DocumentPanel />
                                <div className="rag-placeholder">RAG Configuration (Coming Soon)</div>
                            </div>
                        )}

                        {activeMode === 'settings' && (
                            <SettingsPage />
                        )}

                        {activeMode === 'documents' && (
                            <div className="documents-view">
                                <DocumentPanel />
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default App;
