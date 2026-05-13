"""注文を表す Order データクラス。

旧コードでは dict にフィールドを生やしていたが、IDE 補完と型チェックの
ために dataclass に移行。表示用の整形ロジックはここに property として集約。
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.menu import MENU_BY_NAME


@dataclass(slots=True)
class Order:
    id: int
    items: dict[str, int]
    irregular: str = ""
    total: int = 0
    paid: bool = False
    received: Optional[int] = None
    change: Optional[int] = None
    in_kitchen: bool = False
    delivered: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    paid_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None

    @property
    def timestamp_label(self) -> str:
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def paid_at_iso(self) -> str:
        return self.paid_at.isoformat() if self.paid_at else ""

    @property
    def elapsed_seconds(self) -> Optional[int]:
        if not self.paid_at or not self.delivered_at:
            return None
        return int((self.delivered_at - self.paid_at).total_seconds())

    @property
    def elapsed_label(self) -> Optional[str]:
        sec = self.elapsed_seconds
        return None if sec is None else f"{sec // 60:02d}:{sec % 60:02d}"

    def kitchen_dishes(self) -> list[tuple[str, int]]:
        return [
            (name, qty)
            for name, qty in self.items.items()
            if qty > 0 and name in MENU_BY_NAME and MENU_BY_NAME[name].is_dish
        ]

    def status_label(self) -> str:
        if self.delivered:
            return "提供済み"
        if self.in_kitchen:
            return "調理済み"
        return "提供中"
