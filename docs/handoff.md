# 引き継ぎメモ — X週次サマリー機能（2026-08-09）

クラウドセッション（スマホ発）でやった作業を、ローカルのMacで続けるための
引き継ぎ。会話履歴は移せないので、決定事項と残タスクをここに残す。

## 何を作ろうとしているか

Claude Code関連のXアカウントを定期巡回して、有益なTips・新機能情報だけを
日本語で要約し、Slackの `#ai-運用改善` に投稿する仕組み。

きっかけはGrokの回答で、そこでは「X公式MCP + Claude CodeのRoutines」が
推奨されていた。方向性は正しかったが、**クラウドの実行環境では成立しない
部分があった**ので構成を変えている（下記「調査で分かったこと」）。

## 決まっていること

| 項目 | 決定 |
|---|---|
| 配信先 | Slack `#ai-運用改善` |
| 実行頻度 | 毎週土曜 5:00 JST |
| 対象アカウント | 18件。tier 1（Anthropic中の人）/ tier 2（コミュニティ）/ tier 3（日本語） |
| 取得元 | 当面はWebSearch。X MCPを繋いだら自動で高精度モードに切り替わる |

## 完了していること

- `.claude/skills/x-summary/accounts.md` — 監視アカウント一覧
- `.claude/skills/x-summary/SKILL.md` — 取得→絞り込み→要約→Slack投稿の手順
- `docs/x-summary-setup.md` — X MCP接続手順、取得元3案のコスト比較、Routine運用
- ブランチ `claude/x-auto-summary-implementation-k4to1w` にpush済み
- PR #2（ドラフト）: https://github.com/satokichi1105-star/valentine-/pull/2

`/x-summary` で手動実行できる状態。**まだ一度も本番実行していない**ので、
最初の1回は手動で回して出力を確認すること。

## 残タスク

### 1. リポジトリのprivate化（最優先・手作業）

**このリポジトリは現在publicで、2026-02-14の作成時からずっと公開されている。**
`index.html` に加えて `no_image.png.heic`（3.0MB）と `video.mp4.MOV`（8.3MB）が
含まれており、内容次第では個人的な写真・動画が公開されている。
`has_pages: true` なのでGitHub Pagesで配信されている可能性もある。

Claude Codeのセッションからは変更できない（プロキシが
`Repository settings writes are not permitted through this proxy.` で403を返す）。
GitHubのUIで手動で行う:

- Settings → Danger Zone → Change repository visibility → Make private
- Settings → Pages → Source を None に

### 2. Routineの登録

毎週土曜 5:00 JST（cron `4 20 * * 5` / UTC）に発火し、Slackに投稿するRoutine。
クラウドセッションで登録を試みたが `MCP tool call requires approval` で
2回とも弾かれ、**未登録**。

注意: Routineはクラウド側の機能なので、**ローカルのClaude Codeからは登録できない。**
claude.ai / スマホアプリのセッションで登録すること。登録時にSlackコネクタを
Grantする必要がある。

### 3. X MCPの接続（任意・精度向上）

繋がなくても動くが、繋ぐと直近7日の投稿を正確に取れる。
手順とコスト比較は `docs/x-summary-setup.md` を参照。

推奨は **twitterapi.io の MCP**（従量課金 $0.15/1,000ツイート、月額固定なし、
$1の無料クレジット、カード不要）。X公式MCP（`https://api.x.com/mcp`）は
機能はほぼ同等だが、X API Basic以上が必要で月$200前後 + 開発者審査1〜2週間。

繋いだ後は**Routineにもそのコネクタを追加でGrantする**こと。

## 調査で分かったこと（同じ検証を繰り返さないために）

- **X公式MCPは実在する。**`https://api.x.com/mcp`、2026-06-30ローンチ、
  200以上のAPIエンドポイント。Anthropicの公式コネクタディレクトリには
  未登録だが、claude.ai の「カスタムコネクタを追加」でURL指定すれば繋がる
- **コネクタ（リモートMCP）はAnthropicのクラウドから呼ばれる。**
  実行環境のネットワーク制限は無関係。逆にlocalhostのMCPサーバーは繋がらない
- **クラウド実行環境からは外部ホストがほぼ全部ブロックされる。**
  実測で `api.x.com` / `x.com` / `xcancel.com` / `rsshub.app` / `github.io`
  すべて403。だから「スクリプトでX APIを直接叩く」案はクラウドでは不可
- **WebSearchはX投稿の本文をインデックスしている。**
  `site:x.com trq212 Claude Code` で実投稿とパーマリンクが取れることを確認済み。
  ただし投稿日時が取れないことが多く、「直近7日の全投稿」は保証されない
- **GitHub APIはプロキシで経路制限されている。**リポジトリ設定の書き込みと
  Pages APIは不可。コード変更・PR作成は可能

## ローカルで動かすときの注意

ローカルのClaude Codeには、claude.ai側のコネクタ（Slack / Gmail / Notion など）
**が引き継がれない。**`/x-summary` をMacで実行するとSlack投稿の段階で失敗する
可能性がある。ローカルでSlackに投げたいなら `claude mcp add` でSlack MCPを
別途設定するか、出力をファイルに保存する運用に切り替えること。

要約の生成だけならローカルでもそのまま動く（WebSearchは使える）。
