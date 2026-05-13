"""FastAPI アプリのエントリポイント。

責務：
- 環境変数から Notifier を組み立て、OrderStore と一緒に app.state に載せる
- 各機能のルーターを束ねる
- ルーター側からは request.app.state 経由で store/notifier/templates を取り出す
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.notifier import DiscordNotifier, LogNotifier, Notifier
from app.routes import cashier, history, kitchen, order
from app.store import OrderStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def _build_notifier(store: OrderStore) -> Notifier:
    if settings.notifier_backend == "discord" and settings.discord_token:
        logger.info(
            "Using DiscordNotifier (kitchen=%s, delivery=%s)",
            settings.kitchen_channel_id, settings.delivery_channel_id,
        )
        return DiscordNotifier(
            token=settings.discord_token,
            kitchen_channel_id=settings.kitchen_channel_id,
            delivery_channel_id=settings.delivery_channel_id,
            store=store,
        )
    if settings.notifier_backend == "discord":
        logger.warning(
            "NOTIFIER_BACKEND=discord ですが DISCORD_TOKEN が空です。LogNotifier にフォールバック。"
        )
    return LogNotifier()


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = OrderStore()
    notifier = _build_notifier(store)
    app.state.store = store
    app.state.notifier = notifier
    app.state.templates = Jinja2Templates(directory="templates")
    await notifier.startup()
    yield
    await notifier.shutdown()


app = FastAPI(title="Taco Order System", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(order.router)
app.include_router(cashier.router)
app.include_router(kitchen.router)
app.include_router(history.router)
