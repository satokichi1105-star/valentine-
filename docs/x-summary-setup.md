# X週次サマリー — セットアップと運用

Claude Code関連のXアカウントを毎週巡回して、有益なTips・新機能情報だけを
日本語で要約し、Slackの `#ai-運用改善` に投稿する仕組み。

## 構成

| 部品 | 実体 | 役割 |
|---|---|---|
| 対象アカウント | `.claude/skills/x-summary/accounts.md` | 誰を監視するか。ここを書き換えれば対象が変わる |
| 生成ロジック | `.claude/skills/x-summary/SKILL.md` | 取得・絞り込み・要約・Slack投稿の手順 |
| スケジューラ | Claude の Routine（後述） | 毎週土曜 5:00 JST に発火 |
| 配信先 | Slack `#ai-運用改善` | |

手動で回したいときは Claude Code で `/x-summary` と打つ。

## 投稿データの取得元 — 3つの選択肢

現状は **C（WebSearchフォールバック）** で動く。A か B を繋ぐと精度が上がり、
スキルが自動で切り替わる（`SKILL.md` がMCPの有無を検出する）。

| | 取得元 | 精度 | コスト | 手間 |
|---|---|---|---|---|
| **A** | X公式ホストMCP `https://api.x.com/mcp` | ◎ 直近の投稿を正確に全件 | **月$200前後**（X API Basic以上） | 開発者アカウント審査に1〜2週間 |
| **B** | twitterapi.io の MCP `mcp.twitterapi.io` | ◎ ほぼ同等 | **従量課金 $0.15 / 1,000ツイート**、月額固定なし。$1の無料クレジット付き（カード不要） | 15分 |
| **C** | Claude の WebSearch（現状） | △ 話題性のある投稿のみ。投稿日時が取れないことがある | 無料 | ゼロ（設定済み） |

**おすすめは B。**10数アカウント × 週1回なら月数十円〜数百円で収まる。
A は同じことをするのに月$200かかるので、業務でX APIを他にも使う予定が
ないなら選ぶ理由が薄い。

### 重要な前提

コネクタ（リモートMCP）は**あなたのPCではなくAnthropicのクラウドから
呼ばれる**。だから Claude Code on the web の実行環境が持つネットワーク制限は
一切関係しない。逆に、localhost やVPN内で動くMCPサーバーは繋がらない
（公開HTTPSのURLが必要）。

## B の繋ぎ方（推奨ルート）

1. https://twitterapi.io/ でアカウントを作る。$1の無料クレジットが付く（カード登録不要）
2. ダッシュボードでAPIキーを発行する
3. claude.ai を開く → **Settings → Connectors → カスタムコネクタを追加**
4. MCPサーバーのURLに twitterapi.io が案内しているMCPエンドポイントを入れる
5. 認証情報（APIキー、または案内されたOAuth設定）を入れて追加する
6. **会話ごとにコネクタを有効化する必要がある。**チャット左下の「+」→
   Connectors から今回のコネクタをONにする
7. Claude Code で `/x-summary` を手動実行して、モードAで動くか確認する

Team / Enterprise プランの場合は、まずOwnerが
**Organization Settings → Connectors → Add → Custom → Web** で追加してから、
各メンバーが個別に接続する。

## A の繋ぎ方（X公式MCP）

1. https://developer.x.com/ でX開発者アカウントを申請する（審査1〜2週間）
2. Basic以上のプランに加入する（月$200前後）
3. アプリを作成し、OAuth 2.0 のクライアントID / シークレットを取得する
4. claude.ai → **Settings → Connectors → カスタムコネクタを追加**
5. URLに `https://api.x.com/mcp` を入れる
6. 「Advanced settings」を開き、OAuth Client ID / Client Secret を入れる
7. 追加後、会話ごとにコネクタをONにする

なお `https://docs.x.com/mcp` という別サーバーもあり、こちらはX APIの
ドキュメント検索用。投稿の取得はできないので今回の用途では不要。

## Routine（自動実行）の管理

毎週土曜 5:00 JST に発火するRoutineが登録されている。

- **一覧を見る / 止める / 時刻を変える:** Claude に「Routineの一覧を出して」
  「土曜のXサマリーを毎日に変えて」等と頼めば操作できる
- **手動で今すぐ回す:** Claude に「Xサマリーを今すぐ回して」と頼むか、
  Claude Code で `/x-summary`
- Routineは毎回**新しいセッション**を立ち上げる。前回の会話の文脈は
  引き継がれないので、プロンプトは単体で完結するように書いてある

Routineが使うコネクタは登録時に指定してある（Slack）。B や A のX MCPを
追加したら、**RoutineにもそのコネクタをGrantし直す必要がある**ので、
繋いだら Claude に「XのMCPもRoutineで使えるようにして」と伝えること。

## 対象アカウントを変えたいとき

`.claude/skills/x-summary/accounts.md` を編集してコミットするだけ。
tier 1 は必ず全件巡回されるので、絶対に見逃したくないアカウントは
tier 1 に置く。

## 既知の限界

- WebSearchモード（C）では「直近7日の全投稿」は取得できない。
  検索インデックスに載った投稿だけが対象になる
- 鍵アカウントや公開制限のある投稿は、どのモードでも取得できない
- Routineは実行時にSlackコネクタが利用可能である必要がある。
  Slackの認証が切れると投稿に失敗する
