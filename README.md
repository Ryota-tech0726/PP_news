# Power Platform ニュース ダイジェスト

Microsoft Power Platform の更新情報を自動収集・一覧表示する静的サイトです。

## データソース

| ソース | URL | 取得方法 |
|--------|-----|----------|
| Power Platform Blog | powerapps.microsoft.com/en-us/blog/feed/ | RSS |
| Developer Blog | devblogs.microsoft.com/powerplatform/feed/ | RSS |

## 構成

```
pp-news-digest/
├── .github/workflows/
│   └── update-news.yml    # 毎日 JST 0:00 に自動実行
├── docs/
│   ├── index.html         # フロントエンド (GitHub Pages で配信)
│   └── news.json          # ニュースデータ (自動更新)
├── fetch_news.py           # RSS取得・JSON生成スクリプト
└── README.md
```

## セットアップ手順

### 1. GitHubリポジトリを作成

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/<ユーザー名>/pp-news-digest.git
git push -u origin main
```

### 2. GitHub Pages を有効化

1. リポジトリの Settings → Pages
2. Source: **Deploy from a branch**
3. Branch: **main** / **docs** を選択
4. Save

数分後に `https://<ユーザー名>.github.io/pp-news-digest/` で公開されます。

### 3. GitHub Actions の確認

- `.github/workflows/update-news.yml` が毎日 UTC 15:00 (JST 0:00) に自動実行
- `Actions` タブで実行状況を確認可能
- 手動実行: Actions → Update Power Platform News → Run workflow

### 4. (任意) カスタムドメインの設定

1. ドメインを取得 (例: pp-news.example.com)
2. DNS に CNAME レコードを追加: `pp-news.example.com` → `<ユーザー名>.github.io`
3. GitHub Pages の Settings で Custom domain に入力

## ローカル開発

```bash
# RSS取得テスト
python fetch_news.py

# ローカルプレビュー
cd docs && python -m http.server 8000
# → http://localhost:8000 で確認
```

## 免責事項

本サイトは非公式の情報集約ページです。掲載内容の正確性は保証しません。
正確な情報は [Microsoft 公式サイト](https://learn.microsoft.com/en-us/power-platform/) でご確認ください。
