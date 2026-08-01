// レンダラに渡す最小限の窓口。contextIsolation を有効にしたままにしたいので、
// Node の機能はここで閉じて、必要なものだけ contextBridge で公開する。
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("pet", {
  getConfig: () => ipcRenderer.invoke("frenchie:config"),
  onState: (callback) =>
    ipcRenderer.on("frenchie:state", (_event, payload) => callback(payload)),
});
