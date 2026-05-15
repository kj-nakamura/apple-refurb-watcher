# Apple Refurb Watcher

Apple 整備済み品に **Mac mini** が入荷したら Slack に通知するツールです。  
GitHub Actions で 30 分ごとに自動チェックします（無料枠で動作）。

## 通知イメージ

```
🎉 Mac mini が整備済み品に入荷しました！

• Mac mini [整備済製品] Apple M4チップ - ¥94,800
  https://www.apple.com/jp/shop/product/...
```

## セットアップ

### 1. リポジトリをフォーク

右上の **Fork** ボタンからフォークしてください。

### 2. Slack Incoming Webhook を作成

1. [api.slack.com/apps](https://api.slack.com/apps) にアクセス
2. **Create New App** → **From scratch** を選択
3. App Name（例: `Apple Refurb Watcher`）とワークスペースを入力して **Create App**
4. 左メニューの **Incoming Webhooks** を開き、トグルを **On** にする
5. **Add New Webhook to Workspace** をクリック
6. 通知先チャンネルを選択して **許可する**
7. 生成された Webhook URL をコピー（`https://hooks.slack.com/services/...`）

### 3. GitHub Secrets に Webhook URL を登録

フォークしたリポジトリの **Settings → Secrets and variables → Actions** を開き、  
**New repository secret** で以下を追加します。

| Name | Value |
|------|-------|
| `SLACK_WEBHOOK_URL` | 手順 2 でコピーした Webhook URL |

### 4. 動作確認

**Actions タブ → Check Apple Refurbished Mac mini → Run workflow** で手動実行できます。

## カスタマイズ

### 監視する製品を変える

リポジトリの **Settings → Variables → Actions** で `WATCH_KEYWORDS` を追加するだけです（コード変更不要）。

| 設定しない場合 | `Mac mini` のみ監視 |
|---|---|
| `Mac mini,iPhone` | Mac mini と iPhone を両方監視 |
| `MacBook Pro` | MacBook Pro のみ監視 |

対応しているキーワード：`Mac mini` / `MacBook` / `iMac` / `Mac Pro` / `Mac Studio` / `iPhone` / `iPad` / `Apple Watch` / `AirPods` / `Apple TV`

> [!TIP]
> Secrets（`SLACK_WEBHOOK_URL`）と同じ場所に Variables として追加します。  
> Settings → Secrets and variables → Actions → **Variables タブ** → New repository variable

### チェック頻度を変える

[.github/workflows/check.yml](.github/workflows/check.yml) の `cron` を変更してください。

```yaml
- cron: '*/30 * * * *'  # 30分ごと
- cron: '0 * * * *'     # 1時間ごと
```

> [!NOTE]
> GitHub Actions のスケジュール実行は高負荷時に遅延する場合があります。

## 仕組み

1. `https://www.apple.com/jp/shop/refurbished/mac` をフェッチ
2. ページ内の JSON-LD から商品名・SKU・価格・URL を抽出
3. `notified.json`（リポジトリ内）と照合し、新着 SKU のみ Slack 通知
4. 在庫が消えた SKU は `notified.json` から削除（再入荷を再通知するため）
