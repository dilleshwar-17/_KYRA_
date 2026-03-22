import React, { useState, useEffect, useRef, useCallback } from 'react';
import KyraSpriteAvatar, { AvatarState as SpriteState } from './KyraSpriteAvatar';

const WS_URL = 'ws://127.0.0.1:8091/ws';
const EXPR_WS_URL = 'ws://127.0.0.1:8091/ws/expression';

interface AvatarOverlayProps {
    isStatic?: boolean;
}

export default function AvatarOverlay({ isStatic = false }: AvatarOverlayProps) {
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
                        if (data.expression === 'happy') setMood('excited');
                        else if (data.expression === 'angry') setMood('upset');
                        else setMood('calm');

                        setKyraState(currentKyra => {
                            if (currentKyra === 'talking' || currentKyra === 'thinking' || currentKyra === 'listening') return currentKyra;
                            setAvatar('idle'); 
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
        return () => kyraWs.close();
    }, []);

    // ── Drag logic ───────────────────────────────────────────────────────────
    const onMouseDown = useCallback((e: React.MouseEvent) => {
        if (isStatic || e.button !== 0) return;
        setDragging(true);
        dragStart.current = { x: e.screenX, y: e.screenY };
    }, [isStatic]);

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

    // ── Colors from index.css ────────────────────────────────────────────────
    const glowMap: Record<SpriteState, string> = {
        idle: '#6366f1',      // Indigo
        listening: '#ef4444',  // Red/Danger
        thinking: '#fbbf24',   // Amber
        talking: '#10b981',    // Emerald/Success
    };
    const glow = glowMap[avatarState] ?? '#6366f1';

    return (
        <div
            id="avatar-overlay-root"
            onMouseDown={onMouseDown}
            onMouseMove={onMouseMove}
            onMouseUp={onMouseUp}
            onMouseLeave={onMouseUp}
            onClick={(e) => { if (!isStatic && e.detail === 3) elec?.openChat(); }}
            style={{
                width: isStatic ? '100%' : '100vw',
                height: isStatic ? '100%' : '100vh',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                background: 'transparent',
                cursor: isStatic ? 'default' : (isDragging ? 'grabbing' : 'grab'),
                userSelect: 'none',
            }}
        >
            <div style={{
                position: 'relative',
                filter: `drop-shadow(0 0 15px ${glow})`,
                transition: 'filter 0.4s ease',
            }}>
                <KyraSpriteAvatar 
                    state={avatarState} 
                    userExpression={expression}
                    userMood={mood}
                    voiceSentiment={sentiment}
                    size={isStatic ? 160 : 200} 
                />
            </div>

            {!isStatic && (
                <div style={{
                    marginTop: 8,
                    color: glow,
                    fontSize: 11,
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
            )}
        </div>
    );
}
