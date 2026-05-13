import pytest

from app.store import OrderStore


@pytest.fixture
def store() -> OrderStore:
    return OrderStore()


def test_add_assigns_incrementing_ids(store):
    a = store.add(items={"タコス": 1}, irregular="", total=350)
    b = store.add(items={"ビール": 1}, irregular="", total=500)
    assert (a.id, b.id) == (1, 2)
    assert store.find(1) is a
    assert store.find(999) is None


def test_check_stock_returns_message_when_short(store):
    assert store.check_stock({"ビール": 10}) is None
    err = store.check_stock({"ビール": 1000})
    assert err is not None and "ビール" in err


def test_confirm_payment_decrements_stock_and_records_change(store):
    order = store.add(items={"タコス": 2, "ビール": 1}, irregular="", total=1200)
    before = store.stock
    confirmed = store.confirm_payment(order.id, received=1500)

    assert confirmed is not None
    assert confirmed.paid is True
    assert confirmed.change == 300
    assert confirmed.paid_at is not None
    assert store.stock["タコス"] == before["タコス"] - 2
    assert store.stock["ビール"] == before["ビール"] - 1


def test_confirm_payment_rejects_short_payment(store):
    order = store.add(items={"タコス": 1}, irregular="", total=350)
    assert store.confirm_payment(order.id, received=300) is None
    assert store.find(order.id).paid is False


def test_taco_variants_decrement_shared_taco_stock(store):
    order = store.add(
        items={"パクチー抜きタコス": 2, "玉ねぎ抜きタコス": 1},
        irregular="",
        total=1050,
    )
    before = store.stock["タコス"]
    store.confirm_payment(order.id, received=1050)
    assert store.stock["タコス"] == before - 3


def test_cancel_paid_returns_stock_and_removes_order(store):
    order = store.add(items={"タコス": 3, "コーラ": 2}, irregular="", total=1450)
    store.confirm_payment(order.id, received=1450)
    before = store.stock
    cancelled = store.cancel_paid(order.id)

    assert cancelled is not None
    assert store.find(order.id) is None
    assert store.stock["タコス"] == before["タコス"] + 3
    assert store.stock["コーラ"] == before["コーラ"] + 2


def test_cancel_before_payment_does_not_touch_stock(store):
    order = store.add(items={"タコス": 1}, irregular="", total=350)
    before = store.stock
    assert store.cancel(order.id) is not None
    assert store.find(order.id) is None
    assert store.stock == before


def test_clear_restores_stock_for_paid_orders_only(store):
    paid_order = store.add(items={"ビール": 5}, irregular="", total=2500)
    store.confirm_payment(paid_order.id, received=2500)
    unpaid_order = store.add(items={"タコス": 2}, irregular="", total=700)

    before = store.stock
    store.clear()

    assert store.all_orders() == []
    # 会計済みのビール分だけ戻る。未会計のタコスは減算前なので影響なし
    assert store.stock["ビール"] == before["ビール"] + 5
    assert store.stock["タコス"] == before["タコス"]


def test_stats_includes_total_sum_and_item_totals(store):
    o1 = store.add(items={"タコス": 2, "ビール": 1}, irregular="", total=1200)
    store.confirm_payment(o1.id, received=1200)
    o2 = store.add(items={"タコス": 1, "コーラ": 1}, irregular="", total=550)
    store.confirm_payment(o2.id, received=600)
    # 未会計は集計対象外
    store.add(items={"タコス": 99}, irregular="", total=99 * 350)

    stats = store.stats()
    assert stats["total_sum"] == 1200 + 550
    assert stats["item_totals"] == {"タコス": 3, "ビール": 1, "コーラ": 1}


def test_mark_delivered_sets_elapsed(store):
    order = store.add(items={"タコス": 1}, irregular="", total=350)
    store.confirm_payment(order.id, received=350)
    store.mark_delivered(order.id)

    found = store.find(order.id)
    assert found.delivered is True
    assert found.delivered_at is not None
    assert found.elapsed_seconds is not None
    assert found.elapsed_label is not None  # "00:00" 形式
