# 🐶 French Bulldog pixel sprites (32x32)

白黒フレンチブルドッグの 32x32 ドット絵スプライト。
実物の写真を参考に、**黒い耳／目の上まで覆う黒いマスク／額を通る白いブレーズ／
白いマズルと胸／背中の黒ブチ** というブチの入り方を再現している。

すべて `tools/frenchie_spritesheet.py` から生成しているので、
手描きの png を直接編集せず **スクリプトを直して再生成** してください。

```bash
pip install Pillow
python tools/frenchie_spritesheet.py           # assets/frenchie/ に出力
python tools/frenchie_spritesheet.py -s 12     # プレビュー倍率を変える
python tools/frenchie_spritesheet.py --no-gif  # GIF を作らない
```

## 中身

| ファイル | 内容 |
| --- | --- |
| `frenchie_sheet.png` | スプライトシート本体 (128x160 / 4列 x 5行) |
| `frenchie_sheet@8x.png` | 目視確認用の 8 倍拡大 |
| `frames/<state>_<n>.png` | フレーム単体 |
| `<state>.gif` | 状態ごとのアニメーション GIF (背景 `#1a1b3a` で塗りつぶし) |
| `frenchie.json` | 行番号・フレーム数・fps のメタデータ |
| `preview.html` | 5 状態を並べて動かす確認ページ |

## 状態 (シートの行順)

| 行 | state | 内容 | frames | fps |
| --- | --- | --- | --- | --- |
| 0 | `idle` | 待機。座って尻尾を振り、4 コマ目でまばたき | 4 | 4 |
| 1 | `walk` | 歩行。上下に弾みながら前あしを交互に上げる | 4 | 8 |
| 2 | `work` | 作業中。首をかしげ、右上のドットが増えていく | 4 | 5 |
| 3 | `done` | 完了。しゃがむ → 踏み切る → 頂点 → 着地 (ループなし) | 4 | 8 |
| 4 | `sleep` | スリープ。丸まって呼吸しつつ Zzz | 3 | 2 |

フレームは左詰め。`sleep` の 4 列目は空 (透明) なので、
描画時は `frenchie.json` の `frames` を見てコマ数を決めてください。

## 使い方

CSS だけで動かす場合 (`preview.html` と同じ方式):

```css
.frenchie {
  width: 64px; height: 64px;              /* 32 * 2 倍 */
  background: url("frenchie_sheet.png") 0 -64px / 256px 320px;  /* row 1 = walk */
  image-rendering: pixelated;
  animation: frenchie-walk .5s steps(4) infinite;
}
@keyframes frenchie-walk { to { background-position-x: -256px } }
```

Canvas に描く場合:

```js
const meta = await fetch("frenchie.json").then(r => r.json());
const sheet = new Image(); sheet.src = "frenchie_sheet.png";

function drawFrenchie(ctx, state, timeMs, x, y, scale = 2) {
  const s = meta.states[state];
  const i = Math.floor(timeMs / 1000 * s.fps);
  const frame = s.loop ? i % s.frames : Math.min(i, s.frames - 1);
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(
    sheet,
    frame * meta.frameWidth, s.row * meta.frameHeight, meta.frameWidth, meta.frameHeight,
    x, y, meta.frameWidth * scale, meta.frameHeight * scale,
  );
}
```

## 描き方のしくみ

`tools/frenchie_spritesheet.py` は 1 ドット = 1 文字のグリッド (`Canvas`) に
楕円を塗っていくだけの構成です。

1. パーツごとに空レイヤーを作ってシルエットを塗る
2. `shade_bottom()` で白い毛の下端 1px をグレーにする
3. `outline()` で外周に黒フチを自動生成する
4. しっぽ → 耳 → 胴体 → 前あし → 頭 の順に重ねる

重ねる順番がそのまま前後関係になるので、頭が胴体にかぶる部分にも
輪郭線がきちんと入ります。ポーズは `Pose` データクラスの数値
(頭・胴体の中心と半径、耳の角度、目のスタイル、前あし・しっぽの座標) を
フレームごとに差し替えて表現しています。

### 色の役割 (5 色)

| 記号 | 用途 |
| --- | --- |
| `K` | 輪郭線・瞳・鼻 |
| `D` | 黒い毛。輪郭線と同化しないよう 1 段明るくしてある |
| `M` | 黒い毛の影・耳の内側・黒地の上の下まぶた |
| `G` | 白い毛の影・マズルのシワ・黒地の上の閉じ目 |
| `W` | 白い毛・目のハイライト |

黒ベタを `K` にすると暗い背景で輪郭が消え、顔も真っ黒につぶれてしまうため、
毛の黒は `D`、線だけ `K` と分けています。目が黒いマスクに乗る状態では
`draw_eye()` が自動で下まぶた (`M`) や閉じ目の色 (`G`) を切り替えます。

### 32px の高さはほぼ埋まっている

耳の先から前あしまでで縦を使い切っているので、`done` (ジャンプ) は
体を持ち上げるのではなく **あしをたたんで足元に隙間を作る** ことで
浮いて見せています。ポーズをいじったときは生成時の
`! <state>_<n> が枠に接しています` という警告を見て、はみ出していないか
確認してください。
