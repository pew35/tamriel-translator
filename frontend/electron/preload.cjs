const { clipboard, contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("desktopWindow", {
  minimize: () => ipcRenderer.invoke("window:minimize"),
  close: () => ipcRenderer.invoke("window:close"),
  readClipboardImage: () => {
    const image = clipboard.readImage();

    return image.isEmpty() ? null : image.toDataURL();
  },
  setIgnoreMouseEvents: (ignore) =>
    ipcRenderer.invoke("window:set-ignore-mouse-events", ignore),
  setContentHeight: (height) =>
    ipcRenderer.invoke("window:set-content-height", height),
});
