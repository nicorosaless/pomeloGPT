import React, { useState, useEffect } from 'react';
import { Trash2, Download, HardDrive, Library, X, Check } from 'lucide-react';

const OllamaManager = () => {
    const [activeTab, setActiveTab] = useState('installed');
    const [installedModels, setInstalledModels] = useState([]);
    const [availableModels, setAvailableModels] = useState([]);
    const [loading, setLoading] = useState(false);
    const [downloadModal, setDownloadModal] = useState(null); // { name, tag } or null
    const [downloadProgress, setDownloadProgress] = useState(null); // string message
    const [selectedModel, setSelectedModel] = useState(null); // For details view
    const [toast, setToast] = useState(null); // { message, type }

    useEffect(() => {
        fetchInstalledModels();
        fetchAvailableModels();
    }, []);

    const fetchInstalledModels = async () => {
        try {
            const res = await window.api.invoke('api-call', 'models/installed', {}, 'GET');
            // Backend returns { models: [...] }
            if (res.models) {
                setInstalledModels(res.models);
            }
        } catch (err) {
            console.error("Failed to fetch installed models", err);
        }
    };

    const fetchAvailableModels = async () => {
        try {
            const res = await window.api.invoke('api-call', 'models/available', {}, 'GET');
            if (res.models) {
                setAvailableModels(res.models);
            }
        } catch (err) {
            console.error("Failed to fetch available models", err);
        }
    };

    const fetchModelInfo = async (name) => {
        try {
            const res = await window.api.invoke('api-call', `models/${name}/info`, {}, 'GET');
            setSelectedModel(res);
        } catch (err) {
            console.error("Failed to fetch model info", err);
            alert(`Failed to fetch info for ${name}`);
        }
    };

    const handleDelete = async (name) => {
        if (!confirm(`Are you sure you want to delete ${name}?`)) return;
        try {
            await window.api.invoke('api-call', `models/${name}`, {}, 'DELETE');
            fetchInstalledModels();
            if (selectedModel && selectedModel.modelfile.includes(name)) { // Simple check, ideally use ID
                setSelectedModel(null);
            }
        } catch (err) {
            alert(`Failed to delete: ${err.message}`);
        }
    };

    const handleDownload = async () => {
        if (!downloadModal) return;
        setLoading(true);
        setDownloadProgress("Starting download... This may take a while.");

        try {
            const res = await window.api.invoke('api-call', 'models/pull', {
                name: downloadModal.name,
                tag: downloadModal.tag
            });

            if (res.status === 'success') {
                setDownloadProgress("Download complete!");
                setTimeout(() => {
                    setLoading(false);
                    setDownloadModal(null);
                    setDownloadProgress(null);
                    fetchInstalledModels();
                    setToast({ message: `Model ${downloadModal.name} installed successfully!`, type: 'success' });
                    setTimeout(() => setToast(null), 3000);
                }, 1000);
            }
        } catch (err) {
            setDownloadProgress(`Error: ${err.message}`);
            setLoading(false);
        }
    };

    return (
        <div className="ollama-manager">
            <div className="tabs">
                <button
                    className={`tab ${activeTab === 'installed' ? 'active' : ''}`}
                    onClick={() => { setActiveTab('installed'); setSelectedModel(null); }}
                >
                    <HardDrive size={18} /> Installed
                </button>
                <button
                    className={`tab ${activeTab === 'library' ? 'active' : ''}`}
                    onClick={() => { setActiveTab('library'); setSelectedModel(null); }}
                >
                    <Library size={18} /> Library
                </button>
            </div>

            <div className="tab-content">
                {activeTab === 'installed' && !selectedModel && (
                    <div className="models-list">
                        {installedModels.length === 0 ? (
                            <div className="empty-state">No models installed. Go to Library to download one.</div>
                        ) : (
                            installedModels.map((model) => (
                                <div key={model.digest} className="model-item" onClick={() => fetchModelInfo(model.name)}>
                                    <div className="model-info">
                                        <div className="model-name">{model.name}</div>
                                        <div className="model-meta">
                                            {(model.size / 1024 / 1024 / 1024).toFixed(2)} GB • {model.details?.family} • {model.details?.quantization_level}
                                        </div>
                                    </div>
                                    <button
                                        className="action-btn delete"
                                        onClick={(e) => { e.stopPropagation(); handleDelete(model.name); }}
                                        title="Delete Model"
                                    >
                                        <Trash2 size={18} />
                                    </button>
                                </div>
                            ))
                        )}
                    </div>
                )}

                {activeTab === 'installed' && selectedModel && (
                    <div className="model-details">
                        <button className="back-btn" onClick={() => setSelectedModel(null)}>← Back to list</button>
                        <h2>{selectedModel.details?.family} <span className="tag">{selectedModel.details?.parameter_size}</span></h2>

                        <div className="details-grid">
                            <div className="detail-item">
                                <label>Format</label>
                                <span>{selectedModel.details?.format}</span>
                            </div>
                            <div className="detail-item">
                                <label>Family</label>
                                <span>{selectedModel.details?.family}</span>
                            </div>
                            <div className="detail-item">
                                <label>Quantization</label>
                                <span>{selectedModel.details?.quantization_level}</span>
                            </div>
                            <div className="detail-item">
                                <label>Parameters</label>
                                <span>{selectedModel.details?.parameter_size}</span>
                            </div>
                        </div>

                        <div className="modelfile-section">
                            <h3>Modelfile</h3>
                            <pre>{selectedModel.modelfile}</pre>
                        </div>
                        <div className="template-section">
                            <h3>Template</h3>
                            <pre>{selectedModel.template}</pre>
                        </div>
                    </div>
                )}

                {activeTab === 'library' && (
                    <div className="library-grid">
                        {availableModels.map((model) => (
                            <div key={model.name} className="library-card">
                                <div className="card-header">
                                    <h3>{model.title || model.name.split(':')[0]}</h3>
                                    <span className="tag">{model.name}</span>
                                </div>
                                <p className="card-desc">{model.description}</p>

                                {model.performance && (
                                    <div className="performance-badges">
                                        <div className="badge-group">
                                            <span className="badge-label">Velocity</span>
                                            <span className={`badge grade-${model.performance.velocity.replace('+', 'plus').toLowerCase()}`}>{model.performance.velocity}</span>
                                        </div>
                                        <div className="badge-group">
                                            <span className="badge-label">Quality</span>
                                            <span className={`badge grade-${model.performance.quality.replace('+', 'plus').toLowerCase()}`}>{model.performance.quality}</span>
                                        </div>
                                    </div>
                                )}

                                <div className="card-meta">
                                    <span>~{model.size_approx}</span>
                                </div>
                                <button
                                    className={`download-btn ${installedModels.some(m => m.name === model.name) ? 'installed' : ''}`}
                                    onClick={() => {
                                        if (installedModels.some(m => m.name === model.name)) return;
                                        setDownloadModal({
                                            name: model.name.split(':')[0],
                                            tag: model.recommended_quantization || 'latest',
                                            modelData: model
                                        });
                                    }}
                                    disabled={installedModels.some(m => m.name === model.name)}
                                >
                                    {installedModels.some(m => m.name === model.name) ? (
                                        <><Check size={16} /> Installed</>
                                    ) : (
                                        <><Download size={16} /> Download</>
                                    )}
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {downloadModal && (
                <div className="modal-overlay">
                    <div className="modal">
                        <div className="modal-header">
                            <h3>Configure {downloadModal.name}</h3>
                            <button className="close-btn" onClick={() => setDownloadModal(null)}><X size={20} /></button>
                        </div>
                        <div className="modal-body">
                            <div className="m1-disclaimer">
                                <div className="disclaimer-icon">i</div>
                                <p>Performance estimates are based on an <strong>Apple M1 Pro</strong>. Your actual experience may vary.</p>
                            </div>

                            <div className="config-section">
                                <h4>Personalize and configure</h4>
                                <p className="config-desc">Choose the quantization level that fits your needs.</p>

                                <div className="quant-options">
                                    {downloadModal.modelData?.quantization_options?.map((option) => (
                                        <div
                                            key={option.tag}
                                            className={`quant-option ${downloadModal.tag === option.tag ? 'selected' : ''}`}
                                            onClick={() => setDownloadModal({ ...downloadModal, tag: option.tag })}
                                        >
                                            <div className="quant-header">
                                                <span className="quant-tag">{option.tag}</span>
                                                {downloadModal.tag === option.tag && <Check size={16} className="check-icon" />}
                                            </div>
                                            <div className="quant-desc">{option.desc}</div>
                                            <div className="quant-details">{option.details}</div>
                                        </div>
                                    )) || (
                                            <div className="form-group">
                                                <label>Tag / Quantization</label>
                                                <input
                                                    type="text"
                                                    value={downloadModal.tag}
                                                    onChange={(e) => setDownloadModal({ ...downloadModal, tag: e.target.value })}
                                                />
                                            </div>
                                        )}
                                </div>
                            </div>

                            {downloadProgress && (
                                <div className="download-status">
                                    {downloadProgress}
                                </div>
                            )}
                        </div>
                        <div className="modal-footer">
                            <button className="cancel-btn" onClick={() => setDownloadModal(null)}>Cancel</button>
                            <button className="confirm-btn" onClick={handleDownload} disabled={loading}>
                                {loading ? 'Downloading...' : 'Download'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {toast && (
                <div className={`toast ${toast.type}`}>
                    {toast.message}
                </div>
            )}
        </div>
    );
};

export default OllamaManager;
