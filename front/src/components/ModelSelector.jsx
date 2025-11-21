import React from 'react';

const ModelSelector = ({ models, selectedModel, onSelectModel, loading }) => {
    return (
        <div className="model-selector-container">
            <select
                id="model-select"
                className="model-dropdown"
                value={selectedModel}
                onChange={(e) => onSelectModel(e.target.value)}
                disabled={loading}
            >
                {loading ? (
                    <option>Loading...</option>
                ) : models.length === 0 ? (
                    <option>No models installed</option>
                ) : (
                    models.map((model) => (
                        <option key={model.name} value={model.name}>
                            {model.name}
                        </option>
                    ))
                )}
            </select>
            <div className="model-info">
                <span className={`status-dot ${models.length > 0 ? 'online' : 'offline'}`}></span>
                {models.length > 0 ? 'Ready' : 'No models'}
            </div>
        </div>
    );
};

export default ModelSelector;
