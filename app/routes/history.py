"""履歴画面 + 一括クリア + robots.txt。"""
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse, RedirectResponse

from app.auth import require_auth

router = APIRouter()

PER_PAGE = 30


@router.get("/history", dependencies=[Depends(require_auth)])
async def history(request: Request, page: int = Query(1, ge=1)):
    store = request.app.state.store
    templates = request.app.state.templates

    orders = store.all_orders()
    total_pages = max(1, (len(orders) + PER_PAGE - 1) // PER_PAGE)
    page = min(page, total_pages)
    start = (page - 1) * PER_PAGE
    paged = orders[start:start + PER_PAGE]

    return templates.TemplateResponse(
        "history.html",
        {
            "request": request,
            "orders": paged,
            "page": page,
            "total_pages": total_pages,
            "stock": store.stock,
            **store.stats(),
        },
    )


@router.get("/history/clear", dependencies=[Depends(require_auth)])
async def clear_history(request: Request):
    request.app.state.store.clear()
    return RedirectResponse(url="/history", status_code=303)


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    return "User-agent: *\nDisallow: /\n"
