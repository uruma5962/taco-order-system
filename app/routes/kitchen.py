"""厨房・提供画面と「提供完了」ボタン。"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.auth import require_auth

router = APIRouter()


@router.get("/kitchen", dependencies=[Depends(require_auth)])
async def kitchen(request: Request):
    store = request.app.state.store
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "kitchen.html",
        {"request": request, "orders": store.all_orders()},
    )


@router.get("/kitchen/deliver/{order_id}", dependencies=[Depends(require_auth)])
async def deliver(order_id: int, request: Request):
    request.app.state.store.mark_delivered(order_id)
    return RedirectResponse(url="/kitchen", status_code=303)
