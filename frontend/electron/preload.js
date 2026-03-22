const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
    // Window controls (chat window)
    minimize: () => ipcRenderer.send('window:minimize'),
    close: () => ipcRenderer.send('window:close'),
    toggleMax: () => ipcRenderer.send('window:toggleMax'),

    // Layout mode detection (query param from URL)
    mode: new URLSearchParams(window.location.search).get('mode') ?? 'chat',

    // Open the full chat window from avatar overlay
    openChat: () => ipcRenderer.send('open:chat'),

    // Avatar dragging
    dragAvatar: (dx, dy) => ipcRenderer.send('avatar:drag', { dx, dy }),

    // Avatar menu
    showAvatarMenu: () => ipcRenderer.send('avatar:menu'),

    // Click-through for transparent areas
    setClickThrough: (value) => ipcRenderer.send('avatar:setClickThrough', value),

    // Expression detection updates
    onExpression: (callback) => {
        ipcRenderer.on('expression:update', (_, emotion) => callback(emotion));
    },
    removeExpressionListener: () => {
        ipcRenderer.removeAllListeners('expression:update');
    },
});
