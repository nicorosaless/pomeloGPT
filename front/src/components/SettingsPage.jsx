import React, { useState, useEffect } from 'react';
import { Settings, Globe, Palette, Bot } from 'lucide-react';
import OllamaManager from './OllamaManager';

const SettingsPage = () => {
    const [activeTab, setActiveTab] = useState('models');
    const [webSearchEnabled, setWebSearchEnabled] = useState(false);

    // Load settings from localStorage on mount
    useEffect(() => {
        setWebSearchEnabled(localStorage.getItem('web_search_enabled') === 'true');
    }, []);

    const handleToggleChange = (e) => {
        const checked = e.target.checked;
        setWebSearchEnabled(checked);
        localStorage.setItem('web_search_enabled', checked.toString());
    };

    const renderContent = () => {
        switch (activeTab) {
            case 'models':
                return <OllamaManager />;
            case 'websearch':
                return (
                    <div className="settings-section">
                        <h3>Web Search Configuration</h3>
                        <p className="settings-desc">SearXNG search engine runs automatically with PomeloGPT.</p>
                        <div className="setting-item">
                            <label>Search Engine Status</label>
                            <p style={{ marginTop: '8px', color: '#10a37f' }}>
                                ✓ SearXNG is configured and ready to use
                            </p>
                        </div>
                        <div className="setting-item">
                            <label>SearXNG URL</label>
                            <input
                                type="text"
                                className="setting-input"
                                value="http://localhost:8080"
                                disabled
                                style={{ opacity: 0.7 }}
                            />
                        </div>
                        <p className="settings-note">
                            SearXNG starts automatically when you run PomeloGPT. No API key needed!
                            Simply toggle the globe icon in the chat to enable web search.
                        </p>
                    </div>
                );
            case 'appearance':
                return (
                    <div className="settings-section">
                        <h3>Appearance</h3>
                        <p className="settings-desc">Customize the look and feel of PomeloGPT.</p>
                        <div className="setting-item">
                            <label>Theme</label>
                            <select className="setting-select">
                                <option>Dark</option>
                                <option>Light</option>
                                <option>System</option>
                            </select>
                        </div>
                    </div>
                );
            default:
                return null;
        }
    };

    return (
        <div className="settings-container">
            <div className="settings-sidebar">
                <div className="settings-header">
                    <Settings size={20} />
                    <h2>Settings</h2>
                </div>
                <nav className="settings-nav">
                    <button
                        className={`settings-tab ${activeTab === 'models' ? 'active' : ''}`}
                        onClick={() => setActiveTab('models')}
                    >
                        <Bot size={18} />
                        <span>Model Manager</span>
                    </button>
                    <button
                        className={`settings-tab ${activeTab === 'websearch' ? 'active' : ''}`}
                        onClick={() => setActiveTab('websearch')}
                    >
                        <Globe size={18} />
                        <span>Web Search</span>
                    </button>
                    <button
                        className={`settings-tab ${activeTab === 'appearance' ? 'active' : ''}`}
                        onClick={() => setActiveTab('appearance')}
                    >
                        <Palette size={18} />
                        <span>Appearance</span>
                    </button>
                </nav>
            </div>
            <div className="settings-content">
                {renderContent()}
            </div>
        </div>
    );
};

export default SettingsPage;
