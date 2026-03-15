import React, { useState, useEffect, useRef, useCallback } from 'react';
import KyraSpriteAvatar, { AvatarState as SpriteState } from './KyraSpriteAvatar';

const WS_URL = 'ws://localhost:8000/ws';
const EXPR_WS_URL = 'ws://localhost:8000/ws/expression';

export default function AvatarOverlay() {
    const [avatarState, setAvatar] = useState<SpriteState>('idle');
    const [expression, setExpr] = useState<string>('neutral');
    const [mood, setMood] = useState<string>('calm');
    const [sentiment, setSentiment] = useState<number>(0);
    const [kyraState, setKyraState] = useState<SpriteState>('idle');
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
                        setExpr(data.expression);
                        // Also map some expressions to mood
                        if (data.expression === 'happy') setMood('excited');
                        else if (data.expression === 'angry') setMood('upset');
                        else setMood('calm');

                        // Only override avatar state if KYRA isn't talking/thinking
                        setKyraState(currentKyra => {
                            if (currentKyra === 'talking' || currentKyra === 'thinking' || currentKyra === 'listening') return currentKyra;
                            setAvatar('idle'); // We now use userExpression prop for face, avatarState for body/glow
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

    // ── KYRA state via WebSocket ─────────────────────────────────────────────
    useEffect(() => {
        const kyraWs = new WebSocket(WS_URL);

        kyraWs.onmessage = (e) => {
            try {
                const data = JSON.parse(e.data);
                if (data.event === 'state') {
                    const s = data.state as SpriteState;
                    setKyraState(s);
                    setAvatar(s);
                }
                if (data.event === 'sentiment') {
                    setSentiment(data.score || 0);
                    if (data.score > 0.4) setMood('excited');
                    else if (data.score < -0.4) setMood('upset');
                }
            } catch { /* ignore */ }
        };

        kyraWs.onclose = () => { };
        return () => kyraWs.close();
    }, []);

    // ── Electron expression IPC (fallback) ──────────────────────────────────
    useEffect(() => {
        if (!elec?.onExpression) return;
        elec.onExpression((emotion: string) => {
            setExpr(emotion);
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
    const glowMap: Record<SpriteState, string> = {
        idle: '#00dcff',
        listening: '#ff4d6d',
        thinking: '#f7c94b',
        talking: '#00e5a0',
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
                <KyraSpriteAvatar 
                    state={avatarState} 
                    userExpression={expression}
                    userMood={mood}
                    voiceSentiment={sentiment}
                    size={200} 
                />
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
