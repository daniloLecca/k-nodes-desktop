import { app, BrowserWindow } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let mainWindow;
let pythonProcess;

function startBackend() {
  const isDev = !app.isPackaged;
  const port = 8123;
  
  if (isDev) {
    console.log("Modalità Sviluppo: Il backend python deve essere avviato manualmente su porta 8123");
  } else {
    const executableName = process.platform === 'win32' ? 'backend-api.exe' : 'backend-api';
    const backendPath = path.join(process.resourcesPath, 'backend-dist', executableName);
    
    pythonProcess = spawn(backendPath, ["--port", port.toString()], { detached: false });

    pythonProcess.stdout.on('data', (data) => console.log(`Backend: ${data}`));
    pythonProcess.stderr.on('data', (data) => console.error(`Backend Err: ${data}`));
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    icon: path.join(__dirname, 'public', 'vipnodes-logo.png'),
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

let isBackendReady = false; 

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
      .catch(err => {
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
    pythonProcess.kill();
  }
});