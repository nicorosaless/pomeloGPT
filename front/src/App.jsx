import React, { useState, useEffect } from 'react';
import ErrorBoundary from './components/ErrorBoundary';
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
    const [sidebarRefreshTrigger, setSidebarRefreshTrigger] = useState(0);

    // Theme State
    const [theme, setTheme] = useState(() => {
        return localStorage.getItem('theme') || 'dark';
    });

    useEffect(() => {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }, [theme]);

    const toggleTheme = () => {
        setTheme(prev => prev === 'dark' ? 'light' : 'dark');
    };

    return (
        <ErrorBoundary>
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
                            refreshTrigger={sidebarRefreshTrigger}
                            theme={theme}
                            onToggleTheme={toggleTheme}
                        />
                    )}

                    <div className="main-content">
                        <div className="workspace">
                            {activeMode === 'chat' && (
                                <>
                                    <ChatWindow
                                        conversationId={activeConversationId}
                                        onConversationCreated={setActiveConversationId}
                                        onRefreshSidebar={() => setSidebarRefreshTrigger(prev => prev + 1)}
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
        </ErrorBoundary>
    );
}

export default App;
