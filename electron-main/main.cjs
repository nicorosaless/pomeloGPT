const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let pythonProcess = null;

function startPythonBackend() {
    const scriptPath = path.join(__dirname, '..', 'backend', 'main.py');
    // In a real app, you'd use a bundled python executable or venv
    // For dev, we assume 'python3' is available and has deps installed
    pythonProcess = spawn('python3', [scriptPath]);

    pythonProcess.stdout.on('data', (data) => {
        console.log(`Backend stdout: ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`Backend stderr: ${data}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`Backend exited with code ${code}`);
    });
}

function createWindow() {
    const win = new BrowserWindow({
        width: 1000,
        height: 800,
        webPreferences: {
            preload: path.join(__dirname, '..', 'preload', 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true,
        },
        titleBarStyle: 'hiddenInset', // Mac-style title bar
        vibrancy: 'under-window',     // Mac-style vibrancy
        visualEffectState: 'active',
    });

    if (process.env.NODE_ENV === 'development') {
        win.loadURL('http://localhost:5173');
        win.webContents.openDevTools();
    } else {
        win.loadFile(path.join(__dirname, '..', 'front', 'dist', 'index.html'));
    }
}

app.whenReady().then(() => {
    // In development, start.sh handles the backend. In production, we start it here.
    if (process.env.NODE_ENV !== 'development') {
        startPythonBackend();
    }
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});

app.on('will-quit', () => {
    if (pythonProcess) {
        pythonProcess.kill();
    }
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});

// Example IPC handler forwarding to FastAPI backend
// Example IPC handler forwarding to FastAPI backend
ipcMain.handle('api-call', async (event, endpoint, payload, method = 'POST') => {
    const maxRetries = 5;
    let attempt = 0;

    while (attempt < maxRetries) {
        try {
            const options = {
                method: method,
                headers: { 'Content-Type': 'application/json' },
            };

            if (method !== 'GET' && method !== 'HEAD' && payload) {
                options.body = JSON.stringify(payload);
            }

            // Forward request to local FastAPI server
            const response = await fetch(`http://127.0.0.1:8000/${endpoint}`, options);

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Backend error (${response.status}): ${errorText}`);
            }

            return await response.json();
        } catch (error) {
            // If connection refused, wait and retry
            if (error.cause && error.cause.code === 'ECONNREFUSED') {
                attempt++;
                console.log(`Connection refused, retrying (${attempt}/${maxRetries})...`);
                await new Promise(resolve => setTimeout(resolve, 1000));
                continue;
            }

            console.error('API call failed:', error);
            return { error: error.message };
        }
    }

    return { error: "Failed to connect to backend after multiple attempts" };
});
