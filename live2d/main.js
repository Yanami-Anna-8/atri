
  const { app, BrowserWindow, ipcMain } = require('electron')
  const path = require('path')
  
  function createWindow () {
    const win = new BrowserWindow({
      width: 800,         // 【修复】把窗口加大，防止模型显示不全
      height: 900,        
      transparent: true,  
      frame: false,       
      alwaysOnTop: true,  
      hasShadow: false,   
      webPreferences: {
        nodeIntegration: true,
        contextIsolation: false
      }
    })
  
    win.loadFile('index.html')
  
    // 【核心新增】：接收前端网页发来的“鼠标穿透”指令
    ipcMain.on('set-ignore-mouse-events', (event, ignore) => {
      const webContents = event.sender
      const currentWin = BrowserWindow.fromWebContents(webContents)
      // forward: true 保证即使窗口穿透了，依然能检测到鼠标移动
      currentWin.setIgnoreMouseEvents(ignore, { forward: true })
    })
  }
  
  app.whenReady().then(createWindow)
  
  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit()
  })