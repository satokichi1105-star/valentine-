# 🐶 French Bulldog — SVG flat vector

ドット絵版 (`assets/frenchie/`) と同じ 5 状態を、フラットベクターで描いた版。
すべて `tools/frenchie_svg.py` から生成しているので、SVG を直接編集せず
**スクリプトを直して再生成** してください。

```bash
python tools/frenchie_svg.py            # assets/frenchie-svg/ に出力
python tools/frenchie_svg.py -o path/   # 出力先を変える
```

Pillow などの依存はなし (標準ライブラリだけ)。

## 中身

| ファイル | 内容 |
| --- | --- |
| `frenchie-<state>.svg` | 状態ごとの単体ファイル。`<img src>` でそのまま動く |
| `frenchie.svg` | 全状態入り。ルートの class で切り替える (インライン用) |
| `preview.html` | 5 状態を並べた確認ページ + 切り替えデモ |
| `raster/<state>.gif` `.png` | SVG から書き出したラスタ版 (おまけ) |

`preview.html` は SVG をすべて直接インラインしてあるので、**このファイル 1 つ
だけをどこに置いてもそのまま動きます** (外部参照ゼロ)。

## SVG が開けない場所向け

チャットのプレビュー、資料への貼り付け、SVG のアニメーションを再生しない
ビューアなど向けに、GIF / PNG も書き出せます。

```bash
pip install playwright pillow
python tools/frenchie_svg_export.py            # assets/frenchie-svg/raster/ へ
python tools/frenchie_svg_export.py -s 480     # 大きめに書き出す
```

実際にブラウザで描画してコマを撮るので、本体と違って Playwright と Pillow が
要ります。各コマは Web Animations API でアニメーションを止めて `currentTime` を
進めながら撮っているため、ドットや Zzz のずらしもそのまま再現されます。
(`animation-delay` を上書きする方法だとずらしが消えてしまう。)

## 状態

| state | 内容 | 動き |
| --- | --- | --- |
| `idle` | 待機 | 尻尾振り + ゆっくり呼吸 + ときどきまばたき |
| `walk` | 歩行 | 上下に弾みながら前あしを交互に振る。耳も揺れる |
| `work` | 作業中 | 首をかしげ、右上に考え中のドットが浮かぶ |
| `done` | 完了 | しゃがむ → 跳ぶ → 着地。笑い目 + ベロ + キラキラ |
| `sleep` | スリープ | 伏せて呼吸。Zzz が浮かぶ |

`done` と `sleep` は口や姿勢そのものが変わるので、1 枚の SVG の中に
「立ちポーズ」と「伏せポーズ」、「まん丸の目」と「笑い目」を両方持たせて
CSS の `display` で出し分けています。

## 使い方

いちばん簡単なのは状態別ファイルをそのまま貼る方法:

```html
<img src="assets/frenchie-svg/frenchie-walk.svg" width="120" height="120" alt="">
```

状態を切り替えたいときは全状態入りをインラインして class を差し替える:

```html
<div id="pet"><!-- frenchie.svg の中身をそのまま貼る --></div>
<script>
  const svg = document.querySelector("#pet svg");
  const setState = s => svg.setAttribute("class", "frenchie frx-" + s);
  setState("work");
</script>
```

色は CSS 変数なので、埋め込み先から上書きできます:

```css
#pet svg { --frx-fur: #fff0f5; --frx-dark: #4a2f3a; }
```

| 変数 | 用途 |
| --- | --- |
| `--frx-ink` | 輪郭線・瞳・鼻 |
| `--frx-dark` | 黒い毛 (輪郭線と分けて潰れないようにしてある) |
| `--frx-dark2` | 耳の内側・目のふち・閉じ目 |
| `--frx-fur` | 白い毛 |
| `--frx-shade` | 白い毛の影・マズル |

`prefers-reduced-motion: reduce` のときはアニメーションを止めます。

## いじるときの注意

**インライン埋め込みで埋め込み先を壊さないための約束**

- クラス名と `@keyframes` 名はすべて `frx-` 始まり
- CSS セレクタは `.frenchie` 配下に閉じる
- `clipPath` の `id` はファイルごとにユニーク (`frx-idle-head` など)

新しいパーツや状態を足すときも、この 3 つは守ってください。

**`transform` 属性と CSS の `transform-origin` を同じ要素に付けない**

SVG の `transform` 属性は CSS の `transform` プロパティとして扱われるため、
`transform-box` / `transform-origin` を指定すると原点のぶんだけ二重に移動して
しまいます (これで最初、右耳が画面外に飛んでいました)。

配置用の `<g transform="...">` と、アニメーションさせる `<g class="frx-...">`
を必ず分けてください。耳・キラキラ・Zzz はこの形になっています。

右耳は `scale(-1,1)` の中にいるので、**回転角の符号が画面上では反転します**。
左右で同じ向きに倒したいとき (首かしげ) は符号を逆に、左右対称に開きたいとき
(歩行・ジャンプ) は同じ符号にします。
