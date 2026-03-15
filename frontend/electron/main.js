/**
 * KYRA – Electron Main Process
 *
 * Two windows:
 *   1. avatarWin  – tiny, frameless, transparent, always-on-top floating avatar
 *   2. chatWin    – full chat UI, opened on demand via right-click or tray
 *
 * Windows compatibility: no empty nativeImage tray (crashes on some builds).
 */

// ─── Self-relaunch guard ───────────────────────────────────────────────────────────
// When ELECTRON_RUN_AS_NODE=1 is set (e.g. by some IDE / Python env),
// require('electron') returns a file path string instead of the module.
// Detect this and re-spawn via the actual electron binary with the var cleared.
if (process.env.ELECTRON_RUN_AS_NODE) {
    const { spawnSync } = require('child_process');
    const electronBin = require('electron'); // will be a path string here
    delete process.env.ELECTRON_RUN_AS_NODE;
    const result = spawnSync(
        electronBin,
        [__filename, ...process.argv.slice(2)],
        {
            stdio: 'inherit',
            env: { ...process.env },   // ELECTRON_RUN_AS_NODE already deleted
            detached: false,
        }
    );
    process.exit(result.status ?? 0);
}

const { app, BrowserWindow, ipcMain, screen, Menu, Tray, nativeImage } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

// ─── Global crash guards ──────────────────────────────────────────────────────
// Prevents EPIPE / broken-pipe from showing the JS error dialog when launched
// without an attached terminal (e.g. double-clicking run_kyra.bat).
process.on('uncaughtException', (err) => {
    if (err.code === 'EPIPE' || err.code === 'ECONNRESET') return; // swallow silently
    console.error('[KYRA] Uncaught exception:', err);
});
process.on('unhandledRejection', (reason) => {
    console.error('[KYRA] Unhandled rejection:', reason);
});

const isDev = process.env.NODE_ENV !== 'production';

let avatarWin = null;
let chatWin = null;
let tray = null;
let backendProc = null;

// ─── Backend Spawn ────────────────────────────────────────────────────────────

function startBackend() {
    let cmd, args, cwd;

    if (isDev) {
        // Dev: use venv python
        const root = path.join(__dirname, '..', '..', 'backend');
        const venvPy = path.join(root, '..', '.venv', 'Scripts', 'python.exe');
        const python = fs.existsSync(venvPy) ? venvPy : 'python';
        cmd = python;
        args = ['main.py'];
        cwd = root;
    } else {
        // Production: bundled backend exe next to this file
        const exePath = path.join(process.resourcesPath, 'backend', 'kyra_backend.exe');
        cmd = exePath;
        args = [];
        cwd = path.dirname(exePath);
    }

    console.log(`Spawning backend: ${cmd} ${args.join(' ')}`);
    backendProc = spawn(cmd, args, {
        cwd,
        env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
        // 'ignore' avoids EPIPE when no terminal is attached (e.g. launched via .bat)
        stdio: 'ignore',
        detached: false,
    });

    backendProc.on('exit', code => console.log(`Backend process exited with code: ${code}`));
}

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

// ─── Auto-start (Windows Registry via Electron) ────────────────────────────────

function getAutoStart() {
    return app.getLoginItemSettings().openAtLogin;
}

function setAutoStart(enable) {
    const exePath = process.execPath;
    app.setLoginItemSettings({
        openAtLogin: enable,
        // In dev, point to electron + main.js; in production, just the exe
        path: exePath,
        args: isDev ? [path.resolve(__dirname, '../electron/main.js')] : [],
        name: 'KYRA AI',
    });
    console.log(`Auto-start ${enable ? 'enabled' : 'disabled'}`);
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
        buildTrayMenu();
        tray.on('double-click', createChatWindow);
        console.log('✅ Tray created');
    } catch (e) {
        console.warn('⚠️  Tray creation failed (non-fatal):', e.message);
    }
}

function buildTrayMenu() {
    if (!tray) return;
    const isAutoStart = getAutoStart();
    const menu = Menu.buildFromTemplate([
        { label: '💬 Open Chat',    click: createChatWindow },
        { label: '👁 Show Avatar',  click: () => createAvatarWindow() },
        { type: 'separator' },
        {
            label: `${isAutoStart ? '✅' : '⬜'} Start with Windows`,
            click: () => {
                setAutoStart(!isAutoStart);
                buildTrayMenu(); // refresh menu to show new state
            },
        },
        { type: 'separator' },
        { label: '✕ Quit KYRA', click: () => app.quit() },
    ]);
    tray.setContextMenu(menu);
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
    startBackend();

    // Enable auto-start on first launch (only if not already set)
    if (!isDev && !getAutoStart()) {
        setAutoStart(true);
        console.log('Auto-start registered on first launch.');
    }

    // Open UI immediately — windows use ready-to-show so they
    // appear only once fully painted (no white flicker).
    setupIPC();
    createAvatarWindow();
    createTray();
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin' && !tray) app.quit();
});

app.on('before-quit', () => {
    if (backendProc) {
        backendProc.kill();
        backendProc = null;
    }
});

app.on('activate', () => {
    if (!avatarWin) createAvatarWindow();
});
