import React from 'react';

export type AvatarState =
    | 'idle' | 'listening' | 'thinking' | 'talking'
    // User expression states via OpenCV / DeepFace
    | 'happy' | 'sad' | 'angry' | 'surprised' | 'neutral';

interface AvatarFaceProps {
    state: AvatarState;
    size?: number;   // default 180
}

const AvatarFace: React.FC<AvatarFaceProps> = ({ state, size = 180 }) => {

    // ── Eye blink ────────────────────────────────────────────────────────────
    const [eyeScale, setEyeScale] = React.useState(1);

    React.useEffect(() => {
        const id = setInterval(() => {
            setEyeScale(0.1);
            setTimeout(() => setEyeScale(1), 120);
        }, 2400 + Math.random() * 2000);
        return () => clearInterval(id);
    }, []);

    // ── Surprised wide-eye scale ─────────────────────────────────────────────
    const eyeRy = state === 'surprised' ? 14 : 11 * eyeScale;
    const irisRy = state === 'surprised' ? 10 : 7.5 * eyeScale;

    // ── Animation ────────────────────────────────────────────────────────────
    const avatarAnim =
        state === 'idle' || state === 'neutral' ? 'breathe 3.5s ease-in-out infinite' :
            state === 'talking' ? 'talking-bob 0.55s ease-in-out infinite' :
                state === 'thinking' ? 'breathe 1.5s ease-in-out infinite' :
                    state === 'happy' ? 'happy-bounce 0.8s ease-in-out infinite' :
                        state === 'surprised' ? 'none' :
                            state === 'sad' ? 'breathe 5s ease-in-out infinite' :
                                state === 'angry' ? 'talking-bob 0.3s ease-in-out infinite' :
                                    'none';

    // ── Glow / iris colour per state ─────────────────────────────────────────
    const colours: Record<AvatarState, { glow: string; iris: string }> = {
        idle: { glow: 'rgba(0,220,255,0.4)', iris: '#00dcff' },
        neutral: { glow: 'rgba(170,170,170,0.3)', iris: '#aaaaaa' },
        listening: { glow: 'rgba(255,77,109,0.6)', iris: '#ff4d6d' },
        thinking: { glow: 'rgba(247,201,75,0.5)', iris: '#f7c94b' },
        talking: { glow: 'rgba(0,229,160,0.5)', iris: '#00e5a0' },
        happy: { glow: 'rgba(255,215,0,0.6)', iris: '#ffd700' },
        sad: { glow: 'rgba(102,153,204,0.5)', iris: '#6699cc' },
        angry: { glow: 'rgba(255,68,68,0.7)', iris: '#ff4444' },
        surprised: { glow: 'rgba(255,159,67,0.6)', iris: '#ff9f43' },
    };

    const { glow: glowColor, iris: irisColor } = colours[state] ?? colours.idle;

    // ── Eyebrow shapes ────────────────────────────────────────────────────────
    // angry: lowered inner brows; sad: raised inner brows; surprised: raised all
    const browLeft =
        state === 'angry' ? 'M62 84 Q76 80 88 86' :
            state === 'sad' ? 'M62 90 Q76 84 88 90' :
                state === 'surprised' ? 'M60 83 Q76 76 90 82' :
                    'M62 88 Q76 82 88 86';

    const browRight =
        state === 'angry' ? 'M112 86 Q124 80 138 84' :
            state === 'sad' ? 'M112 90 Q124 84 138 90' :
                state === 'surprised' ? 'M110 82 Q124 76 140 83' :
                    'M112 86 Q124 82 138 88';

    // ── Mouth shapes ──────────────────────────────────────────────────────────
    const renderMouth = () => {
        switch (state) {
            case 'talking':
                return (
                    <>
                        <path d="M82 140 Q100 148 118 140" stroke="#4a7a90" strokeWidth="1.5" fill="none" strokeLinecap="round" />
                        <ellipse cx="100" cy="143" rx="14" ry="7" fill="#091520" />
                        <path d="M87 143 Q100 147 113 143" stroke="#8a3050" strokeWidth="1.5" fill="none" />
                    </>
                );
            case 'listening':
                return (
                    <>
                        <path d="M82 140 Q100 148 118 140" stroke="#4a7a90" strokeWidth="1" fill="none" strokeLinecap="round" />
                        <ellipse cx="100" cy="141" rx="12" ry="4" fill="#091520" />
                    </>
                );
            case 'happy':
                return (
                    <>
                        <path d="M78 136 Q100 158 122 136" stroke={irisColor} strokeWidth="2.5" fill="none" strokeLinecap="round" />
                        {/* Cheek highlights for happy */}
                    </>
                );
            case 'sad':
                return (
                    <path d="M82 148 Q100 138 118 148" stroke={irisColor} strokeWidth="2" fill="none" strokeLinecap="round" />
                );
            case 'angry':
                return (
                    <path d="M84 144 Q100 140 116 144" stroke={irisColor} strokeWidth="2" fill="none" strokeLinecap="round" />
                );
            case 'surprised':
                return (
                    <>
                        <ellipse cx="100" cy="148" rx="12" ry="10" fill="#091520" />
                        <path d="M88 148 Q100 155 112 148" stroke="#8a3050" strokeWidth="1" fill="none" />
                    </>
                );
            default:
                // Gentle smile
                return (
                    <>
                        <path d="M82 138 Q100 150 118 138" stroke="none" fill="#8a3050" />
                        <path d="M82 138 Q100 150 118 138" stroke="#4a7a90" strokeWidth="1.5" fill="none" strokeLinecap="round" />
                    </>
                );
        }
    };

    return (
        <div style={{ position: 'relative', width: size, height: size }}>
            {/* Pulse rings for listening */}
            {state === 'listening' && (
                <>
                    <div style={{
                        position: 'absolute', inset: 0, borderRadius: '50%',
                        border: '2px solid rgba(255,77,109,0.6)',
                        animation: 'pulse-ring 1.2s cubic-bezier(0.215,0.61,0.355,1) infinite',
                    }} />
                    <div style={{
                        position: 'absolute', inset: 0, borderRadius: '50%',
                        border: '2px solid rgba(255,77,109,0.4)',
                        animation: 'pulse-ring 1.2s cubic-bezier(0.215,0.61,0.355,1) 0.4s infinite',
                    }} />
                </>
            )}

            {/* Happy sparkles */}
            {state === 'happy' && (
                <>
                    {[...Array(4)].map((_, i) => (
                        <div key={i} style={{
                            position: 'absolute',
                            top: `${[10, 5, 15, 8][i]}%`,
                            left: `${[80, 15, 75, 20][i]}%`,
                            width: 6, height: 6, borderRadius: '50%',
                            background: irisColor,
                            animation: `sparkle ${0.8 + i * 0.2}s ${i * 0.15}s ease-in-out infinite`,
                            boxShadow: `0 0 8px ${irisColor}`,
                        }} />
                    ))}
                </>
            )}

            <svg
                viewBox="0 0 200 200"
                style={{
                    animation: avatarAnim,
                    transition: 'all 0.4s ease',
                    width: '100%',
                    height: '100%',
                }}
                xmlns="http://www.w3.org/2000/svg"
            >
                <defs>
                    <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
                        <feGaussianBlur stdDeviation="6" result="coloredBlur" />
                        <feMerge>
                            <feMergeNode in="coloredBlur" />
                            <feMergeNode in="SourceGraphic" />
                        </feMerge>
                    </filter>
                    <radialGradient id="faceGrad" cx="45%" cy="40%" r="60%">
                        <stop offset="0%" stopColor="#1a2a3a" />
                        <stop offset="100%" stopColor="#0a131f" />
                    </radialGradient>
                    <linearGradient id="hairGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#0d1b2e" />
                        <stop offset="100%" stopColor="#050d1a" />
                    </linearGradient>
                    <linearGradient id="spinGrad" x1="0" y1="0" x2="1" y2="1">
                        <stop offset="0%" stopColor={irisColor} stopOpacity="0" />
                        <stop offset="100%" stopColor={irisColor} />
                    </linearGradient>
                </defs>

                {/* Outer glow ring */}
                <circle cx="100" cy="100" r="92"
                    fill="none" stroke={glowColor} strokeWidth="1.5"
                    filter="url(#glow)"
                    opacity={state === 'idle' || state === 'neutral' ? 0.5 : 0.9}
                />

                {/* Neck */}
                <rect x="84" y="166" width="32" height="26" rx="6" fill="#1a2a3a" />

                {/* Head */}
                <ellipse cx="100" cy="105" rx="68" ry="76" fill="url(#faceGrad)" />

                {/* Hair */}
                <ellipse cx="100" cy="55" rx="68" ry="30" fill="url(#hairGrad)" />
                <path d="M32 90 Q18 140 28 180 Q40 170 44 150 Q48 130 44 100 Z" fill="url(#hairGrad)" />
                <path d="M168 90 Q182 140 172 180 Q160 170 156 150 Q152 130 156 100 Z" fill="url(#hairGrad)" />
                <path d="M36 82 Q60 38 100 34 Q140 38 164 82" fill="url(#hairGrad)" />

                {/* Eyebrows */}
                <path d={browLeft} stroke={state === 'angry' ? '#ff4444' : '#c8dae8'} strokeWidth="2.5" strokeLinecap="round" fill="none" />
                <path d={browRight} stroke={state === 'angry' ? '#ff4444' : '#c8dae8'} strokeWidth="2.5" strokeLinecap="round" fill="none" />

                {/* Eyes */}
                {/* Left */}
                <ellipse cx="75" cy="104" rx="14" ry={eyeRy} fill="#d8ecf5" />
                <ellipse cx="75" cy="104" rx="9" ry={irisRy} fill={irisColor} filter="url(#glow)" />
                <ellipse cx="75" cy="104" rx="4" ry={irisRy * 0.47} fill="#050d1a" />
                <ellipse cx="78" cy="101" rx="2.5" ry={irisRy * 0.27} fill="white" opacity="0.9" />
                {/* Right */}
                <ellipse cx="125" cy="104" rx="14" ry={eyeRy} fill="#d8ecf5" />
                <ellipse cx="125" cy="104" rx="9" ry={irisRy} fill={irisColor} filter="url(#glow)" />
                <ellipse cx="125" cy="104" rx="4" ry={irisRy * 0.47} fill="#050d1a" />
                <ellipse cx="128" cy="101" rx="2.5" ry={irisRy * 0.27} fill="white" opacity="0.9" />

                {/* Nose */}
                <path d="M96 116 Q100 125 104 116" stroke="#6a8fa0" strokeWidth="1.5" fill="none" strokeLinecap="round" />

                {/* Mouth */}
                {renderMouth()}

                {/* Thinking ring */}
                {state === 'thinking' && (
                    <circle cx="100" cy="100" r="78"
                        fill="none" stroke="url(#spinGrad)"
                        strokeWidth="3" strokeDasharray="80 220"
                        style={{ animation: 'thinking-spin 1.2s linear infinite', transformOrigin: '100px 100px' }}
                    />
                )}

                {/* Sad tear drops */}
                {state === 'sad' && (
                    <>
                        <ellipse cx="78" cy="118" rx="2" ry="3" fill="#6699cc" opacity="0.7" style={{ animation: 'tear-fall 2s ease-in infinite' }} />
                        <ellipse cx="122" cy="118" rx="2" ry="3" fill="#6699cc" opacity="0.7" style={{ animation: 'tear-fall 2s 0.5s ease-in infinite' }} />
                    </>
                )}

                {/* Angry red tint on cheeks */}
                {state === 'angry' && (
                    <>
                        <ellipse cx="58" cy="118" rx="14" ry="9" fill="rgba(255,68,68,0.2)" />
                        <ellipse cx="142" cy="118" rx="14" ry="9" fill="rgba(255,68,68,0.2)" />
                    </>
                )}

                {/* Cheek blush (idle / happy) */}
                {(state === 'idle' || state === 'happy' || state === 'neutral') && (
                    <>
                        <ellipse cx="60" cy="120" rx="12" ry="7" fill={state === 'happy' ? 'rgba(255,215,0,0.15)' : 'rgba(220,100,120,0.12)'} />
                        <ellipse cx="140" cy="120" rx="12" ry="7" fill={state === 'happy' ? 'rgba(255,215,0,0.15)' : 'rgba(220,100,120,0.12)'} />
                    </>
                )}
            </svg>
        </div>
    );
};

export default AvatarFace;
