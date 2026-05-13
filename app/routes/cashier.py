"""会計画面・会計確定・キャンセル各種。"""
from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.auth import require_auth

router = APIRouter()


@router.get("/cashier", dependencies=[Depends(require_auth)])
async def cashier(request: Request):
    store = request.app.state.store
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "cashier.html",
        {"request": request, "orders": store.all_orders(), "error": None},
    )


@router.post("/cashier/confirm/{order_id}", dependencies=[Depends(require_auth)])
async def confirm_payment(
    order_id: int,
    request: Request,
    background: BackgroundTasks,
    received: int = Form(...),
):
    store = request.app.state.store
    notifier = request.app.state.notifier
    templates = request.app.state.templates

    order = store.find(order_id)
    if order is None or order.paid:
        return RedirectResponse(url="/cashier", status_code=303)

    if received < order.total:
        return templates.TemplateResponse(
            "cashier.html",
            {
                "request": request,
                "orders": store.all_orders(),
                "error": (
                    f"⚠ 注文ID {order_id} の受取額が不足しています！"
                    f"（必要: ¥{order.total} / 入力: ¥{received}）"
                ),
            },
        )

    confirmed = store.confirm_payment(order_id, received)
    if confirmed is not None:
        background.add_task(notifier.notify_kitchen, confirmed)
        background.add_task(notifier.notify_delivery, confirmed)
    return RedirectResponse(url="/cashier", status_code=303)


@router.get("/cancel/{order_id}", dependencies=[Depends(require_auth)])
async def cancel(order_id: int, request: Request):
    store = request.app.state.store
    order = store.find(order_id)
    if order and order.paid:
        return RedirectResponse(url=f"/cancel_paid/{order_id}", status_code=303)
    store.cancel(order_id)
    return RedirectResponse(url="/cashier", status_code=303)


@router.get("/cancel_paid/{order_id}", dependencies=[Depends(require_auth)])
async def cancel_paid(order_id: int, request: Request, background: BackgroundTasks):
    store = request.app.state.store
    notifier = request.app.state.notifier
    cancelled = store.cancel_paid(order_id)
    if cancelled is not None:
        background.add_task(notifier.notify_cancel, cancelled)
    return RedirectResponse(url="/cashier", status_code=303)


@router.get("/cancel_delivered/{order_id}", dependencies=[Depends(require_auth)])
async def cancel_delivered(order_id: int, request: Request):
    request.app.state.store.unmark_delivered(order_id)
    return RedirectResponse(url="/history", status_code=303)
