"""注文と在庫の状態を一元管理する OrderStore。

シングルプロセス前提のインメモリ実装。永続化したい場合は
このクラスのメソッドだけ差し替えれば呼び出し側は変えずに済む構造にしている。
"""
from datetime import datetime
from typing import Optional

from app.menu import initial_stock, required_stock
from app.models import Order


class OrderStore:
    def __init__(self) -> None:
        self._orders: list[Order] = []
        self._next_id: int = 1
        self._stock: dict[str, int] = initial_stock()

    @property
    def stock(self) -> dict[str, int]:
        return dict(self._stock)

    def all_orders(self) -> list[Order]:
        return sorted(self._orders, key=lambda o: o.id, reverse=True)

    def find(self, order_id: int) -> Optional[Order]:
        return next((o for o in self._orders if o.id == order_id), None)

    def add(self, *, items: dict[str, int], irregular: str, total: int) -> Order:
        order = Order(id=self._next_id, items=items, irregular=irregular, total=total)
        self._orders.append(order)
        self._next_id += 1
        return order

    def check_stock(self, items: dict[str, int]) -> Optional[str]:
        """在庫不足ならユーザー向けエラーメッセージを返す。問題なければ None。"""
        for key, qty in required_stock(items).items():
            available = self._stock.get(key, 0)
            if qty > available:
                return f"⚠ {key}の在庫が不足しています。（残り: {available}個）"
        return None

    def confirm_payment(self, order_id: int, received: int) -> Optional[Order]:
        order = self.find(order_id)
        if order is None or order.paid or received < order.total:
            return None
        for key, qty in required_stock(order.items).items():
            self._stock[key] -= qty
        order.paid = True
        order.received = received
        order.change = received - order.total
        order.paid_at = datetime.now()
        return order

    def mark_in_kitchen(self, order_id: int) -> Optional[Order]:
        order = self.find(order_id)
        if order is None:
            return None
        order.in_kitchen = True
        return order

    def mark_delivered(self, order_id: int) -> Optional[Order]:
        order = self.find(order_id)
        if order is None:
            return None
        order.delivered = True
        order.delivered_at = datetime.now()
        return order

    def unmark_delivered(self, order_id: int) -> Optional[Order]:
        order = self.find(order_id)
        if order is None:
            return None
        order.delivered = False
        order.delivered_at = None
        return order

    def cancel(self, order_id: int) -> Optional[Order]:
        order = self.find(order_id)
        if order is None or order.paid:
            return None
        self._orders = [o for o in self._orders if o.id != order_id]
        return order

    def cancel_paid(self, order_id: int) -> Optional[Order]:
        order = self.find(order_id)
        if order is None or not order.paid:
            return None
        for key, qty in required_stock(order.items).items():
            self._stock[key] += qty
        self._orders = [o for o in self._orders if o.id != order_id]
        return order

    def clear(self) -> None:
        for order in self._orders:
            if order.paid:
                for key, qty in required_stock(order.items).items():
                    self._stock[key] += qty
        self._orders = []
        self._next_id = 1

    def stats(self) -> dict:
        paid = [o for o in self._orders if o.paid]
        total_sum = sum(o.total for o in paid)

        item_totals: dict[str, int] = {}
        for o in paid:
            for name, qty in o.items.items():
                if qty > 0:
                    item_totals[name] = item_totals.get(name, 0) + qty

        elapsed_list = [o.elapsed_seconds for o in paid if o.elapsed_seconds is not None]
        if elapsed_list:
            avg = sum(elapsed_list) // len(elapsed_list)
            average_time: Optional[str] = f"{avg // 60:02d}:{avg % 60:02d}"
        else:
            average_time = None

        return {
            "total_sum": total_sum,
            "item_totals": item_totals,
            "average_time": average_time,
        }
