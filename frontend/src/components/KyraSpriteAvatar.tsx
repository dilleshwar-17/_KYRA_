import React, { useEffect, useRef } from 'react';

export type AvatarState = 'idle' | 'talking' | 'listening' | 'thinking';

interface KyraSpriteAvatarProps {
    state: AvatarState;
    userExpression?: string; // e.g., 'happy', 'sad', 'surprised', 'neutral'
    userMood?: string;       // e.g., 'calm', 'excited', 'upset'
    voiceSentiment?: number; // -1 to 1
    size?: number;
}

const KyraSpriteAvatar: React.FC<KyraSpriteAvatarProps> = ({ 
    state, 
    userExpression = 'neutral', 
    userMood = 'calm',
    voiceSentiment = 0,
    size = 200 
}) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const imagesRef = useRef<Record<string, HTMLImageElement>>({});
    const stateRef = useRef<AvatarState>(state);
    const expressionRef = useRef<string>(userExpression);
    const animationFrameRef = useRef<number>();

    // Animation state variables
    const animData = useRef({
        lastTs: 0,
        breathPhase: 0,
        swayPhase: 0,
        blinkPhase: 'none' as 'none' | 'closing' | 'closed' | 'opening',
        blinkTimer: 0,
        nextBlink: 3000 + Math.random() * 2000,
        talkTimer: 0,
        talkIdx: 0,
        talkMouths: [0, 0.3, 0.7, 1.0, 0.7, 0.3],
        blinkInterval: 3200,
        talkSpeed: 150,
        reactionTilt: 0,
        targetReactionTilt: 0
    });

    useEffect(() => {
        stateRef.current = state;
    }, [state]);

    useEffect(() => {
        expressionRef.current = userExpression;
        // React to user expression with a slight tilt or shift
        if (userExpression === 'surprised') {
            animData.current.targetReactionTilt = -5;
        } else if (userExpression === 'happy') {
            animData.current.targetReactionTilt = 3;
        } else {
            animData.current.targetReactionTilt = 0;
        }
    }, [userExpression]);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Load all expression images
        // Load the original image
        const img = new Image();
        img.src = '/kyra_front.png';
        imagesRef.current['neutral'] = img; // We keep 'neutral' as the key to avoid changing drawing logic too much

        const CW = canvas.width;
        const CH = canvas.height;

        const drawBase = (tiltDeg = 0, scaleY = 1, oy = 0, currentExpr = 'neutral') => {
            ctx.clearRect(0, 0, CW, CH);
            const img = imagesRef.current[currentExpr] || imagesRef.current['neutral'];
            if (!img || !img.complete || img.naturalWidth === 0) return;

            ctx.save();
            const px = CW / 2, py = CH * 0.22;
            ctx.translate(px, py);
            
            // Apply reaction tilt + procedural tilt
            ctx.rotate((tiltDeg + animData.current.reactionTilt) * Math.PI / 180);
            
            ctx.scale(1, scaleY);
            ctx.translate(-px, -py);

            const s = Math.min(CW / img.naturalWidth, (CH - 10) / img.naturalHeight) * 0.96;
            const dw = img.naturalWidth * s;
            const dh = img.naturalHeight * s;
            const dx = (CW - dw) / 2;
            const dy = CH - dh - 5 + oy;
            
            // Basic background removal if white
            // For now just draw, as white might be fine in certain themes
            ctx.drawImage(img, 0, 0, img.naturalWidth, img.naturalHeight, dx, dy, dw, dh);
            ctx.restore();
        };

        const drawBlink = (amount: number) => {
            const img = imagesRef.current['neutral'];
            if (amount <= 0 || !img || !img.complete) return;
            const s = Math.min(CW / img.naturalWidth, (CH - 10) / img.naturalHeight) * 0.96;
            const dw = img.naturalWidth * s;
            const dh = img.naturalHeight * s;
            const dx = (CW - dw) / 2;
            const dy = CH - dh - 5;

            ctx.save();
            ctx.fillStyle = '#b4845a';
            const ey = dy + dh * 0.20;
            const eh = dh * 0.035 * amount;
            const ew = dw * 0.15;
            [[dx + dw * 0.32, ey], [dx + dw * 0.58, ey]].forEach(([ex]) => {
                ctx.beginPath();
                ctx.ellipse(ex + ew / 2, ey + eh / 2, ew / 2, eh / 2 + 1, 0, 0, Math.PI * 2);
                ctx.fill();
            });
            ctx.restore();
        };

        const drawProceduralFace = (expression: string, mouthOpenness: number) => {
            const img = imagesRef.current['neutral'];
            if (!img || !img.complete) return;
            const s = Math.min(CW / img.naturalWidth, (CH - 10) / img.naturalHeight) * 0.96;
            const dw = img.naturalWidth * s, dh = img.naturalHeight * s;
            const dx = (CW - dw) / 2, dy = CH - dh - 5;

            const leftEyeX = dx + dw * 0.32;
            const rightEyeX = dx + dw * 0.58;

            const mouthX = dx + dw * 0.44;
            const mouthY = dy + dh * 0.285;
            const mouthW = dw * 0.18;

            ctx.save();

            // --- 1. Patch over existing mouth if expression changed ---
            if (expression !== 'neutral' || mouthOpenness > 0) {
                const g = ctx.createRadialGradient(mouthX, mouthY, 2, mouthX, mouthY, mouthW/1.2);
                g.addColorStop(0, 'rgba(238, 187, 145, 1)'); // Custom skin tone match
                g.addColorStop(1, 'rgba(238, 187, 145, 0)');
                ctx.fillStyle = g;
                ctx.beginPath();
                ctx.ellipse(mouthX, mouthY + 1, mouthW/1.2, dh * 0.025, 0, 0, Math.PI * 2);
                ctx.fill();
            }

            // --- 2. Draw Eyebrows ---
            ctx.strokeStyle = 'rgba(50, 30, 20, 0.9)';
            ctx.lineWidth = 4;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';

            const browY = dy + dh * 0.145; 
            const browW = dw * 0.12;

            ctx.beginPath();
            if (expression === 'sad') {
                ctx.moveTo(leftEyeX - browW/2, browY + 2);
                ctx.quadraticCurveTo(leftEyeX, browY - 4, leftEyeX + browW/2, browY - 6);
                
                ctx.moveTo(rightEyeX - browW/2, browY - 6);
                ctx.quadraticCurveTo(rightEyeX, browY - 4, rightEyeX + browW/2, browY + 2);
            } else if (expression === 'surprised') {
                ctx.moveTo(leftEyeX - browW/2, browY - 5);
                ctx.quadraticCurveTo(leftEyeX, browY - 12, leftEyeX + browW/2, browY - 5);

                ctx.moveTo(rightEyeX - browW/2, browY - 5);
                ctx.quadraticCurveTo(rightEyeX, browY - 12, rightEyeX + browW/2, browY - 5);
            } else if (expression === 'thinking') {
                ctx.moveTo(leftEyeX - browW/2, browY + 3);
                ctx.lineTo(leftEyeX + browW/2, browY + 1);

                ctx.moveTo(rightEyeX - browW/2, browY - 8);
                ctx.quadraticCurveTo(rightEyeX, browY - 12, rightEyeX + browW/2, browY - 5);
            }
            ctx.stroke();

            // --- 3. Draw Mouth ---
            if (mouthOpenness > 0) {
                const oh = dh * 0.035 * mouthOpenness;
                ctx.fillStyle = '#3a1a10';
                
                if (expression === 'surprised') {
                    ctx.beginPath();
                    ctx.ellipse(mouthX, mouthY + oh/2 + 2, mouthW/2.2, oh + 2, 0, 0, Math.PI * 2);
                    ctx.fill();
                } else if (expression === 'sad') {
                    ctx.beginPath();
                    ctx.ellipse(mouthX, mouthY + oh/2 + 3, mouthW/2, oh/1.5 + 1, 0, 0, Math.PI * 2);
                    ctx.fill();
                } else {
                    ctx.beginPath();
                    ctx.ellipse(mouthX, mouthY + oh/2 + 1, mouthW/2, oh/2 + 1, 0, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.fillStyle = 'rgba(215,115,100,0.6)';
                    ctx.beginPath();
                    ctx.ellipse(mouthX, mouthY + oh * 0.35 + 1, mouthW/2 * 0.8, oh * 0.35, 0, 0, Math.PI);
                    ctx.fill();
                }
            } else if (expression !== 'neutral') {
                ctx.strokeStyle = '#a65d4f';
                ctx.lineWidth = 2.5;
                ctx.beginPath();
                if (expression === 'sad') {
                    ctx.moveTo(mouthX - mouthW/2, mouthY + 7);
                    ctx.quadraticCurveTo(mouthX, mouthY + 2, mouthX + mouthW/2, mouthY + 7);
                } else if (expression === 'happy') {
                    ctx.moveTo(mouthX - mouthW/1.8, mouthY + 2);
                    ctx.quadraticCurveTo(mouthX, mouthY + 9, mouthX + mouthW/1.8, mouthY + 2);
                } else if (expression === 'thinking') {
                    ctx.moveTo(mouthX - mouthW/4, mouthY + 4);
                    ctx.lineTo(mouthX + mouthW/4, mouthY + 4);
                }
                ctx.stroke();
            }
            ctx.restore();
        };

        const drawGlow = (color: string, intensity: number) => {
            const g = ctx.createRadialGradient(CW / 2, CH * 0.4, 5, CW / 2, CH * 0.4, 110);
            g.addColorStop(0, `rgba(${color},${0.13 * intensity})`);
            g.addColorStop(0.6, `rgba(${color},${0.05 * intensity})`);
            g.addColorStop(1, 'rgba(0,0,0,0)');
            ctx.fillStyle = g;
            ctx.fillRect(0, 0, CW, CH);
        };

        const tickBlink = (dt: number, multiplier = 1) => {
            const d = animData.current;
            d.blinkTimer += dt;
            if (d.blinkPhase === 'none' && d.blinkTimer >= d.nextBlink * multiplier) {
                d.blinkPhase = 'closing'; d.blinkTimer = 0;
            }
            let amt = 0;
            const speed = stateRef.current === 'thinking' ? 80 : 60;
            if (d.blinkPhase === 'closing') {
                amt = Math.min(d.blinkTimer / speed, 1);
                if (d.blinkTimer >= speed) { d.blinkPhase = 'closed'; d.blinkTimer = 0; }
            } else if (d.blinkPhase === 'closed') {
                amt = 1;
                if (d.blinkTimer >= 80) { d.blinkPhase = 'opening'; d.blinkTimer = 0; }
            } else if (d.blinkPhase === 'opening') {
                amt = 1 - Math.min(d.blinkTimer / speed, 1);
                if (d.blinkTimer >= speed) {
                    d.blinkPhase = 'none'; d.blinkTimer = 0;
                    d.nextBlink = d.blinkInterval + Math.random() * 3000;
                }
            }
            return amt;
        };

        const render = (ts: number) => {
            if (!animData.current.lastTs) animData.current.lastTs = ts;
            const dt = Math.min(ts - animData.current.lastTs, 50);
            animData.current.lastTs = ts;

            const d = animData.current;
            
            // Influence animation speed by user mood
            const moodSpeedMult = userMood === 'excited' ? 2.0 : (userMood === 'upset' ? 0.5 : 1.0);
            d.breathPhase += dt * 0.001 * moodSpeedMult;
            d.swayPhase += dt * 0.0015 * moodSpeedMult;

            // Interpolate reaction tilt
            d.reactionTilt += (d.targetReactionTilt - d.reactionTilt) * 0.1;

            const currentState = stateRef.current;
            const currentExpr = expressionRef.current;

            // Voice sentiment influence (e.g., negative sentiment -> slower/subtler)
            const sentimentShift = Math.max(0, -voiceSentiment) * 5;

            // Modify animation based on state
            if (currentState === 'idle') {
                const sc = 1 + Math.sin(d.breathPhase) * 0.003;
                drawBase(0, sc, sentimentShift, currentExpr);
                drawProceduralFace(currentExpr, 0);
                drawBlink(tickBlink(dt));

            } else if (currentState === 'talking') {
                const bob = Math.sin(d.breathPhase * 4) * 0.8;
                drawBase(bob * 0.3, 1, bob + sentimentShift, currentExpr);
                drawProceduralFace(currentExpr, 0);
                drawBlink(tickBlink(dt, 0.7));

            } else if (currentState === 'listening') {
                // Glow color could shift based on sentiment
                const glowColor = voiceSentiment > 0.3 ? '100,255,150' : (voiceSentiment < -0.3 ? '150,100,255' : '80,220,200');
                const gi = Math.sin(d.swayPhase) * 0.4 + 1.0;
                ctx.clearRect(0, 0, CW, CH);
                drawGlow(glowColor, gi);
                drawBase(Math.sin(d.swayPhase * 0.8) * -3.5 - 2, 1, sentimentShift, currentExpr);
                drawProceduralFace(currentExpr, 0);
                drawBlink(tickBlink(dt));

            } else if (currentState === 'thinking') {
                drawBase(Math.sin(d.swayPhase * 0.7) * 4 + 5, 1, sentimentShift, 'thinking');
                drawProceduralFace('thinking', 0);
                drawBlink(tickBlink(dt, 1.5));
            }

            animationFrameRef.current = requestAnimationFrame(render);
        };

        animationFrameRef.current = requestAnimationFrame(render);

        return () => {
            if (animationFrameRef.current) {
                cancelAnimationFrame(animationFrameRef.current);
            }
        };
    }, [userMood, voiceSentiment]); // Re-run effect if mood/sentiment changes to update color/speed

    return (
        <canvas
            ref={canvasRef}
            width={300}
            height={400}
            style={{
                width: size,
                height: (size * 400) / 300,
                display: 'block',
                imageRendering: 'auto',
                filter: 'drop-shadow(0 0 10px rgba(0,0,0,0.1))'
            }}
        />
    );
};

export default KyraSpriteAvatar;
