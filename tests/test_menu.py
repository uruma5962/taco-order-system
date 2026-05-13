from app.menu import MENU_BY_NAME, calc_total, required_stock


TACO_VARIANTS = ["タコス", "パクチー抜きタコス", "玉ねぎ抜きタコス", "イレギュラータコス"]


def test_all_taco_variants_share_price_and_stock_key():
    for name in TACO_VARIANTS:
        item = MENU_BY_NAME[name]
        assert item.price == 350
        assert item.stock_key == "タコス"
        assert item.is_dish is True


def test_drinks_have_distinct_stock_keys_and_are_not_dishes():
    assert MENU_BY_NAME["ビール"].stock_key == "ビール"
    assert MENU_BY_NAME["ビール"].is_dish is False
    assert MENU_BY_NAME["コーラ"].stock_key == "コーラ"
    assert MENU_BY_NAME["コーラ"].price == 200


def test_calc_total_for_mixed_order():
    items = {"タコス": 2, "パクチー抜きタコス": 1, "ビール": 1, "コーラ": 2}
    # 2*350 + 1*350 + 1*500 + 2*200 = 1950
    assert calc_total(items) == 1950


def test_calc_total_ignores_unknown_items_and_zero_quantities():
    assert calc_total({"タコス": 1, "謎の商品": 5, "ビール": 0}) == 350


def test_required_stock_aggregates_all_taco_variants_under_taco_key():
    items = {
        "タコス": 1,
        "パクチー抜きタコス": 2,
        "玉ねぎ抜きタコス": 1,
        "ビール": 3,
        "コーラ": 0,
    }
    assert required_stock(items) == {"タコス": 4, "ビール": 3}
