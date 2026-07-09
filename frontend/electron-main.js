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
    // Punta alla cartella creata da PyInstaller
    const executableName = process.platform === 'win32' ? 'backend-api.exe' : 'backend-api';
    const backendPath = path.join(process.resourcesPath, 'backend-dist', executableName);
    
    // Avvia l'eseguibile passando la porta come argomento
    pythonProcess = spawn(backendPath, ["--port", port.toString()], { detached: false });

    pythonProcess.stdout.on('data', (data) => console.log(`Backend: ${data}`));
    pythonProcess.stderr.on('data', (data) => console.error(`Backend Err: ${data}`));
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
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

app.whenReady().then(() => {
  startBackend();
  // Aspetta 2 secondi che il server Uvicorn (Python) sia pronto
  setTimeout(createWindow, 2000); 

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
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