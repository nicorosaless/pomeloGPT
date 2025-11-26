import React, { useState, useEffect, useRef } from 'react';
import { Globe, Paperclip, ArrowUp, FileText, X } from 'lucide-react';
import ModelSelector from './ModelSelector';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import Toast from './Toast';
import LoadingOrb from './LoadingOrb';

const ChatWindow = ({ conversationId, onConversationCreated, onRefreshSidebar }) => {
    const [messages, setMessages] = useState([
        { role: 'assistant', content: 'Welcome to PomeloGPT. How can I help you today?' }
    ]);
    const [input, setInput] = useState('');
    const [webSearchEnabled, setWebSearchEnabled] = useState(() => {
        return localStorage.getItem('web_search_enabled') === 'true';
    });
    const [streaming, setStreaming] = useState(false);
    const [loadingMessage, setLoadingMessage] = useState('');
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
    const messagesContainerRef = useRef(null);
    const textareaRef = useRef(null);
    const isStreamingRef = useRef(false);
    const streamingQueueRef = useRef([]);
    const justCreatedConversationIdRef = useRef(null);
    const lastUserMessageRef = useRef(null);
    const shouldScrollToUserRef = useRef(false);
    const shouldScrollToBottomRef = useRef(true);
    // Tracks desired scroll direction after messages update


    // Load history when conversationId changes
    useEffect(() => {
        console.log("ConversationId changed to:", conversationId);
        try {
            if (conversationId) {
                // If we just created this conversation locally, don't reload messages
                // to avoid overwriting the current state with potentially incomplete DB state
                if (conversationId === justCreatedConversationIdRef.current) {
                    console.log("Skipping loadMessages for just-created conversation");
                    justCreatedConversationIdRef.current = null;
                    fetchAttachments(conversationId);
                } else {
                    console.log("Loading messages for existing conversation");
                    loadMessages(conversationId);
                    fetchAttachments(conversationId);
                }
                setPendingFiles([]); // Clear pending files when switching to an existing chat
            } else {
                // Reset for new chat
                console.log("Resetting for new chat");
                setMessages([
                    { role: 'assistant', content: 'Welcome to PomeloGPT. How can I help you today?' }
                ]);
                setAttachments([]);
                setPendingFiles([]);
            }
        } catch (error) {
            console.error("Error in conversationId useEffect:", error);
        }
    }, [conversationId]);

    useEffect(() => {
        fetchModels();
    }, []);

    const fetchModels = async (retryCount = 0) => {
        if (retryCount === 0) setLoadingModels(true);

        try {
            const res = await window.api.invoke('api-call', 'models/installed', {}, 'GET');

            // Check for error in response object (IPC handler might return { error: ... })
            if (res.error) {
                throw new Error(res.error);
            }

            if (res.models) {
                setModels(res.models);
                if (res.models.length > 0) {
                    // Default to the first model if none selected
                    if (!selectedModel) {
                        setSelectedModel(res.models[0].name);
                    }
                }
                setLoadingModels(false);
            } else {
                throw new Error("Invalid response format: missing models");
            }
        } catch (err) {
            console.error(`Failed to fetch models (attempt ${retryCount + 1})`, err);

            // Retry up to 10 times with 1 second delay (10 seconds total)
            if (retryCount < 10) {
                setTimeout(() => fetchModels(retryCount + 1), 1000);
            } else {
                setLoadingModels(false);
                setToast({ message: "Failed to load models. Is the backend running?", type: "error" });
            }
        }
    };

    const loadMessages = async (id) => {
        try {
            const res = await window.api.invoke('api-call', `chat/${id}`, {}, 'GET');
            if (res.messages) {
                shouldScrollToBottomRef.current = true;
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

    const scrollToBottom = () =>
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });

    useEffect(() => {
        if (shouldScrollToUserRef.current && lastUserMessageRef.current) {
            lastUserMessageRef.current.scrollIntoView({ behavior: 'auto', block: 'start' });
            shouldScrollToUserRef.current = false;
            shouldScrollToBottomRef.current = false;
        } else if (shouldScrollToBottomRef.current) {
            scrollToBottom();
        }
    }, [messages, streaming]);

    // Process streaming queue - DISABLED (using direct updates)
    useEffect(() => {
        // No-op
    }, []);

    const handleSend = async () => {
        console.log("=== handleSend START ===");
        console.log("Input:", input);
        console.log("Streaming:", streaming);
        console.log("Selected Model:", selectedModel);
        console.log("ConversationId:", conversationId);

        if (!input.trim() || streaming) return;
        if (!selectedModel) {
            setMessages(prev => [...prev, { role: 'assistant', content: 'Error: No model selected. Please install a model first.' }]);
            return;
        }

        console.log("Sending request with Web Search:", webSearchEnabled);

        const userMessage = { role: 'user', content: input };
        let loadingInterval = null; // Declare outside try block for cleanup in finally

        try {
            shouldScrollToUserRef.current = true;
            shouldScrollToBottomRef.current = false;
            setMessages(prev => [...prev, userMessage]);
            setInput('');
            setStreaming(true);
            isStreamingRef.current = true;
            streamingQueueRef.current = []; // Clear queue

            if (textareaRef.current) {
                textareaRef.current.style.height = 'auto';
            }

            // Add placeholder for assistant message
            setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

            // Start loading messages if web search is enabled
            if (webSearchEnabled) {
                setLoadingMessage('Iniciando...');
            }

            let currentConversationId = conversationId;

            // 1. Create chat if needed
            if (!currentConversationId) {
                console.log("Creating new conversation...");
                const res = await window.api.invoke('api-call', 'chat/new', { title: "New Chat" }, 'POST');
                if (res && res.id) {
                    currentConversationId = res.id;
                    console.log("Created conversation:", currentConversationId);
                    // CRITICAL: Set this BEFORE calling onConversationCreated to prevent race condition
                    // where the useEffect calls loadMessages and wipes out the streaming messages
                    justCreatedConversationIdRef.current = currentConversationId;
                    onConversationCreated(currentConversationId);
                } else {
                    throw new Error("Failed to create new chat");
                }
            }

            // 2. Upload pending files if any
            if (pendingFiles.length > 0) {
                console.log("Uploading pending files:", pendingFiles.length);
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
            console.log("Starting stream...");
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

            const newConversationId = response.headers.get('X-Conversation-ID');
            console.log("Stream started, conversation ID:", newConversationId);

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let hasStartedStreaming = false;

            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    console.log("Stream done");
                    break;
                }

                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;

                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.trim()) {
                        try {
                            console.log("Processing chunk:", line);
                            const json = JSON.parse(line);

                            if (json.status !== undefined) {
                                // Update loading message with status from backend
                                setLoadingMessage(json.status);
                            } else if (json.content) {
                                // Clear loading message once we start receiving content
                                if (!hasStartedStreaming) {
                                    setLoadingMessage('');
                                    hasStartedStreaming = true;
                                }

                                // Directly append content to the assistant message
                                setMessages(prev => {
                                    const updated = [...prev];
                                    const lastIndex = updated.length - 1;
                                    const lastMsg = updated[lastIndex];
                                    if (lastMsg && lastMsg.role === 'assistant') {
                                        updated[lastIndex] = {
                                            ...lastMsg,
                                            content: lastMsg.content + json.content
                                        };
                                    }
                                    return updated;
                                });
                            } else if (json.error) {
                                console.error("Stream error from backend:", json.error);
                            }
                        } catch (e) {
                            console.warn("Error parsing JSON chunk:", e, line);
                        }
                    }
                }
            }

            // Refresh sidebar to show the new conversation
            if (onRefreshSidebar) {
                console.log("Refreshing sidebar");
                onRefreshSidebar();
            }

            console.log("=== handleSend COMPLETE ===");
        } catch (err) {
            console.error("=== handleSend ERROR ===", err);
            setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message || 'Failed to get response.'}` }]);
        } finally {
            // Clear loading interval if it's still running
            if (loadingInterval) {
                clearInterval(loadingInterval);
            }
            setLoadingMessage('');
            setStreaming(false);
            isStreamingRef.current = false;
            console.log("=== handleSend FINALLY ===");
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

    const lastUserIndex = messages.map(m => m.role).lastIndexOf('user');

    return (
        <div className="chat-window">
            {toast && (
                <Toast
                    message={toast.message}
                    type={toast.type}
                    onClose={() => setToast(null)}
                />
            )}
            <div className="messages-container" ref={messagesContainerRef}>
                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        className={`message-wrapper ${msg.role}`}
                        ref={idx === lastUserIndex ? lastUserMessageRef : null}
                    >
                        <div className="message-bubble">
                            {msg.role === 'assistant' ? (
                                <>
                                    {/* Show loading orb if this is the last message, it's empty, and we're streaming */}
                                    {streaming && idx === messages.length - 1 && !msg.content && (
                                        <LoadingOrb
                                            showProgress={webSearchEnabled}
                                            progressMessage={loadingMessage}
                                        />
                                    )}
                                    {/* Always show markdown content, even during streaming */}
                                    {msg.content && (
                                        <div className="markdown-content">
                                            <ReactMarkdown
                                                remarkPlugins={[remarkMath]}
                                                rehypePlugins={[rehypeKatex]}
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
                                    )}
                                </>
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
