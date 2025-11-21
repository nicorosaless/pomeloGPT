import React from 'react';

const DocumentPanel = () => {
    const documents = [
        { id: 1, name: 'Project_Specs.pdf', size: '2.4 MB', date: '2023-10-27' },
        { id: 2, name: 'Meeting_Notes.txt', size: '12 KB', date: '2023-10-28' },
    ];

    return (
        <div className="panel document-panel">
            <div className="panel-header">
                <h3>Knowledge Base</h3>
                <button className="add-doc-btn">+</button>
            </div>
            <div className="document-list">
                {documents.length === 0 ? (
                    <div className="empty-state">No documents uploaded</div>
                ) : (
                    documents.map((doc) => (
                        <div key={doc.id} className="document-item">
                            <div className="doc-icon">📄</div>
                            <div className="doc-info">
                                <div className="doc-name">{doc.name}</div>
                                <div className="doc-meta">{doc.size} • {doc.date}</div>
                            </div>
                            <button className="doc-action">⋮</button>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

export default DocumentPanel;
