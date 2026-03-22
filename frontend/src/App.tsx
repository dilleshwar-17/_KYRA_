import { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { 
  Send, 
  Mic, 
  Square, 
  Trash2, 
  Moon, 
  Sun, 
  X, 
  Copy, 
  Check, 
  Code2, 
  FileText, 
  Maximize2, 
  Minimize2,
  Sparkles
} from 'lucide-react';
import AvatarOverlay from './components/AvatarOverlay';

// ─── Detect window mode ────────────────────────────────────────────────────────
const urlMode = new URLSearchParams(window.location.search).get('mode');
const elec = (window as any).electron;
const IS_AVATAR_MODE = urlMode === 'avatar' || elec?.mode === 'avatar';

// ─── Types ────────────────────────────────────────────────────────────────────
interface Artifact {
    title: string;
    type: 'code' | 'markdown';
    language: string;
    content: string;
}

interface Message {
    id: string;
    role: 'user' | 'kyra';
    text: string;
    time: string;
    artifact?: Artifact;
}

const BACKEND_URL = ''; // Relative path, handled by Vite proxy
const WS_URL = `ws://${window.location.host}/ws`;

function timeStr() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
function genId() {
    return Math.random().toString(36).slice(2);
}

// ─── Avatar-Only Mode ─────────────────────────────────────────────────────────
if (IS_AVATAR_MODE) {
    document.documentElement.style.background = 'transparent';
    document.body.style.background = 'transparent';
    const root = document.getElementById('root');
    if (root) root.style.background = 'transparent';
}

// ─── App ──────────────────────────────────────────────────────────────────────
export default function App() {
    if (IS_AVATAR_MODE) return <AvatarOverlay />;
    return <ChatApp />;
}

// ─── Chat App (ClawdBot Style) ───────────────────────────────────────────────
function ChatApp() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isListening, setListening] = useState(false);
    const [status, setStatus] = useState<'connecting' | 'ok' | 'error'>('connecting');
    const [statusText, setStatusText] = useState('Connecting…');
    
    // Artifact State
    const [activeArtifact, setActiveArtifact] = useState<Artifact | null>(null);
    const [isArtifactOpen, setArtifactOpen] = useState(false);
    const [copied, setCopied] = useState(false);
    const [agenticStatus, setAgenticStatus] = useState<string | null>(null);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    // Theme toggle
    const [isDarkMode, setIsDarkMode] = useState(() => {
        const saved = localStorage.getItem('kyra-theme');
        return saved !== 'light';
    });

    useEffect(() => {
        if (isDarkMode) {
            document.documentElement.classList.remove('light');
            localStorage.setItem('kyra-theme', 'dark');
        } else {
            document.documentElement.classList.add('light');
            localStorage.setItem('kyra-theme', 'light');
        }
    }, [isDarkMode]);

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
                if (res.ok) {
                    setStatus('ok');
                    setStatusText('Ready');
                } else {
                    setStatus('error');
                    setStatusText('Backend error — is the server running?');
                }
            } catch {
                setStatus('error');
                setStatusText('Cannot reach backend — run: cd backend && python main.py');
            }
        };
        check();
        const t = setInterval(check, 10000);
        return () => clearInterval(t);
    }, []);

    // Artifact & Agentic Tag Parsing Logic
    const parseMessage = (text: string): { cleanText: string; artifact?: Artifact } => {
        // Remove Agentic Tags first
        let cleanText = text
            .replace(/<FILE_LIST\s+path="[^"]*"\s*\/>/gi, "")
            .replace(/<FILE_READ\s+path="[^"]*"\s*\/>/gi, "")
            .replace(/<FILE_WRITE\s+path="[^"]*"\s*>[\s\S]*?<\/FILE_WRITE>/gi, "")
            .replace(/<FILE_DELETE\s+path="[^"]*"\s*\/>/gi, "")
            .replace(/<CMD_EXEC\s+cmd="[^"]*"\s*\/>/gi, "")
            .replace(/<PY_EXEC>[\s\S]*?<\/PY_EXEC>/gi, "")
            .trim();

        const artifactRegex = /<ARTIFACT\s+title="([^"]*)"\s+type="([^"]*)"\s+language="([^"]*)">([\s\S]*?)<\/ARTIFACT>/i;
        const match = cleanText.match(artifactRegex);
        if (match) {
            const [fullMatch, title, type, language, content] = match;
            cleanText = cleanText.replace(fullMatch, "").trim();
            return {
                cleanText: cleanText || "I've generated an artifact for you.",
                artifact: { title, type: type as any, language, content: content.trim() }
            };
        }
        return { cleanText: cleanText };
    };

    // KYRA state WebSocket
    useEffect(() => {
        const connect = () => {
            const ws = new WebSocket(WS_URL);
            wsRef.current = ws;
            ws.onopen = () => { setStatus('ok'); setStatusText('Ready'); };
            ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                if (data.event === 'state') setListening(data.state === 'listening');
                if (data.event === 'transcript') { 
                    addMessage('user', data.text, data.id); 
                    addTypingIndicator(); 
                }
                if (data.event === 'wakeword') setListening(true);
                if (data.event === 'response') { 
                    removeTypingIndicator(); 
                    const { cleanText, artifact } = parseMessage(data.text);
                    addMessage('kyra', cleanText, data.id, artifact); 
                    if (artifact) {
                        setActiveArtifact(artifact);
                        setArtifactOpen(true);
                    }
                    speak(cleanText); 
                }
                if (data.event === 'error') { removeTypingIndicator(); setListening(false); }
                if (data.event === 'reset') setMessages([]);
                if (data.event === 'agentic_action') {
                    setAgenticStatus(data.status);
                    if (data.status === "Agentic task completed.") {
                        setTimeout(() => setAgenticStatus(null), 3000);
                    }
                }
            };
            ws.onclose = () => setTimeout(connect, 3000);
            ws.onerror = () => ws.close();
        };
        connect();
        return () => wsRef.current?.close();
    }, []);

    // Message helpers
    const addMessage = (role: 'user' | 'kyra', text: string, id?: string, artifact?: Artifact) => {
        setMessages(prev => {
            if (id && prev.some(m => m.id === id)) return prev;
            const isDuplicate = prev.some(m => m.role === role && m.text === text && (m.id !== 'typing'));
            if (isDuplicate && !id) return prev; 
            const newMsg: Message = { id: id || genId(), role, text, time: timeStr(), artifact };
            return [...prev.filter(m => m.id !== 'typing'), newMsg];
        });
    };
    const addTypingIndicator = () => {
        setMessages(prev => {
            if (prev.find(m => m.id === 'typing')) return prev;
            return [...prev, { id: 'typing', role: 'kyra', text: '', time: '' }];
        });
    };
    const removeTypingIndicator = () => setMessages(prev => prev.filter(m => m.id !== 'typing'));

    const sendText = async () => {
        const msg = input.trim();
        if (!msg || status === 'error') return;
        window.speechSynthesis.cancel();
        setInput('');
        addTypingIndicator();
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ action: 'chat', message: msg }));
        }
    };

    const speak = useCallback((text: string) => {
        if (!window.speechSynthesis) return;
        window.speechSynthesis.cancel();
        const cleanText = text.replace(/[*_`#>\[\]]/g, "").replace(/<[^>]*>/g, "").slice(0, 500);
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.rate = 1.05;
        const voices = window.speechSynthesis.getVoices();
        
        // Prefer female voices: Aria, Samantha (Mac), Zira (Windows), Sonia, etc.
        const femaleVoice = voices.find(v => 
            v.name.includes("Aria") || 
            v.name.includes("Samantha") || 
            v.name.includes("Zira") || 
            v.name.includes("Sonia") || 
            v.name.includes("Hazel") ||
            v.name.toLowerCase().includes("female") || 
            v.name.includes("Google US English")
        ) || voices.find(v => v.lang.startsWith("en"));
        
        if (femaleVoice) utterance.voice = femaleVoice;
        window.speechSynthesis.speak(utterance);
    }, []);

    const toggleVoice = () => {
        const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (SR && !isListening) {
            const recog = new SR();
            recog.lang = "en-IN";
            recog.onstart = () => { 
                setListening(true); 
                window.speechSynthesis.cancel();
                if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(JSON.stringify({ action: 'pause_wakeword' }));
            };
            recog.onresult = (e: any) => setInput(e.results[0][0].transcript);
            recog.onend = () => {
                setListening(false);
                if (wsRef.current?.readyState === WebSocket.OPEN) {
                    wsRef.current.send(JSON.stringify({ action: 'resume_wakeword' }));
                    const finalInput = inputRef.current?.value.trim() || "";
                    if (finalInput) {
                        addTypingIndicator();
                        wsRef.current.send(JSON.stringify({ action: 'voice_command', message: finalInput }));
                        setInput('');
                    }
                }
            };
            recog.start();
        } else if (!isListening) {
            wsRef.current?.send(JSON.stringify({ action: 'listen' }));
        }
    };

    const handleCopy = () => {
        if (!activeArtifact) return;
        navigator.clipboard.writeText(activeArtifact.content);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className={`app-container ${isDarkMode ? 'dark' : 'light'}`}>
            {/* ── Title Bar ── */}
            <header className="title-bar">
                <div style={{ display: 'flex', alignItems: 'center', gap: 15 }}>
                    <span className="title-bar-name">KYRA AI</span>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <button onClick={() => setIsDarkMode(!isDarkMode)} className="clear-btn theme-toggle" title="Toggle Theme">
                            {isDarkMode ? <Sun size={14} /> : <Moon size={14} />}
                        </button>
                        <button onClick={() => { try { fetch(`${BACKEND_URL}/reset`, { method: 'POST' }); } catch(e){} setMessages([]); }} className="clear-btn" title="Clear Chat">
                            <Trash2 size={14} />
                        </button>
                    </div>
                </div>
                {elec && (
                    <div className="window-controls">
                        <button className="win-btn min" onClick={() => elec.minimize()}><Minimize2 size={10} color="white"/></button>
                        <button className="win-btn max" onClick={() => elec.toggleMax()}><Maximize2 size={10} color="white"/></button>
                        <button className="win-btn close" onClick={() => elec.close()}><X size={10} color="white"/></button>
                    </div>
                )}
            </header>

            {/* ── Main Body ── */}
            <main className="main-body">
                {/* ── Left Sidebar (Avatar) ── */}
                <aside className="avatar-panel">
                    <div className="avatar-wrapper">
                        <AvatarOverlay isStatic />
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'center' }}>
                        <span className="avatar-state-label">
                            {isListening ? 'Listening' : status === 'ok' ? 'Online' : 'Offline'}
                        </span>
                        <div className="kyra-logo">KYRA</div>
                    </div>
                    
                    <div style={{ marginTop: 'auto', width: '100%', display: 'flex', flexDirection: 'column', gap: 10 }}>
                        <div className="clear-btn" style={{ fontSize: 10, display: 'flex', gap: 8, alignItems: 'center' }}>
                            <Sparkles size={12} color="var(--accent)"/> Functional Artifacts Active
                        </div>
                    </div>
                </aside>

                {/* ── Chat Panel ── */}
                <section className="chat-panel">
                    <div className="chat-messages">
                        {messages.length === 0 ? (
                            <div className="chat-empty">
                                <div className="chat-empty-icon"><Sparkles size={48} /></div>
                                <div className="chat-empty-text">
                                    Hello Boss, what can I do for you?
                                </div>
                            </div>
                        ) : (
                            messages.map(m =>
                                m.id === 'typing' ? (
                                    <div key="typing" className="message kyra">
                                        <div className="message-label">KYRA Thinking</div>
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
                                        <div className="bubble">
                                            <ReactMarkdown>{m.text}</ReactMarkdown>
                                            {m.artifact && (
                                                <div className="artifact-link" onClick={() => { setActiveArtifact(m.artifact!); setArtifactOpen(true); }}>
                                                    {m.artifact.type === 'code' ? <Code2 size={16} /> : <FileText size={16} />}
                                                    <span>View Artifact: {m.artifact.title}</span>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )
                            )
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* ── Input Bar ── */}
                    <footer className="input-bar">
                        <button
                            className={`icon-btn mic ${isListening ? 'active' : ''}`}
                            onClick={toggleVoice}
                        >
                            {isListening ? <Square size={18} fill="currentColor" /> : <Mic size={18} />}
                        </button>
                        <textarea
                            ref={inputRef}
                            className="text-input"
                            placeholder="Type a message or use the mic..."
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendText(); } }}
                            rows={1}
                        />
                        <button
                            className="icon-btn send"
                            onClick={sendText}
                            disabled={!input.trim()}
                        >
                            <Send size={18} />
                        </button>
                    </footer>
                </section>

                {/* ── Artifacts Panel ── */}
                <aside className={`artifacts-panel ${isArtifactOpen ? 'open' : ''}`}>
                    <div className="artifact-header">
                        <div className="artifact-title">
                            {activeArtifact?.type === 'code' ? <Code2 size={16} /> : <FileText size={16} />}
                            {activeArtifact?.title}
                            <span className="artifact-type-tag">{activeArtifact?.language || activeArtifact?.type}</span>
                        </div>
                        <div style={{ display: 'flex', gap: 10 }}>
                            <button className="clear-btn" onClick={handleCopy} title="Copy to Clipboard">
                                {copied ? <Check size={14} color="var(--success)" /> : <Copy size={14} />}
                            </button>
                            <button className="clear-btn" onClick={() => setArtifactOpen(false)} title="Close Panel">
                                <X size={14} />
                            </button>
                        </div>
                    </div>
                    <div className="artifact-body">
                        {activeArtifact?.type === 'code' ? (
                            <SyntaxHighlighter 
                                language={activeArtifact.language} 
                                style={atomDark}
                                customStyle={{ margin: 0, padding: '20px', background: 'transparent', fontSize: '13px' }}
                            >
                                {activeArtifact.content}
                            </SyntaxHighlighter>
                        ) : (
                            <div style={{ padding: '30px' }}>
                                <div className="markdown-body">
                                    <ReactMarkdown>{activeArtifact?.content || ''}</ReactMarkdown>
                                </div>
                            </div>
                        )}
                    </div>
                </aside>
            </main>

            {/* ── Status Bar ── */}
            <footer className="status-bar">
                <div className={`status-dot ${status}`} />
                <span>{statusText}</span>
                {agenticStatus && (
                    <div className="agentic-indicator">
                        <Sparkles size={12} className="spin-slow" />
                        <span>{agenticStatus}</span>
                    </div>
                )}
                <span style={{ marginLeft: 'auto', opacity: 0.5 }}>v1 • KYRA AI</span>
            </footer>
        </div>
    );
}
