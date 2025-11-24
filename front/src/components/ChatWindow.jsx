import React, { useState, useEffect, useRef } from 'react';
import { Globe, Paperclip, ArrowUp, FileText, X } from 'lucide-react';
import ModelSelector from './ModelSelector';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import Toast from './Toast';

const ChatWindow = ({ conversationId, onConversationCreated }) => {
    const [messages, setMessages] = useState([
        { role: 'assistant', content: 'Welcome to PomeloGPT. How can I help you today?' }
    ]);
    const [input, setInput] = useState('');
    const [webSearchEnabled, setWebSearchEnabled] = useState(false);
    const [streaming, setStreaming] = useState(false);
    const [toast, setToast] = useState(null); // { message, type }

    // Model State
    const [models, setModels] = useState([]);
    const [selectedModel, setSelectedModel] = useState('');
    const [loadingModels, setLoadingModels] = useState(true);

    // RAG State
    const [attachments, setAttachments] = useState([]);
    const [pendingFiles, setPendingFiles] = useState([]); // Files waiting to be uploaded (for new chats)
    const [uploading, setUploading] = useState(false);
    const [showAttachments, setShowAttachments] = useState(false);
    const fileInputRef = useRef(null);

    const messagesEndRef = useRef(null);
    const textareaRef = useRef(null);

    // Load history when conversationId changes
    useEffect(() => {
        if (conversationId) {
            loadMessages(conversationId);
            fetchAttachments(conversationId);
            setPendingFiles([]); // Clear pending files when switching to an existing chat
        } else {
            // Reset for new chat
            setMessages([
                { role: 'assistant', content: 'Welcome to PomeloGPT. How can I help you today?' }
            ]);
            setAttachments([]);
            // Keep pending files if we are just staying in new chat mode, 
            // but if we switched FROM a chat TO new chat, we might want to clear?
            // Actually, if conversationId becomes null, it means we switched to New Chat.
            // We should probably clear pending files from previous attempts if any?
            // Let's assume switching to New Chat clears everything.
            setPendingFiles([]);
        }
    }, [conversationId]);

    // ... (keep existing useEffects)

    const loadMessages = async (id) => {
        try {
            const res = await window.api.invoke('api-call', `chat/${id}`, {}, 'GET');
            if (res.messages) {
                setMessages(res.messages);
            }
        } catch (err) {
            console.error("Failed to load messages", err);
        }
    };

    const fetchAttachments = async (id) => {
        try {
            const res = await window.api.invoke('api-call', `rag/documents?conversation_id=${id}`, {}, 'GET');
            if (res.documents) {
                setAttachments(res.documents);
            } else {
                setAttachments([]);
            }
        } catch (err) {
            console.error("Failed to fetch attachments", err);
            setAttachments([]);
        }
    };

    const handleUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // If we are in a new chat (no ID), just add to pending files
        if (!conversationId) {
            setPendingFiles(prev => [...prev, file]);
            setToast({ message: `The file "${file.name}" has been added (pending)`, type: 'info' });
            if (fileInputRef.current) fileInputRef.current.value = '';
            return;
        }

        // If we have an ID, upload immediately
        setUploading(true);
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('conversation_id', conversationId);

            const res = await fetch('http://localhost:8000/rag/upload', {
                method: 'POST',
                body: formData
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Upload failed");
            }

            await fetchAttachments(conversationId);
            setToast({ message: `The file "${file.name}" has been added`, type: 'success' });
        } catch (err) {
            console.error("Upload failed", err);
            setToast({ message: `Upload failed: ${err.message}`, type: 'error' });
        } finally {
            setUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    const handleDeleteAttachment = async (filename, isPending = false) => {
        if (!confirm(`Remove ${filename}?`)) return;

        if (isPending) {
            setPendingFiles(prev => prev.filter(f => f.name !== filename));
            setToast({ message: `Removed "${filename}"`, type: 'info' });
            return;
        }

        try {
            const encodedFilename = encodeURIComponent(filename);
            await window.api.invoke('api-call', `rag/documents/${encodedFilename}?conversation_id=${conversationId}`, {}, 'DELETE');
            await fetchAttachments(conversationId);
            setToast({ message: `Removed "${filename}"`, type: 'success' });
        } catch (err) {
            console.error("Failed to delete attachment", err);
            setToast({ message: `Failed to remove "${filename}"`, type: 'error' });
        }
    };

    // ... (keep scrollToBottom and other effects)

    const handleSend = async () => {
        if (!input.trim() || streaming) return;
        if (!selectedModel) {
            setMessages(prev => [...prev, { role: 'assistant', content: 'Error: No model selected. Please install a model first.' }]);
            return;
        }

        console.log("Sending request with Web Search:", webSearchEnabled);

        const userMessage = { role: 'user', content: input };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setStreaming(true);
        isStreamingRef.current = true;
        streamingQueueRef.current = []; // Clear queue

        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }

        try {
            // Add placeholder for assistant message
            setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

            let currentConversationId = conversationId;

            // 1. Create chat if needed
            if (!currentConversationId) {
                const res = await window.api.invoke('api-call', 'chat/new', { title: "New Chat" }, 'POST');
                if (res && res.id) {
                    currentConversationId = res.id;
                    onConversationCreated(currentConversationId);
                } else {
                    throw new Error("Failed to create new chat");
                }
            }

            // 2. Upload pending files if any
            if (pendingFiles.length > 0) {
                for (const file of pendingFiles) {
                    const formData = new FormData();
                    formData.append('file', file);
                    formData.append('conversation_id', currentConversationId);

                    await fetch('http://localhost:8000/rag/upload', {
                        method: 'POST',
                        body: formData
                    });

                    // Show success toast for each uploaded file
                    setToast({ message: `"${file.name}" ready for RAG`, type: 'success' });
                }
                // Clear pending files as they are now uploaded
                setPendingFiles([]);
                // Fetch attachments to update UI
                await fetchAttachments(currentConversationId);
            }

            // 3. Send message
            const response = await fetch('http://localhost:8000/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: selectedModel,
                    messages: [
                        ...messages,
                        userMessage
                    ].map(m => ({ role: m.role, content: m.content })),
                    conversation_id: currentConversationId,
                    stream: true,
                    use_rag: attachments.length > 0 || pendingFiles.length > 0, // Use RAG if we have existing OR pending files
                    use_web_search: webSearchEnabled,
                    searxng_url: "http://localhost:8080"
                })
            });

            if (!response.body) throw new Error('No response body');

            // ... (rest of streaming logic)

            const newConversationId = response.headers.get('X-Conversation-ID');
            if (newConversationId && newConversationId !== conversationId) {
                onConversationCreated(newConversationId);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;

                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.trim()) {
                        try {
                            const json = JSON.parse(line);
                            if (json.content) {
                                // Push to queue instead of setting state directly
                                // Split content into smaller chunks (chars) for smoother animation if needed
                                // But pushing the whole token is usually fine if interval is fast
                                // For very smooth typing, we can split by char
                                const chars = json.content.split('');
                                streamingQueueRef.current.push(...chars);
                            }
                        } catch (e) {
                            console.warn("Error parsing JSON chunk:", e);
                        }
                    }
                }
            }
        } catch (err) {
            console.error("Streaming error:", err);
            setMessages(prev => [...prev, { role: 'assistant', content: 'Error: Failed to get response.' }]);
        } finally {
            setStreaming(false);
            isStreamingRef.current = false;
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const adjustTextareaHeight = () => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
        }
    };

    // Helper to clean message content
    const cleanContent = (content) => {
        if (!content) return '';
        const trimmed = content.trim();
        // If the entire message is wrapped in a code block, unwrap it
        if (trimmed.startsWith('```') && trimmed.endsWith('```')) {
            const lines = trimmed.split('\n');
            if (lines.length >= 2) {
                return lines.slice(1, -1).join('\n');
            }
        }
        return content;
    };

    return (
        <div className="chat-window">
            {toast && (
                <Toast
                    message={toast.message}
                    type={toast.type}
                    onClose={() => setToast(null)}
                />
            )}
            <div className="messages-container">
                {messages.map((msg, idx) => (
                    <div key={idx} className={`message-wrapper ${msg.role}`}>
                        <div className="message-bubble">
                            {msg.role === 'assistant' ? (
                                <div className="markdown-content">
                                    <ReactMarkdown
                                        components={{
                                            code({ node, inline, className, children, ...props }) {
                                                const match = /language-(\w+)/.exec(className || '');
                                                return !inline && match ? (
                                                    <SyntaxHighlighter
                                                        style={vscDarkPlus}
                                                        language={match[1]}
                                                        PreTag="div"
                                                        {...props}
                                                    >
                                                        {String(children).replace(/\n$/, '')}
                                                    </SyntaxHighlighter>
                                                ) : (
                                                    <code className={className} {...props}>
                                                        {children}
                                                    </code>
                                                );
                                            }
                                        }}
                                    >
                                        {cleanContent(msg.content)}
                                    </ReactMarkdown>
                                </div>
                            ) : (
                                <p>{msg.content}</p>
                            )}
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            <div className="chat-input-container">
                <div className="input-controls">
                    <ModelSelector
                        models={models}
                        selectedModel={selectedModel}
                        onSelectModel={setSelectedModel}
                        loading={loadingModels}
                    />
                    <div
                        className="control-btn-wrapper"
                        onMouseEnter={() => setShowAttachments(true)}
                        onMouseLeave={() => setShowAttachments(false)}
                    >
                        {showAttachments && (attachments.length > 0 || pendingFiles.length > 0) && (
                            <div className="attachments-popover">
                                {attachments.map((doc, idx) => (
                                    <div key={`existing-${idx}`} className="attachment-item">
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                            <FileText size={14} />
                                            <span>{doc.filename}</span>
                                        </div>
                                        <button
                                            className="remove-attachment-btn"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleDeleteAttachment(doc.filename, false);
                                            }}
                                        >
                                            <X size={12} />
                                        </button>
                                    </div>
                                ))}
                                {pendingFiles.map((file, idx) => (
                                    <div key={`pending-${idx}`} className="attachment-item pending">
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontStyle: 'italic', opacity: 0.8 }}>
                                            <FileText size={14} />
                                            <span>{file.name} (pending)</span>
                                        </div>
                                        <button
                                            className="remove-attachment-btn"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleDeleteAttachment(file.name, true);
                                            }}
                                        >
                                            <X size={12} />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                        <button
                            className={`control-btn ${attachments.length > 0 || pendingFiles.length > 0 ? 'has-attachments' : ''}`}
                            title="Upload Document"
                            onClick={() => fileInputRef.current?.click()}
                            disabled={uploading}
                        >
                            <Paperclip size={18} />
                        </button>
                    </div>
                    <input
                        type="file"
                        ref={fileInputRef}
                        style={{ display: 'none' }}
                        onChange={handleUpload}
                        accept=".pdf,.txt"
                    />
                    <button
                        className={`control-btn ${webSearchEnabled ? 'active' : ''}`}
                        onClick={() => {
                            const newValue = !webSearchEnabled;
                            setWebSearchEnabled(newValue);
                            localStorage.setItem('web_search_enabled', newValue.toString());
                        }}
                        title={`Web Search ${webSearchEnabled ? '(Enabled)' : '(Disabled)'}`}
                    >
                        <Globe size={18} />
                    </button>
                </div>
                <div className="input-wrapper">
                    <textarea
                        ref={textareaRef}
                        value={input}
                        onChange={(e) => { setInput(e.target.value); adjustTextareaHeight(); }}
                        onKeyDown={handleKeyDown}
                        placeholder="Message PomeloGPT..."
                        rows={1}
                    />
                    <button onClick={handleSend} className="send-button" disabled={!input.trim() || streaming}>
                        <ArrowUp size={20} />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ChatWindow;
