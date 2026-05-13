# Taco Order System

イベントで実際に運用したタコス屋台の **注文・会計・厨房・売上管理** を一通り行う FastAPI Web アプリ。
ブラウザを開いた端末が POS / 会計 / 厨房ディスプレイ / 売上集計のすべてを兼ねる。

> 祭りで 1 日運用した個人プロジェクトを、ポートフォリオ向けに整理した版。
> 元コードは 460 行の単一ファイルだったものを、責務ごとに分割しテストを足し、
> Discord 依存を抽象化してトークン無しでデモ起動できるようにした。

> 🔄 **リニューアル版を制作中**：本リポジトリは祭りで実運用した FastAPI + Discord 版のコードです。
> 現在はこれをベースに、**アプリ化を見据えた SPA 版**（GUI 商品管理、トッピング差額対応、営業日締めなど）を別途制作中。
> SPA 版の進捗・スクリーンショットは個別にお見せできます。

---

## デモ起動（3 コマンド）

```bash
pip install -r requirements.txt
cp .env.example .env       # PowerShell: Copy-Item .env.example .env
uvicorn app.main:app --reload
```

ブラウザで <http://localhost:8000/> を開き、Basic 認証 `admin` / `admin` でログイン。

`.env` の `NOTIFIER_BACKEND=log`（デフォルト）の状態では Discord トークン無しで全画面が動作し、
会計確定時の通知はターミナルログに出力される。

```
2026-05-13 15:23:52 INFO app.notifier | 🍳 Kitchen [注文ID 1]
  - タコス x 2
  - パクチー抜きタコス x 1
  📝 イレギュラー: 辛さ控えめで
2026-05-13 15:23:52 INFO app.notifier | 🚚 Delivery [注文ID 1]
  - ビール x 2
  - コーラ x 1
  - タコス x 2
  - パクチー抜きタコス x 1
```

---

## 画面構成

| 画面 | パス | 役割 |
| --- | --- | --- |
| 注文 | `/` | 商品カードから数量を選んで注文。在庫数を常時表示。 |
| 会計 | `/cashier` | 未会計／会計済みリスト。受取額入力でお釣り自動計算。 |
| 厨房・提供 | `/kitchen` | 提供待ち／提供済みリスト。1 クリックで状態遷移。 |
| 履歴 | `/history` | 売上合計・商品別販売数・平均提供時間・残在庫を集計。 |

> スクリーンショットは `screenshots/` に配置予定（手動撮影）。

---

## 主な機能

- **注文 → 会計 → 厨房 → 提供 → 履歴** の業務フローを 1 つの Web アプリで完結
- **派生タコス**（パクチー抜き／玉ねぎ抜き／イレギュラー）を「タコス」在庫に集約しつつ、厨房表示では個別に出し分け
- **在庫リアルタイム表示**と注文時の在庫不足チェック
- **提供時間の自動計測**（会計確定 → 提供完了の経過時間）と全注文の平均提供時間集計
- **キャンセル** に対応（会計前削除／会計済み取消で在庫補充／提供済み巻き戻し）
- **Discord 連携**（オプション）：会計確定時に厨房・提供チャンネルへ自動投稿、ボタンで状態遷移
- **Basic 認証** で全画面を保護

---

## 技術スタック

| 種別 | 採用 |
| --- | --- |
| 言語 | Python 3.13 |
| Web | FastAPI 0.115 / Jinja2 / Uvicorn |
| 設定 | pydantic-settings（`.env` を型安全に読み込み） |
| UI | Bootstrap 5（CDN） |
| Bot | discord.py 2.4（オプション） |
| テスト | pytest（15 ケース） |
| Lint | ruff |

---

## アーキテクチャ

```
app/
├── main.py        FastAPI app + lifespan（OrderStore / Notifier を app.state に注入）
├── config.py      pydantic-settings で .env を読み込み
├── auth.py        Basic 認証（secrets.compare_digest でタイミング攻撃対策）
├── menu.py        MenuItem dataclass + MENU 定義（価格・在庫キー・厨房通知対象）
├── models.py      Order dataclass（経過時間・表示ラベルなどを property に集約）
├── store.py       OrderStore：注文と在庫の状態管理（in-memory）
├── notifier.py    Notifier Protocol + LogNotifier + DiscordNotifier
└── routes/        order / cashier / kitchen / history に分割した APIRouter
```

各ルーターは `request.app.state.{store,notifier,templates}` から依存を取得する。
状態は `OrderStore` に集約してあり、永続化（SQLite/Postgres）したい場合は
このクラスのメソッドを差し替えれば呼び出し側のコード変更は不要。

---

## 工夫した点

### 1. Notifier の Protocol 抽象化で「触れる」ポートフォリオに

実運用時は会計確定をトリガに Discord の厨房チャンネルへボタン付きメッセージを送り、
厨房スタッフがボタンを押すと FastAPI 側の状態が遷移する設計で組んでいた。
ただこの構造のままだと **採用担当が触る** には Bot トークンと 2 つのチャンネル ID が必須になる。

そこで通知層を `Notifier` Protocol で抽象化し、

- `LogNotifier` ：通知内容をターミナルログに出力（デフォルト）
- `DiscordNotifier` ：discord.py で本物のチャンネルへ送信（実運用版）

を環境変数 `NOTIFIER_BACKEND` で切り替えられるようにした。
これでトークン無しでも `pip install` → `uvicorn` だけでデモ起動でき、
かつ Discord 連携自体は設計として残せる。

`DiscordNotifier` は内部で `discord.py` を **遅延 import** しているので、
Log バックエンドしか使わない環境で discord.py が壊れていても影響しない。

### 2. 派生タコスをデータで宣言

「パクチー抜きタコス」「玉ねぎ抜きタコス」のようなバリエーションが、
元コードでは価格計算・在庫減算・厨房通知の各所で if/elif に分散していた。
これを `MenuItem` dataclass に集約：

```python
MENU = [
    MenuItem("タコス",           350, "タコス", is_dish=True),
    MenuItem("パクチー抜きタコス", 350, "タコス", is_dish=True),
    MenuItem("玉ねぎ抜きタコス",   350, "タコス", is_dish=True),
    ...
]
```

`stock_key` で在庫を共有し、`is_dish` で厨房通知の要否を切り替える。
新メニュー追加 = MENU に 1 行追加、で完結する。

### 3. 厨房と提供を別チャンネルに送る（実運用知見）

屋台で運用してみて気づいた：厨房（料理を作る側）と提供（料理を渡す側）は、
動線も忙しさも別物で、同じチャンネルに混ぜると見落とす。
そこで会計確定時に **厨房用** と **提供用** の 2 チャンネルへ別フォーマットで送る設計にした。

- 厨房用 ：料理だけ（タコス派生のみ、ドリンクは載せない）
- 提供用 ：全商品（ドリンク含む）

`is_dish=True` の MenuItem だけを厨房通知に載せることでこれを実現している。

### 4. 提供時間の計測

会計確定時刻と提供完了時刻を `Order.paid_at` / `Order.delivered_at` に記録し、
履歴画面で **個別の提供時間** と **平均提供時間** を集計する。
祭りでのオペレーション改善（何分かかっているかの可視化）に直結した機能。

---

## テスト

```bash
pip install -r requirements-dev.txt
pytest -v
```

```
tests/test_menu.py ......                                                [ 33%]
tests/test_store.py .........                                            [100%]
============================== 15 passed in 0.07s ==============================
```

ルーティング層は薄いコントローラーに留め、ロジックを `menu.py` / `store.py` に
寄せたことで、Web 層を立ち上げずに核となる動作（価格計算・在庫減算・キャンセル時の補充）
を検証できる構造にしている。

---

## 実運用で得た学び

- **複数画面を 1 人で操作する** ことが多かったので、各画面に 10 分ごとの自動リロードを入れて他端末の操作結果を取り込めるようにした
- 厨房側のスマホ画面が小さいので、Discord 投稿には **タコス合計個数** を冒頭にデカく出す（個別の派生は下に並べる）
- 入力ミス対策で会計画面に「ちょうど」ボタン（受取額に合計を自動入力）を追加した

---

## 今後の改善候補

- **永続化**：現在は in-memory のため再起動で揺り戻る。SQLite + SQLAlchemy で `OrderStore` を実装し直すのが最小コスト
- **リアルタイム更新**：自動リロード（ポーリング）を WebSocket に置き換え、操作即時反映
- **多ユーザー認証**：Basic 1 アカウントから OAuth/セッションベースに移行
- **モバイル UI**：注文画面は屋台のお客さんが直接スマホで打つことを想定し、レイアウトを縦長最適化

---

## ライセンス

MIT
