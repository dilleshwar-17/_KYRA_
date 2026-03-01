import React, { useState, useEffect, useRef, useCallback } from 'react';
import AvatarFace, { AvatarState } from './components/AvatarFace';
import AvatarOverlay from './components/AvatarOverlay';

// ─── Detect window mode ────────────────────────────────────────────────────────
// Electron passes ?mode=avatar or ?mode=chat via loadURL / loadFile query
const urlMode = new URLSearchParams(window.location.search).get('mode');
const elec = (window as any).electron;
const IS_AVATAR_MODE = urlMode === 'avatar' || elec?.mode === 'avatar';

// ─── Types ────────────────────────────────────────────────────────────────────
interface Message {
    id: string;
    role: 'user' | 'kyra';
    text: string;
    time: string;
}

const BACKEND_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

function timeStr() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
function genId() {
    return Math.random().toString(36).slice(2);
}

// ─── Avatar-Only Mode ─────────────────────────────────────────────────────────
if (IS_AVATAR_MODE) {
    // Transparent overlay — remove solid background from root
    document.documentElement.style.background = 'transparent';
    document.body.style.background = 'transparent';
    const root = document.getElementById('root');
    if (root) root.style.background = 'transparent';
}

// ─── App ──────────────────────────────────────────────────────────────────────
export default function App() {
    // In avatar mode we just render the overlay
    if (IS_AVATAR_MODE) {
        return <AvatarOverlay />;
    }

    return <ChatApp />;
}

// ─── Chat App (full UI) ───────────────────────────────────────────────────────
function ChatApp() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [avatarState, setAvatar] = useState<AvatarState>('idle');
    const [isListening, setListening] = useState(false);
    const [status, setStatus] = useState<'connecting' | 'ok' | 'error'>('connecting');
    const [statusText, setStatusText] = useState('Connecting…');


    const messagesEndRef = useRef<HTMLDivElement>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // Scroll to bottom
    const scrollBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, []);
    useEffect(scrollBottom, [messages, scrollBottom]);

    // Health check
    useEffect(() => {
        const check = async () => {
            try {
                const res = await fetch(`${BACKEND_URL}/health`);
                if (res.ok) { setStatus('ok'); setStatusText('Ready'); }
                else { setStatus('error'); setStatusText('Backend error — is the server running?'); }
            } catch {
                setStatus('error');
                setStatusText('Cannot reach backend — run: cd backend && python main.py');
            }
        };
        check();
        const t = setInterval(check, 15000);
        return () => clearInterval(t);
    }, []);

    // KYRA state WebSocket
    useEffect(() => {
        const connect = () => {
            const ws = new WebSocket(WS_URL);
            wsRef.current = ws;

            ws.onopen = () => { setStatus('ok'); setStatusText('Ready'); };

            ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                if (data.event === 'state') {
                    setAvatar(data.state as AvatarState);
                    setListening(data.state === 'listening');
                }
                if (data.event === 'transcript') { addMessage('user', data.text); addTypingIndicator(); }
                if (data.event === 'response') { removeTypingIndicator(); addMessage('kyra', data.text); }
                if (data.event === 'error') { removeTypingIndicator(); setAvatar('idle'); setListening(false); }
                if (data.event === 'reset') { setMessages([]); setAvatar('idle'); }
            };

            ws.onclose = () => { setTimeout(connect, 3000); };
            ws.onerror = () => { ws.close(); };
        };
        connect();
        return () => { wsRef.current?.close(); };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Message helpers
    const addMessage = (role: 'user' | 'kyra', text: string) => {
        setMessages(prev => [...prev.filter(m => m.id !== 'typing'), { id: genId(), role, text, time: timeStr() }]);
    };
    const addTypingIndicator = () => {
        setMessages(prev => {
            if (prev.find(m => m.id === 'typing')) return prev;
            return [...prev, { id: 'typing', role: 'kyra', text: '', time: '' }];
        });
    };
    const removeTypingIndicator = () => setMessages(prev => prev.filter(m => m.id !== 'typing'));

    // Send text
    const sendText = async () => {
        const msg = input.trim();
        if (!msg || status === 'error') return;
        setInput('');
        addMessage('user', msg);
        addTypingIndicator();
        setAvatar('thinking');
        try {
            const res = await fetch(`${BACKEND_URL}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg }),
            });
            const data = await res.json();
            removeTypingIndicator();
            addMessage('kyra', data.response);
            setAvatar('talking');
            setTimeout(() => setAvatar('idle'), 2500);
        } catch {
            removeTypingIndicator();
            addMessage('kyra', 'Sorry, I could not reach the backend. Is the server running?');
            setAvatar('idle');
        }
    };

    // Voice
    const toggleVoice = () => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
        if (!isListening) wsRef.current.send(JSON.stringify({ action: 'listen' }));
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendText(); }
    };

    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            if (e.code === 'Space' && document.activeElement !== inputRef.current) {
                e.preventDefault(); toggleVoice();
            }
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isListening]);

    const clearChat = async () => {
        try { await fetch(`${BACKEND_URL}/reset`, { method: 'POST' }); } catch { /* ignore */ }
        setMessages([]); setAvatar('idle');
    };

    const stateLabel = {
        idle: 'Idle',
        neutral: 'Neutral',
        listening: '● Listening',
        thinking: '⟳ Thinking',
        talking: '▶ Speaking',
        happy: '😊 Happy',
        sad: '😢 Sad',
        angry: '😠 Angry',
        surprised: '😲 Surprised',
    }[avatarState] ?? 'Idle';



    return (
        <div className="app-container">
            {/* ── Title Bar ── */}
            <div className="title-bar">
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span className="title-bar-name">KYRA</span>
                </div>
                {elec && (
                    <div className="window-controls">
                        <button className="win-btn min" onClick={() => elec.minimize()} title="Minimize" />
                        <button className="win-btn max" onClick={() => elec.toggleMax()} title="Maximize" />
                        <button className="win-btn close" onClick={() => elec.close()} title="Close" />
                    </div>
                )}
            </div>

            {/* ── Main Body ── */}
            <div className="main-body">
                {/* ── Avatar ── */}
                <div className="avatar-panel">
                    <div className="kyra-logo">KYRA</div>
                    <div className="avatar-wrapper">
                        <AvatarFace state={avatarState} />
                    </div>
                    <div className="avatar-state-label">{stateLabel}</div>

                    <button
                        onClick={clearChat}
                        style={{
                            marginTop: 8, background: 'transparent',
                            border: '1px solid var(--border)', borderRadius: 8,
                            padding: '6px 18px', color: 'var(--text-secondary)',
                            fontSize: 12, cursor: 'pointer', transition: 'all 0.2s',
                            fontFamily: 'var(--font)',
                        }}
                        onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--accent)'; (e.currentTarget as HTMLButtonElement).style.color = 'var(--accent)'; }}
                        onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--border)'; (e.currentTarget as HTMLButtonElement).style.color = 'var(--text-secondary)'; }}
                    >
                        Clear Chat
                    </button>
                </div>

                {/* ── Chat ── */}
                <div className="chat-panel">
                    <div className="chat-messages">
                        {messages.length === 0 ? (
                            <div className="chat-empty">
                                <div className="chat-empty-icon">✨</div>
                                <div className="chat-empty-text">
                                    Say hello to KYRA!<br />
                                    Type below or press <strong>Space</strong> to speak.
                                </div>
                            </div>
                        ) : (
                            messages.map(m =>
                                m.id === 'typing' ? (
                                    <div key="typing" className="message kyra">
                                        <div className="message-label">KYRA</div>
                                        <div className="typing-dots">
                                            <span className="typing-dot" />
                                            <span className="typing-dot" />
                                            <span className="typing-dot" />
                                        </div>
                                    </div>
                                ) : (
                                    <div key={m.id} className={`message ${m.role}`}>
                                        <div className="message-label">
                                            {m.role === 'user' ? `You • ${m.time}` : `KYRA • ${m.time}`}
                                        </div>
                                        <div className="bubble">{m.text}</div>
                                    </div>
                                )
                            )
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* ── Input Bar ── */}
                    <div className="input-bar">
                        <button
                            className={`icon-btn mic ${isListening ? 'active' : ''}`}
                            onClick={toggleVoice}
                            title={isListening ? 'Listening…' : 'Click or press Space to speak'}
                        >
                            {isListening ? '⏹' : '🎤'}
                        </button>
                        <textarea
                            ref={inputRef}
                            className="text-input"
                            placeholder="Ask KYRA anything… (Enter to send, Shift+Enter for newline)"
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            rows={1}
                        />
                        <button
                            className="icon-btn send"
                            onClick={sendText}
                            disabled={!input.trim() || status === 'error'}
                            title="Send"
                        >
                            ➤
                        </button>
                    </div>
                </div>
            </div>

            {/* ── Status Bar ── */}
            <div className="status-bar">
                <div className={`status-dot ${status}`} />
                <span style={{ fontSize: 11 }}>{statusText}</span>
            </div>
        </div>
    );
}
