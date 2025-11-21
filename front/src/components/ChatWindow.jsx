import React, { useState, useEffect, useRef } from 'react';
import { Globe, Paperclip, ArrowUp } from 'lucide-react';
import ModelSelector from './ModelSelector';
import ReactMarkdown from 'react-markdown';

const ChatWindow = ({ conversationId, onConversationCreated }) => {
    const [messages, setMessages] = useState([
        { role: 'assistant', content: 'Welcome to PomeloGPT. How can I help you today?' }
    ]);
    const [input, setInput] = useState('');
    const [webSearchEnabled, setWebSearchEnabled] = useState(false);
    const [streaming, setStreaming] = useState(false);

    // Model State
    const [models, setModels] = useState([]);
    const [selectedModel, setSelectedModel] = useState('');
    const [loadingModels, setLoadingModels] = useState(true);

    const messagesEndRef = useRef(null);
    const textareaRef = useRef(null);

    // Load history when conversationId changes
    useEffect(() => {
        if (conversationId) {
            loadMessages(conversationId);
        } else {
            // Reset for new chat
            setMessages([
                { role: 'assistant', content: 'Welcome to PomeloGPT. How can I help you today?' }
            ]);
        }
    }, [conversationId]);

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

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Fetch models with 30s polling
    // Fetch models with retry logic on startup
    useEffect(() => {
        let attempts = 0;
        const maxFastAttempts = 10;
        let intervalId;

        const fetchWithRetry = async () => {
            const success = await fetchModels();
            if (success) {
                // If successful, switch to slow polling
                clearInterval(intervalId);
                intervalId = setInterval(fetchModels, 30000);
            } else {
                attempts++;
                if (attempts < maxFastAttempts) {
                    // Continue fast polling
                } else {
                    // Switch to slow polling even if failed
                    clearInterval(intervalId);
                    intervalId = setInterval(fetchModels, 30000);
                }
            }
        };

        // Initial fetch
        fetchWithRetry();

        // Start fast polling (every 1s)
        intervalId = setInterval(fetchWithRetry, 1000);

        return () => clearInterval(intervalId);
    }, []);

    const fetchModels = async () => {
        try {
            const res = await window.api.invoke('api-call', 'models/installed', {}, 'GET');
            if (res.models) {
                setModels(res.models);
                // If no model selected, select the first one
                if (!selectedModel && res.models.length > 0) {
                    setSelectedModel(res.models[0].name);
                } else if (selectedModel && !res.models.find(m => m.name === selectedModel)) {
                    // If selected model is no longer available, select first available
                    if (res.models.length > 0) setSelectedModel(res.models[0].name);
                }
                setLoadingModels(false);
                return true; // Success
            }
            return false;
        } catch (err) {
            console.error("Failed to fetch models for selector", err);
            setLoadingModels(false);
            return false; // Failed
        }
    };

    const handleSend = async () => {
        if (!input.trim() || streaming) return;
        if (!selectedModel) {
            setMessages(prev => [...prev, { role: 'assistant', content: 'Error: No model selected. Please install a model first.' }]);
            return;
        }

        const userMessage = { role: 'user', content: input };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setStreaming(true);

        // Reset textarea height
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }

        try {
            // Add placeholder for assistant message
            setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

            const response = await fetch('http://localhost:8000/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: selectedModel,
                    messages: [
                        { role: 'system', content: 'You are a helpful assistant. Respond in the language of the user. Use inline code (single backticks) for single words, short phrases, or variable names. Only use code blocks (triple backticks) for multi-line code or longer snippets.' },
                        ...messages,
                        userMessage
                    ].map(m => ({ role: m.role, content: m.content })),
                    conversation_id: conversationId,
                    stream: true
                })
            });

            if (!response.body) throw new Error('No response body');

            // Check for conversation ID in header
            const newConversationId = response.headers.get('X-Conversation-ID');
            if (newConversationId && newConversationId !== conversationId) {
                onConversationCreated(newConversationId);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let assistantMessage = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                assistantMessage += chunk;

                setMessages(prev => {
                    const newMessages = [...prev];
                    newMessages[newMessages.length - 1] = { role: 'assistant', content: assistantMessage };
                    return newMessages;
                });
            }
        } catch (err) {
            console.error("Streaming error:", err);
            setMessages(prev => [...prev, { role: 'assistant', content: 'Error: Failed to get response.' }]);
        } finally {
            setStreaming(false);
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

    return (
        <div className="chat-window">
            <div className="messages-container">
                {messages.map((msg, idx) => (
                    <div key={idx} className={`message-wrapper ${msg.role}`}>
                        <div className="message-bubble">
                            {msg.role === 'user' ? (
                                msg.content
                            ) : (
                                <ReactMarkdown
                                    components={{
                                        code({ node, inline, className, children, ...props }) {
                                            const match = /language-(\w+)/.exec(className || '')
                                            const codeContent = String(children).replace(/\n$/, '')
                                            const isMultiLine = codeContent.includes('\n')
                                            const isShort = codeContent.length < 50

                                            // Heuristic: If it's a block but short and single-line, render it like a "block-inline" hybrid
                                            // This avoids the heavy window chrome for simple words like "if", "else"
                                            if (!inline && !isMultiLine && isShort) {
                                                return (
                                                    <code className={className} style={{
                                                        display: 'inline-block',
                                                        padding: '4px 8px',
                                                        margin: '4px 0',
                                                        borderRadius: '6px',
                                                        background: 'rgba(255, 255, 255, 0.1)',
                                                        border: '1px solid rgba(255, 255, 255, 0.1)',
                                                        fontFamily: 'monospace',
                                                        color: '#e4e4e7'
                                                    }} {...props}>
                                                        {children}
                                                    </code>
                                                )
                                            }

                                            return !inline ? (
                                                <div className="code-block-wrapper">
                                                    <div className="code-header">
                                                        <span>{match ? match[1] : 'code'}</span>
                                                        <button className="copy-btn" onClick={() => navigator.clipboard.writeText(String(children))}>Copy</button>
                                                    </div>
                                                    <pre className={className} {...props}>
                                                        <code>{children}</code>
                                                    </pre>
                                                </div>
                                            ) : (
                                                <code className={className} {...props}>
                                                    {children}
                                                </code>
                                            )
                                        }
                                    }}
                                >
                                    {msg.content}
                                </ReactMarkdown>
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
                    <button
                        className="control-btn"
                        title="Upload Document"
                        onClick={() => console.log("Clip clicked")}
                    >
                        <Paperclip size={18} />
                    </button>
                    <button
                        className={`control-btn ${webSearchEnabled ? 'active' : ''}`}
                        onClick={() => setWebSearchEnabled(!webSearchEnabled)}
                        title="Web Search"
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
