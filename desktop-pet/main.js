// デスクトップペットの本体。
//
// 画面いちばん下に「透明・枠なし・常に最前面・クリック貫通」の横長ウィンドウを
// 作り、その中で犬を歩かせる。ドックやタスクバーに重なるように、workArea では
// なく bounds (画面全体) を基準に置いている。
//
// 犬の状態は ~/.claude/frenchie.state を監視して受け取る。書いているのは
// Claude Code のフック (tools/frenchie-state.sh)。

const { app, BrowserWindow, screen, ipcMain, Menu, Tray, nativeImage } = require("electron");
const fs = require("fs");
const os = require("os");
const path = require("path");

const REPO = path.join(__dirname, "..");
const SHEET = path.join(REPO, "assets/frenchie/frenchie_sheet.png");
const META = path.join(REPO, "assets/frenchie/frenchie.json");

const STATE_FILE =
  process.env.FRENCHIE_STATE_FILE || path.join(os.homedir(), ".claude/frenchie.state");

const SCALE = Number(process.env.FRENCHIE_SCALE || 3); // 1 ドットを何 px で描くか
const WINDOW_HEIGHT = 32 * SCALE + 24; // 犬の高さ + 影や跳ねる余白

// npm run debug で、透明・クリック貫通・ドック隠しを全部外して起動する。
// 「犬がいない」ときに、ウィンドウ自体が出ていないのか、出ているけど中身が
// 描けていないのかを切り分けるため。
const DEBUG =
  process.argv.includes("--frenchie-debug") || Boolean(process.env.FRENCHIE_DEBUG);

function log(...args) {
  console.log("[frenchie]", ...args);
}

let win = null;
let tray = null;

// --- 状態ファイルの監視 ---------------------------------------------------

const VALID = new Set(["idle", "walk", "work", "done", "sleep"]);

function readState() {
  try {
    const name = fs.readFileSync(STATE_FILE, "utf8").trim();
    if (!VALID.has(name)) return { state: "idle", age: 0 };
    const age = (Date.now() - fs.statSync(STATE_FILE).mtimeMs) / 1000;
    return { state: name, age };
  } catch {
    return { state: "idle", age: 0 };
  }
}

function sendState() {
  if (win && !win.isDestroyed()) win.webContents.send("frenchie:state", readState());
}

function watchState() {
  // fs.watch はファイルが作り直されると監視が外れるので、
  // 監視の張り直しつきで使う。合わせて 2 秒ごとのポーリングも回して、
  // 「放置して寝る」の判定 (経過時間) も更新する。
  let watcher = null;
  const attach = () => {
    try {
      watcher?.close();
      watcher = fs.watch(STATE_FILE, () => sendState());
    } catch {
      /* まだファイルが無いだけ。ポーリング側で拾う */
    }
  };
  attach();
  setInterval(() => {
    attach();
    sendState();
  }, 2000);
}

// --- ウィンドウ -----------------------------------------------------------

function createWindow() {
  const display = screen.getPrimaryDisplay();
  const { x, y, width, height } = display.bounds; // workArea ではなく bounds
  const bounds = { x, y: y + height - WINDOW_HEIGHT, width, height: WINDOW_HEIGHT };

  log("画面 bounds:", display.bounds);
  log("ウィンドウ bounds:", bounds);
  log("スプライト:", SHEET, fs.existsSync(SHEET) ? "(あり)" : "★見つかりません★");
  log("状態ファイル:", STATE_FILE, fs.existsSync(STATE_FILE) ? "(あり)" : "(まだ無い)");

  win = new BrowserWindow({
    ...bounds,
    // デバッグ時は「そもそもウィンドウが出ているか」を見たいので、
    // 透明・パネル・タスクバー隠しをまとめて外す
    transparent: !DEBUG,
    backgroundColor: DEBUG ? "#20222f" : undefined,
    frame: false,
    resizable: false,
    movable: false,
    skipTaskbar: !DEBUG,
    hasShadow: false,
    fullscreenable: false,
    show: false, // ready-to-show で明示的に出す
    type: !DEBUG && process.platform === "darwin" ? "panel" : undefined,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (!DEBUG) {
    // クリックを下のアプリに素通りさせる (ペットは触れないが邪魔にもならない)
    win.setIgnoreMouseEvents(true, { forward: true });
  }
  // ドックより手前・全ワークスペースに出す
  win.setAlwaysOnTop(true, "screen-saver");
  win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });

  // 何も見えないときに原因が分かるよう、失敗はすべて拾って出す
  win.webContents.on("preload-error", (_e, file, error) =>
    console.error("[frenchie] preload でエラー:", file, error)
  );
  win.webContents.on("did-fail-load", (_e, code, desc) =>
    console.error("[frenchie] 画面の読み込みに失敗:", code, desc)
  );
  win.webContents.on("render-process-gone", (_e, details) =>
    console.error("[frenchie] レンダラが落ちました:", details)
  );
  win.webContents.on("console-message", (_e, level, message) => {
    if (DEBUG || level >= 2) console.log("[frenchie:renderer]", message);
  });

  win.loadFile(path.join(__dirname, "index.html"));

  // ready-to-show が来ないまま黙って消えるのがいちばん困るので、
  // 3 秒経っても出ていなければ強制的に出して、その旨を残す
  setTimeout(() => {
    if (win && !win.isDestroyed() && !win.isVisible()) {
      console.error("[frenchie] ready-to-show が来ませんでした。強制的に表示します");
      win.show();
    }
  }, 3000);

  win.once("ready-to-show", async () => {
    win.show();
    log("ウィンドウを表示しました。実際の bounds:", win.getBounds());
    log("見えている?", win.isVisible(), "/ 最前面?", win.isAlwaysOnTop());
    if (DEBUG) win.webContents.openDevTools({ mode: "detach" });
    sendState();

    // 動作確認用: FRENCHIE_SMOKE にパスを渡すと、その場を 1 枚撮って終了する。
    // 実機に入れたあと「ちゃんと描けているか」を確かめるのに使う。
    if (process.env.FRENCHIE_SMOKE) {
      setTimeout(async () => {
        const shot = await win.webContents.capturePage();
        fs.writeFileSync(process.env.FRENCHIE_SMOKE, shot.toPNG());
        app.quit();
      }, 1200);
    }
  });
}

// 画面の解像度や配置が変わったら追従する
function followDisplay() {
  if (!win || win.isDestroyed()) return;
  const { x, y, width, height } = screen.getPrimaryDisplay().bounds;
  win.setBounds({ x, y: y + height - WINDOW_HEIGHT, width, height: WINDOW_HEIGHT });
}

function createTray() {
  // 1x1 の透明画像。メニューを出すためだけのトレイなので見た目は要らない
  tray = new Tray(nativeImage.createEmpty());
  tray.setToolTip("French Bulldog");
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: `監視中: ${STATE_FILE}`, enabled: false },
      { type: "separator" },
      { label: "終了", click: () => app.quit() },
    ])
  );
}

// --- 起動 -----------------------------------------------------------------

ipcMain.handle("frenchie:config", () => ({
  sheet: SHEET,
  meta: JSON.parse(fs.readFileSync(META, "utf8")),
  scale: SCALE,
  stateFile: STATE_FILE,
}));

app.whenReady().then(() => {
  log(`起動 (${process.platform}, Electron ${process.versions.electron})`);
  if (DEBUG) log("デバッグモード: 不透明ウィンドウ + DevTools + クリック貫通なし");
  createWindow();
  // ドックアイコンを消すのはウィンドウを出したあと。先に呼ぶと macOS で
  // ウィンドウが出てこないことがある。デバッグ時は消さない (存在確認のため)。
  if (!DEBUG && !process.env.FRENCHIE_KEEP_DOCK) {
    setTimeout(() => app.dock?.hide(), 1000);
  }
  watchState();
  try {
    createTray();
  } catch {
    /* トレイが使えない環境でも本体は動かす */
  }
  screen.on("display-metrics-changed", followDisplay);
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => app.quit());
