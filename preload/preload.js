const { contextBridge, ipcRenderer } = require('electron');

// Expose a safe API to the renderer process
contextBridge.exposeInMainWorld('api', {
    invoke: (channel, ...args) => {
        // whitelist channels
        const validChannels = ['api-call'];
        if (validChannels.includes(channel)) {
            return ipcRenderer.invoke(channel, ...args);
        }
        console.warn(`Invalid channel: ${channel}`);
    },
    // You can add more methods here as needed
});
