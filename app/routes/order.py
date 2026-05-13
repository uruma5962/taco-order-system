"""注文画面（GET /）と注文送信（POST /order）。"""
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.auth import require_auth
from app.menu import calc_total

router = APIRouter()


@router.get("/", response_class=HTMLResponse, dependencies=[Depends(require_auth)])
async def order_page(request: Request):
    store = request.app.state.store
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "order.html",
        {"request": request, "stock": store.stock},
    )


@router.post("/order", dependencies=[Depends(require_auth)])
async def submit_order(
    request: Request,
    ビール: int = Form(0),
    コーラ: int = Form(0),
    タコス: int = Form(0),
    パクチー抜きタコス: int = Form(0),
    玉ねぎ抜きタコス: int = Form(0),
    イレギュラータコス: int = Form(0),
    irregular: str = Form(""),
):
    store = request.app.state.store
    templates = request.app.state.templates
    items = {
        "ビール": ビール,
        "コーラ": コーラ,
        "タコス": タコス,
        "パクチー抜きタコス": パクチー抜きタコス,
        "玉ねぎ抜きタコス": 玉ねぎ抜きタコス,
        "イレギュラータコス": イレギュラータコス,
    }
    total = calc_total(items)
    irregular = irregular.strip()

    if total == 0 and not irregular:
        return templates.TemplateResponse(
            "order.html",
            {"request": request, "stock": store.stock, "error": "⚠ 商品を1つ以上選択してください。"},
        )

    err = store.check_stock(items)
    if err:
        return templates.TemplateResponse(
            "order.html",
            {"request": request, "stock": store.stock, "error": err},
        )

    store.add(items=items, irregular=irregular, total=total)
    return RedirectResponse(url="/cashier", status_code=303)
