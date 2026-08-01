# 🐶 French Bulldog desktop pet

画面のいちばん下に住んで、Claude Code の状態に合わせて動くデスクトップペット。
ドット絵 (`assets/frenchie/`) と、ステータスライン版と同じ状態ファイルを
そのまま使っています。

```bash
cd desktop-pet
npm install
npm start
```

Electron が必要です (`npm install` で入ります)。終了はメニューバー /
タスクトレイのアイコンから「終了」。

## 犬の状態

`~/.claude/frenchie.state` を監視しています。書いているのは Claude Code の
フック (`tools/frenchie-state.sh`)。設定は `assets/frenchie/README.md` の
「Claude Code のステータスラインに住まわせる」を見てください。フックを
入れていなくても、待機とときどきの散歩だけは動きます。

| Claude Code | 犬 |
| --- | --- |
| セッション開始 | 待機 (ときどき勝手に散歩する) |
| プロンプト送信 | 歩行 |
| ツール実行の直前 | 作業中 |
| 応答の終わり | 完了 (ジャンプ) |
| 6 秒後 / 5 分放置 | 待機 → スリープ |

状態ファイルはプロジェクトごとではなく `~/.claude/` の 1 つを見ます
(ペットは画面に 1 匹なので)。別の場所を見せたいときは
`FRENCHIE_STATE_FILE` で指定できます。

## 犬が見当たらないとき

透明ウィンドウなので「出ていない」のか「出ているけど中身が描けていない」のか
見た目では区別がつきません。まずデバッグモードで起動してください。

```bash
npm run debug
```

透明・クリック貫通・ドックアイコン隠しを全部外し、**濃い色の不透明な帯**を
画面下端に出して DevTools を開きます。切り分けはこうなります。

| デバッグモードで | 分かること | 次に見るところ |
| --- | --- | --- |
| 帯も出ない | ウィンドウ自体が出ていない | ターミナルのログ (下記) |
| 帯は出るが犬がいない | 描画側の問題 | DevTools の Console と Network |
| 帯も犬も出る | 透明・最前面まわりの問題 | `main.js` のウィンドウ設定 |

起動時にこういうログが出ます。ここまで出ていれば、少なくともウィンドウは
作られています。

```
[frenchie] 起動 (darwin, Electron 33.x)
[frenchie] 画面 bounds: { x: 0, y: 0, width: 1512, height: 982 }
[frenchie] ウィンドウ bounds: { x: 0, y: 862, width: 1512, height: 120 }
[frenchie] スプライト: /path/to/assets/frenchie/frenchie_sheet.png (あり)
[frenchie] ウィンドウを表示しました。実際の bounds: {...}
[frenchie] 見えている? true / 最前面? true
```

`★見つかりません★` と出ていたら、`desktop-pet/` の 1 つ上に
`assets/frenchie/frenchie_sheet.png` が無い状態です (リポジトリごと
持ってきていないと起きます)。

ドックアイコンを消す処理が疑わしいときは `FRENCHIE_KEEP_DOCK=1 npm start`
で、消さずに起動できます。

## 環境変数

| 変数 | 既定 | 意味 |
| --- | --- | --- |
| `FRENCHIE_STATE_FILE` | `~/.claude/frenchie.state` | 監視する状態ファイル |
| `FRENCHIE_SCALE` | `3` | 1 ドットを何 px で描くか (`4` でだいぶ大きい) |
| `FRENCHIE_SMOKE` | なし | 指定したパスに 1 枚撮って終了する (動作確認用) |
| `FRENCHIE_DEBUG` | なし | `npm run debug` と同じ (不透明 + DevTools) |
| `FRENCHIE_KEEP_DOCK` | なし | macOS でドックアイコンを消さない |

## つくり

- `main.js` — 画面下端に「透明・枠なし・常に最前面・クリック貫通」の横長
  ウィンドウを作る。ドックやタスクバーに重ねたいので、`workArea` ではなく
  `bounds` (画面全体) を基準に置いている
- `preload.js` — `contextIsolation` を有効にしたまま、設定と状態だけを
  レンダラに渡す最小限の窓口
- `index.html` — スプライトシートを CSS の `steps()` で切り替えて描く。
  歩くときは `requestAnimationFrame` で位置を動かし、端で折り返す

犬の `div` の id が `pet` ではなく `dog` なのは、`id="pet"` にすると
ブラウザの名前付きアクセスで `window.pet` がその要素を指してしまい、
Electron から渡される `window.pet` を上書きしてしまうためです。

## ブラウザだけで見る

`index.html` は `window.pet` が無いとき (= 普通のブラウザ) は自動で
確認モードになり、状態を切り替えるボタンが出ます。

```bash
python3 -m http.server 8000     # リポジトリのルートで
# http://localhost:8000/desktop-pet/index.html
```

## 確認済みのことと、していないこと

Linux + Xvfb 上で実際に Electron を起動し、透明ウィンドウに状態ファイルの
内容 (作業中) が反映されて描かれることまで確認しています。

一方、**macOS でドックより手前に出るか・クリックが下のアプリに抜けるか・
メニューバーのアイコンが出るかは未確認**です (この開発環境が Linux の
コンテナのため)。うまく出ない場合に触るのは `main.js` の以下あたり:

```js
win.setAlwaysOnTop(true, "screen-saver");
win.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
win.setIgnoreMouseEvents(true, { forward: true });
type: process.platform === "darwin" ? "panel" : undefined,
```
