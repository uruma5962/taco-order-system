"""メニュー定義。価格・在庫キー・厨房通知対象を MenuItem としてデータで宣言する。

タコス派生（パクチー抜き等）も同じ MenuItem として並べることで、
価格計算と在庫管理を全派生で共通化している。新メニュー追加は MENU に1行足すだけ。
"""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MenuItem:
    name: str
    price: int
    stock_key: str
    is_dish: bool


MENU: list[MenuItem] = [
    MenuItem("タコス", 350, "タコス", is_dish=True),
    MenuItem("パクチー抜きタコス", 350, "タコス", is_dish=True),
    MenuItem("玉ねぎ抜きタコス", 350, "タコス", is_dish=True),
    MenuItem("イレギュラータコス", 350, "タコス", is_dish=True),
    MenuItem("ビール", 500, "ビール", is_dish=False),
    MenuItem("コーラ", 200, "コーラ", is_dish=False),
]

MENU_BY_NAME: dict[str, MenuItem] = {item.name: item for item in MENU}


def initial_stock() -> dict[str, int]:
    return {"ビール": 72, "コーラ": 60, "タコス": 500}


def calc_total(quantities: dict[str, int]) -> int:
    return sum(
        MENU_BY_NAME[name].price * qty
        for name, qty in quantities.items()
        if name in MENU_BY_NAME and qty > 0
    )


def required_stock(quantities: dict[str, int]) -> dict[str, int]:
    needed: dict[str, int] = {}
    for name, qty in quantities.items():
        if qty <= 0 or name not in MENU_BY_NAME:
            continue
        key = MENU_BY_NAME[name].stock_key
        needed[key] = needed.get(key, 0) + qty
    return needed
