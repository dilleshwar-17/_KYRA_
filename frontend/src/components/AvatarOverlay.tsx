import React, { useState, useEffect, useRef, useCallback } from 'react';
import AvatarFace, { AvatarState } from './AvatarFace';

// Map DeepFace emotions → AvatarState
const EMOTION_MAP: Record<string, AvatarState> = {
    happy: 'happy',
    sad: 'sad',
    angry: 'angry',
    surprise: 'surprised',
    surprised: 'surprised',
    neutral: 'idle',
    fear: 'idle',
    disgust: 'idle',
};

const WS_URL = 'ws://localhost:8000/ws';
const EXPR_WS_URL = 'ws://localhost:8000/ws/expression';

export default function AvatarOverlay() {
    const [avatarState, setAvatar] = useState<AvatarState>('idle');
    const [expression, setExpr] = useState<string>('neutral');
    const [kyraState, setKyraState] = useState<AvatarState>('idle');  // KYRA's own state (talking etc.)
    const [isDragging, setDragging] = useState(false);
    const dragStart = useRef<{ x: number; y: number } | null>(null);

    const elec = (window as any).electron;

    // ── DeepFace expression WebSocket ────────────────────────────────────────
    useEffect(() => {
        let ws: WebSocket | null = null;
        let retry: ReturnType<typeof setTimeout>;

        const connect = () => {
            ws = new WebSocket(EXPR_WS_URL);

            ws.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data);
                    if (data.expression) {
                        const mapped = EMOTION_MAP[data.expression] ?? 'idle';
                        setExpr(data.expression);
                        // Only override avatar if KYRA isn't talking/thinking
                        setKyraState(currentKyra => {
                            if (currentKyra === 'talking' || currentKyra === 'thinking') return currentKyra;
                            setAvatar(mapped);
                            return currentKyra;
                        });
                    }
                } catch { /* ignore */ }
            };

            ws.onclose = () => { retry = setTimeout(connect, 3000); };
            ws.onerror = () => ws?.close();
        };

        connect();
        return () => { ws?.close(); clearTimeout(retry); };
    }, []);

    // ── KYRA state via electron IPC (expression:update from main.js) ─────────
    useEffect(() => {
        const kyraWs = new WebSocket(WS_URL);

        kyraWs.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                if (data.event === 'state') {
                    const s = data.state as AvatarState;
                    setKyraState(s);
                    // KYRA states override expression states
                    if (s === 'talking' || s === 'thinking' || s === 'listening') {
                        setAvatar(s);
                    } else {
                        // Return to expression-based state
                        setAvatar(EMOTION_MAP[expression] ?? 'idle');
                    }
                }
            } catch { /* ignore */ }
        };

        kyraWs.onclose = () => { };
        return () => kyraWs.close();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [expression]);

    // ── Electron expression IPC (forwarded from backend via main process) ────
    useEffect(() => {
        if (!elec?.onExpression) return;
        elec.onExpression((emotion: string) => {
            const mapped = EMOTION_MAP[emotion] ?? 'idle';
            setExpr(emotion);
            setAvatar(prev =>
                (prev === 'talking' || prev === 'thinking' || prev === 'listening')
                    ? prev : mapped
            );
        });
        return () => elec.removeExpressionListener?.();
    }, [elec]);

    // ── Drag to move window ───────────────────────────────────────────────────
    const onMouseDown = useCallback((e: React.MouseEvent) => {
        if (e.button !== 0) return;
        setDragging(true);
        dragStart.current = { x: e.screenX, y: e.screenY };
    }, []);

    const onMouseMove = useCallback((e: React.MouseEvent) => {
        if (!isDragging || !dragStart.current) return;
        const dx = e.screenX - dragStart.current.x;
        const dy = e.screenY - dragStart.current.y;
        dragStart.current = { x: e.screenX, y: e.screenY };
        elec?.dragAvatar(dx, dy);
    }, [isDragging, elec]);

    const onMouseUp = useCallback(() => {
        setDragging(false);
        dragStart.current = null;
    }, []);

    // ── Right-click context menu: open chat ───────────────────────────────────
    const onContextMenu = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        elec?.openChat();
    }, [elec]);



    // ── Glow colour per state ────────────────────────────────────────────────
    const glowMap: Record<AvatarState, string> = {
        idle: '#00dcff',
        listening: '#ff4d6d',
        thinking: '#f7c94b',
        talking: '#00e5a0',
        happy: '#ffd700',
        sad: '#6699cc',
        angry: '#ff4444',
        surprised: '#ff9f43',
        neutral: '#aaaaaa',
    };
    const glow = glowMap[avatarState] ?? '#00dcff';

    return (
        <div
            id="avatar-overlay-root"
            onMouseDown={onMouseDown}
            onMouseMove={onMouseMove}
            onMouseUp={onMouseUp}
            onMouseLeave={onMouseUp}
            onContextMenu={onContextMenu}
            style={{
                width: '100vw',
                height: '100vh',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'transparent',
                cursor: isDragging ? 'grabbing' : 'grab',
                userSelect: 'none',
            }}
        >
            {/* Outer glow halo */}
            <div style={{
                position: 'relative',
                filter: `drop-shadow(0 0 20px ${glow}) drop-shadow(0 0 40px ${glow}55)`,
                transition: 'filter 0.4s ease',
            }}>
                <AvatarFace state={avatarState} size={200} />
            </div>

            {/* State label */}
            <div style={{
                marginTop: 8,
                color: glow,
                fontSize: 11,
                fontFamily: "'Inter', 'Segoe UI', sans-serif",
                fontWeight: 600,
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                textShadow: `0 0 10px ${glow}`,
                transition: 'color 0.4s ease',
            }}>
                {kyraState === 'talking' ? '▶' :
                    kyraState === 'thinking' ? '⟳' :
                        kyraState === 'listening' ? '●' :
                            ''}
            </div>

            {/* Hint */}
            <div style={{
                marginTop: 4,
                color: 'rgba(255,255,255,0.3)',
                fontSize: 9,
                fontFamily: "'Inter', sans-serif",
                letterSpacing: '0.05em',
            }}>
                Right-click to chat
            </div>
        </div>
    );
}
