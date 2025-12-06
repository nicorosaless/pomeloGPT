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

    // Custom download state
    const [customModelInput, setCustomModelInput] = useState(''); // e.g. "ministral-3:3b"
    const [fetchedTags, setFetchedTags] = useState([]);
    const [isFetchingTags, setIsFetchingTags] = useState(false);

    useEffect(() => {
        fetchInstalledModels();
        fetchAvailableModels();
    }, []);

    const fetchInstalledModels = async () => {
        console.log("Fetching installed models...");
        try {
            const res = await window.api.invoke('api-call', 'models/installed', {}, 'GET');
            console.log("Installed models response:", res);
            // Backend returns { models: [...] }
            if (res.models) {
                setInstalledModels(res.models);
            } else {
                console.warn("No models property in response:", res);
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
        setDownloadProgress("Starting download...");

        // Reset progress state
        let success = false;
        let lastStatus = "";

        try {
            // Use direct fetch for streaming support
            const response = await fetch('http://127.0.0.1:8000/models/pull', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: downloadModal.name,
                    tag: downloadModal.tag
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const data = JSON.parse(line);
                        if (data.error) {
                            throw new Error(data.error);
                        }
                        if (data.status) {
                            lastStatus = data.status;
                            let msg = data.status;
                            if (data.total && data.completed) {
                                const percent = Math.round((data.completed / data.total) * 100);
                                msg += ` ${percent}%`;
                                // Update progress bar if we had one, for now string message
                            }
                            setDownloadProgress(msg);

                            if (data.status === 'success') {
                                success = true;
                            }
                        }
                    } catch (e) {
                        console.error("Error parsing chunk", e);
                        if (e.message !== "Unexpected end of JSON input") {
                            // If it's a real error from the backend (parsed from json), rethrow
                            if (line.includes('"error":')) throw e;
                        }
                    }
                }
            }

            if (!success && lastStatus !== 'success') {
                // Check if we got a "success" status at all. 
                // Ollama API usually sends {"status":"success"} as the last message.
                // If we didn't get it, something might be wrong, OR the stream ended abruptly.
                // However, for some pulls, it might just end. 
                // But usually "manifest" -> "downloading" -> "success".
                // Let's rely on the fact that if no error was thrown, it might be ok, 
                // BUT the user reported false success. 
                // Let's verify if the model actually exists in the installed list after a short delay?
                // Or better: if we didn't get any chunks, it's a fail.
                if (!lastStatus) throw new Error("No response from server");
            }

            setDownloadProgress("Download complete!");

            // Add to available models if it's a custom one
            if (!availableModels.some(m => m.name === `${downloadModal.name}:${downloadModal.tag}`)) {
                const newModel = {
                    name: `${downloadModal.name}:${downloadModal.tag}`,
                    title: downloadModal.name,
                    description: "Custom downloaded model",
                    size_approx: "Unknown",
                    tags: ["custom"],
                    recommended_quantization: downloadModal.tag
                };
                setAvailableModels(prev => [...prev, newModel]);
            }

            setTimeout(() => {
                setLoading(false);
                setDownloadModal(null);
                setDownloadProgress(null);
                fetchInstalledModels();
                setToast({ message: `Model ${downloadModal.name}:${downloadModal.tag} installed successfully!`, type: 'success' });
                setTimeout(() => setToast(null), 3000);
            }, 1000);

        } catch (err) {
            console.error("Download error:", err);
            let errorMsg = err.message;
            if (errorMsg.includes("manifest") || errorMsg.includes("file does not exist")) {
                errorMsg = `Model or tag not found. Please check the name and tag on Ollama.com.`;
            }
            setDownloadProgress(`Error: ${errorMsg}`);
            // Do NOT close modal or show success toast
            setLoading(false);
        }
    };

    const fetchTags = async (modelName) => {
        if (!modelName) return;
        setIsFetchingTags(true);
        setFetchedTags([]);
        try {
            const res = await window.api.invoke('api-call', `models/lookup/${modelName}`, {}, 'GET');
            if (res.tags && res.tags.length > 0) {
                setFetchedTags(res.tags);
            } else {
                setFetchedTags([]); // No tags found or error
            }
        } catch (err) {
            console.error("Failed to fetch tags", err);
        } finally {
            setIsFetchingTags(false);
        }
    };

    const handleCustomDownload = () => {
        if (!customModelInput.trim()) {
            alert("Please enter a model name");
            return;
        }

        // Parse input: "model:tag" or just "model"
        let name = customModelInput.trim();
        let tag = "latest";

        if (name.includes(':')) {
            const parts = name.split(':');
            name = parts[0];
            tag = parts.slice(1).join(':');
        }

        // Reset tags when opening modal
        setFetchedTags([]);

        // Auto-fetch tags if we have a name
        fetchTags(name);

        setDownloadModal({
            name: name,
            tag: tag,
            isCustom: true,
            modelData: {
                // We don't provide hardcoded options to force the "Input + Suggestions" view
            }
        });
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
                        {/* Custom Download Card */}
                        <div className="library-card custom-download-card" style={{ border: '1px dashed var(--border-color)' }}>
                            <div className="card-header">
                                <h3>Download New Model</h3>
                                <span className="tag">Custom</span>
                            </div>
                            <p className="card-desc">Download any model from the Ollama library by name.</p>

                            <div className="form-group" style={{ marginTop: '1rem' }}>
                                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Model Name & Tag</label>
                                <input
                                    type="text"
                                    placeholder="e.g. ministral-3:3b"
                                    value={customModelInput}
                                    onChange={(e) => setCustomModelInput(e.target.value)}
                                    style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
                                />
                                <small style={{ display: 'block', marginTop: '0.25rem', color: 'var(--text-tertiary)' }}>
                                    If no tag is specified, "latest" will be used.
                                </small>
                            </div>

                            <button
                                className="download-btn"
                                onClick={handleCustomDownload}
                                style={{ marginTop: '1rem' }}
                            >
                                <Download size={16} /> Download
                            </button>
                        </div>
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
                                                    placeholder="e.g. latest, q4_k_m"
                                                    className="tag-input"
                                                    style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '1rem' }}
                                                />

                                                {downloadModal.isCustom && (
                                                    <div className="tag-suggestions" style={{ marginTop: '1rem' }}>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                                                            <p style={{ fontSize: '0.85rem', color: 'var(--text-tertiary)', margin: 0 }}>
                                                                {isFetchingTags ? 'Fetching available tags...' : (fetchedTags.length > 0 ? 'Available Tags:' : 'Common Tags:')}
                                                            </p>
                                                            <button
                                                                onClick={() => fetchTags(downloadModal.name)}
                                                                disabled={isFetchingTags}
                                                                style={{ background: 'none', border: 'none', color: 'var(--accent-color)', cursor: 'pointer', fontSize: '0.8rem', textDecoration: 'underline' }}
                                                            >
                                                                Refresh Tags
                                                            </button>
                                                        </div>

                                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', maxHeight: '150px', overflowY: 'auto' }}>
                                                            {(fetchedTags.length > 0 ? fetchedTags : ['latest', 'q4_k_m', 'q5_k_m', 'q8_0', 'fp16']).map(tag => (
                                                                <button
                                                                    key={tag}
                                                                    onClick={() => setDownloadModal({ ...downloadModal, tag })}
                                                                    style={{
                                                                        padding: '0.25rem 0.75rem',
                                                                        borderRadius: '100px',
                                                                        border: '1px solid var(--border-color)',
                                                                        background: downloadModal.tag === tag ? 'var(--accent-color)' : 'transparent',
                                                                        color: downloadModal.tag === tag ? '#fff' : 'var(--text-secondary)',
                                                                        cursor: 'pointer',
                                                                        fontSize: '0.85rem'
                                                                    }}
                                                                >
                                                                    {tag}
                                                                </button>
                                                            ))}
                                                        </div>

                                                        {downloadModal.tag && fetchedTags.includes(downloadModal.tag) && (
                                                            <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'center' }}>
                                                                <button
                                                                    onClick={handleDownload}
                                                                    disabled={loading}
                                                                    style={{
                                                                        background: 'var(--accent-color)',
                                                                        color: '#fff',
                                                                        border: 'none',
                                                                        padding: '0.5rem 1.5rem',
                                                                        borderRadius: '8px',
                                                                        cursor: 'pointer',
                                                                        display: 'flex',
                                                                        alignItems: 'center',
                                                                        gap: '0.5rem',
                                                                        fontSize: '0.9rem',
                                                                        fontWeight: 500
                                                                    }}
                                                                >
                                                                    <Download size={16} />
                                                                    Download {downloadModal.name}:{downloadModal.tag}
                                                                </button>
                                                            </div>
                                                        )}

                                                        <p style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)', marginTop: '0.5rem', fontStyle: 'italic' }}>
                                                            {fetchedTags.length > 0 ? 'Tags fetched from Ollama Library.' : 'Note: Not all tags are available for every model. Check the model page on Ollama.com if unsure.'}
                                                        </p>
                                                    </div>
                                                )}
                                                {downloadModal.isCustom && (
                                                    <div style={{ marginTop: '1rem', textAlign: 'center' }}>
                                                        <a
                                                            href={`https://ollama.com/library/${downloadModal.name}`}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            style={{ color: 'var(--accent-color)', fontSize: '0.9rem', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                                                        >
                                                            View {downloadModal.name} on Ollama Library <span style={{ fontSize: '1.1em' }}>↗</span>
                                                        </a>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                </div>
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
