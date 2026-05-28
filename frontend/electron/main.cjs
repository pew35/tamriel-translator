const { app, BrowserWindow, ipcMain } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");

const FRONTEND_URL = "http://127.0.0.1:5173";
const BACKEND_URL = "http://127.0.0.1:8001";
const PROJECT_ROOT = path.resolve(__dirname, "..", "..");
const FRONTEND_DIR = path.join(PROJECT_ROOT, "frontend");
const BACKEND_DIR = path.join(PROJECT_ROOT, "backend");
const LOG_FILE = path.join(FRONTEND_DIR, "electron.log");
const DIST_INDEX = path.join(__dirname, "..", "dist", "index.html");

let mainWindow;
let frontendProcess;
let backendProcess;

function spawnHidden(command, args, cwd) {
  const processHandle = spawn(command, args, {
    cwd,
    shell: process.platform === "win32",
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });

  processHandle.stdout?.on("data", (data) => {
    fs.appendFileSync(LOG_FILE, data);
  });

  processHandle.stderr?.on("data", (data) => {
    fs.appendFileSync(LOG_FILE, data);
  });

  processHandle.on("error", (error) => {
    fs.appendFileSync(LOG_FILE, `${command} failed: ${error.message}\n`);
  });

  return processHandle;
}

function waitForUrl(url, timeoutMs = 30000) {
  const startedAt = Date.now();

  return new Promise((resolve, reject) => {
    const check = () => {
      const request = http.get(url, (response) => {
        response.resume();
        resolve();
      });

      request.on("error", () => {
        if (Date.now() - startedAt > timeoutMs) {
          reject(new Error(`Timed out waiting for ${url}`));
          return;
        }

        setTimeout(check, 500);
      });

      request.setTimeout(2000, () => {
        request.destroy();
      });
    };

    check();
  });
}

function startServices() {
  fs.writeFileSync(LOG_FILE, `Starting Tamriel Translator desktop app\n`);

  backendProcess = spawnHidden(
    "py",
    ["-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8001"],
    BACKEND_DIR,
  );

  frontendProcess = spawnHidden(
    process.platform === "win32" ? "npm.cmd" : "npm",
    ["run", "dev", "--", "--host", "127.0.0.1"],
    FRONTEND_DIR,
  );
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 320,
    height: 120,
    minWidth: 300,
    minHeight: 120,
    frame: false,
    transparent: true,
    resizable: true,
    minimizable: true,
    alwaysOnTop: true,
    skipTaskbar: false,
    backgroundColor: "#00000000",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.setBackgroundColor("#00000000");
  mainWindow.setAlwaysOnTop(true, "screen-saver");
  mainWindow.setIgnoreMouseEvents(false);

  if (app.isPackaged) {
    await mainWindow.loadFile(DIST_INDEX);
    return;
  }

  await waitForUrl(BACKEND_URL);
  await waitForUrl(FRONTEND_URL);
  await mainWindow.loadURL(FRONTEND_URL);
}

function stopServices() {
  for (const processHandle of [frontendProcess, backendProcess]) {
    if (processHandle && !processHandle.killed) {
      processHandle.kill();
    }
  }
}

ipcMain.handle("window:minimize", () => {
  mainWindow?.minimize();
});

ipcMain.handle("window:close", () => {
  mainWindow?.close();
});

ipcMain.handle("window:set-ignore-mouse-events", (_event, ignore) => {
  mainWindow?.setIgnoreMouseEvents(Boolean(ignore), { forward: true });
});

ipcMain.handle("window:set-content-height", (_event, height) => {
  if (!mainWindow) {
    return;
  }

  const bounds = mainWindow.getBounds();
  const nextHeight = Math.max(120, Math.min(Math.ceil(Number(height) || 120), 640));
  mainWindow.setBounds({ ...bounds, height: nextHeight });
});

app.whenReady().then(async () => {
  if (!app.isPackaged) {
    startServices();
  }

  await createWindow();
});

app.on("window-all-closed", () => {
  stopServices();
  app.quit();
});

app.on("before-quit", () => {
  stopServices();
});
