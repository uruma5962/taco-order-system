# Screenshots

README から参照するスクリーンショットを以下のファイル名で配置する。

- `order.png` 注文画面
- `cashier.png` 会計画面
- `kitchen.png` 厨房・提供画面
- `history.png` 履歴・売上集計画面

撮影手順：

```bash
uvicorn app.main:app --reload
```

`http://localhost:8000/` を `admin` / `admin` で開き、上記 4 画面をスクリーンショット撮影。
