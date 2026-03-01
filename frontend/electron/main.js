/**
 * KYRA – Electron Main Process
 *
 * Two windows:
 *   1. avatarWin  – tiny, frameless, transparent, always-on-top floating avatar
 *   2. chatWin    – full chat UI, opened on demand via right-click or tray
 *
 * Windows compatibility: no empty nativeImage tray (crashes on some builds).
 */

const { app, BrowserWindow, ipcMain, screen, Menu, Tray, nativeImage } = require('electron');
const path = require('path');
const fs = require('fs');

const isDev = process.env.NODE_ENV !== 'production';

let avatarWin = null;
let chatWin = null;
let tray = null;

// ─── Avatar Window ────────────────────────────────────────────────────────────

function createAvatarWindow() {
    if (avatarWin && !avatarWin.isDestroyed()) {
        avatarWin.show();
        return;
    }

    const { width: sw, height: sh } = screen.getPrimaryDisplay().workAreaSize;

    avatarWin = new BrowserWindow({
        width: 280,
        height: 320,
        x: sw - 300,
        y: sh - 340,
        frame: false,
        transparent: true,
        backgroundColor: '#00000000',
        hasShadow: false,
        alwaysOnTop: true,
        skipTaskbar: true,
        resizable: false,
        focusable: true,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
        },
    });

    if (isDev) {
        avatarWin.loadURL('http://localhost:5173/?mode=avatar');
    } else {
        avatarWin.loadFile(path.join(__dirname, '../dist/index.html'), {
            query: { mode: 'avatar' },
        });
    }

    avatarWin.on('closed', () => { avatarWin = null; });

    // Show when ready
    avatarWin.once('ready-to-show', () => {
        avatarWin.show();
    });
}

// ─── Chat Window ──────────────────────────────────────────────────────────────

function createChatWindow() {
    if (chatWin && !chatWin.isDestroyed()) {
        chatWin.focus();
        return;
    }

    chatWin = new BrowserWindow({
        width: 900,
        height: 700,
        minWidth: 700,
        minHeight: 550,
        frame: false,
        transparent: false,
        backgroundColor: '#0a0f1e',
        titleBarStyle: 'hidden',
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
        },
    });

    if (isDev) {
        chatWin.loadURL('http://localhost:5173/?mode=chat');
    } else {
        chatWin.loadFile(path.join(__dirname, '../dist/index.html'), {
            query: { mode: 'chat' },
        });
    }

    chatWin.once('ready-to-show', () => chatWin.show());
    chatWin.on('closed', () => { chatWin = null; });
}

// ─── Tray ─────────────────────────────────────────────────────────────────────

function createTray() {
    try {
        // Try to load an icon; fall back to 1×1 transparent PNG
        let icon;
        const iconPath = path.join(__dirname, '../public/kyra-icon.png');
        if (fs.existsSync(iconPath)) {
            icon = nativeImage.createFromPath(iconPath).resize({ width: 16, height: 16 });
        } else {
            // 1×1 transparent PNG as minimal fallback
            const transparentPng = Buffer.from(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
                'base64'
            );
            icon = nativeImage.createFromBuffer(transparentPng);
        }

        tray = new Tray(icon);
        tray.setToolTip('KYRA AI Assistant');

        const menu = Menu.buildFromTemplate([
            { label: '💬 Open Chat', click: createChatWindow },
            { label: '👁 Show Avatar', click: () => createAvatarWindow() },
            { type: 'separator' },
            { label: '✕ Quit KYRA', click: () => app.quit() },
        ]);
        tray.setContextMenu(menu);
        tray.on('double-click', createChatWindow);
        console.log('✅ Tray created');
    } catch (e) {
        console.warn('⚠️  Tray creation failed (non-fatal):', e.message);
    }
}

// ─── IPC Handlers ─────────────────────────────────────────────────────────────

function setupIPC() {
    // Chat window controls
    ipcMain.on('window:minimize', () => chatWin && !chatWin.isDestroyed() && chatWin.minimize());
    ipcMain.on('window:close', () => chatWin && !chatWin.isDestroyed() && chatWin.close());
    ipcMain.on('window:toggleMax', () => {
        if (!chatWin || chatWin.isDestroyed()) return;
        chatWin.isMaximized() ? chatWin.unmaximize() : chatWin.maximize();
    });

    // Open chat from avatar
    ipcMain.on('open:chat', createChatWindow);

    // Drag avatar window
    ipcMain.on('avatar:drag', (_, { dx, dy }) => {
        if (!avatarWin || avatarWin.isDestroyed()) return;
        const [x, y] = avatarWin.getPosition();
        avatarWin.setPosition(x + Math.round(dx), y + Math.round(dy));
    });

    // Toggle click-through on transparent parts
    ipcMain.on('avatar:setClickThrough', (_, value) => {
        if (avatarWin && !avatarWin.isDestroyed()) {
            avatarWin.setIgnoreMouseEvents(value, { forward: true });
        }
    });

    // Forward expression updates to both windows
    ipcMain.on('expression:update', (_, emotion) => {
        if (avatarWin && !avatarWin.isDestroyed())
            avatarWin.webContents.send('expression:update', emotion);
        if (chatWin && !chatWin.isDestroyed())
            chatWin.webContents.send('expression:update', emotion);
    });
}

// ─── App Lifecycle ────────────────────────────────────────────────────────────

app.whenReady().then(() => {
    setupIPC();
    createAvatarWindow();
    createTray();
});

app.on('window-all-closed', () => {
    // Keep alive via tray — only quit on macOS convention or explicit quit
    if (process.platform !== 'darwin' && !tray) app.quit();
});

app.on('activate', () => {
    if (!avatarWin) createAvatarWindow();
});
