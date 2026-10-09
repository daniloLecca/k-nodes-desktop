import { app, BrowserWindow, dialog } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn, exec } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let mainWindow;
let pythonProcess;
let isBackendReady = false;

function startBackend() {
  const isDev = !app.isPackaged;
  const port = 8123;
  
  if (isDev) {
    console.log("Dev mode: server must be started manually on port 8123.");
  } else {
    const executableName = process.platform === 'win32' ? 'backend-api.exe' : 'backend-api';
    const backendPath = path.join(process.resourcesPath, 'backend-dist', executableName);
    
    pythonProcess = spawn(backendPath, ["--port", port.toString()], { detached: false });

    pythonProcess.stdout.on('data', (data) => console.log(`Backend: ${data}`));
    pythonProcess.stderr.on('data', (data) => console.error(`Backend Err: ${data}`));

    // catch if the backend cannot start
    pythonProcess.on('error', (err) => {
      dialog.showErrorBox("Error starting backend", `Cannot run the Python process:\n${err.message}`);
    });

    pythonProcess.on('exit', (code, signal) => {
      if (code !== 0 && code !== null) {
        dialog.showErrorBox("Backend crash", `Python backend has unexpectedly shutted down with code: ${code}`);
      }
    });
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    icon: path.join(__dirname, 'public', process.platform === 'win32' ? 'knodes-logo.ico' : 'knodes-logo.png'),
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  const isDev = !app.isPackaged;
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }
}

function waitForBackend(callback) {
  console.log("In attesa che il server Python sia pronto...");
  
  const checkServer = () => {
    fetch('http://127.0.0.1:8123/api/')
      .then(res => {
        if (res.ok) {
          console.log("Backend pronto! Avvio l'interfaccia Vue.");
          isBackendReady = true; 
          callback(); 
        } else {
          setTimeout(checkServer, 500);
        }
      })
      .catch(() => {
        setTimeout(checkServer, 500);
      });
  };

  checkServer();
}

app.whenReady().then(() => {
  startBackend();
  waitForBackend(createWindow); 

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0 && isBackendReady) {
      createWindow();
    }
  });
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});

app.on('will-quit', () => {
  if (pythonProcess) {
    if (process.platform === 'win32') {
      exec(`taskkill /pid ${pythonProcess.pid} /T /F`);
    } else {
      pythonProcess.kill();
    }
  }
});