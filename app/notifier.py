"""厨房・提供への通知を抽象化する。

LogNotifier: ターミナルにログ出力するだけ。Discord トークン不要でデモ可能。
DiscordNotifier: discord.py で実チャンネルに送る屋台運用版。ボタンで状態遷移する。

通知バックエンドの切替は config.py の NOTIFIER_BACKEND で行う。
依存（discord.py）は DiscordNotifier 内で遅延 import しているので、
log バックエンドのみで運用する場合は discord.py が壊れていても影響しない。
"""
from __future__ import annotations

import logging
from typing import Protocol

from app.models import Order

logger = logging.getLogger(__name__)


class Notifier(Protocol):
    async def startup(self) -> None: ...
    async def shutdown(self) -> None: ...
    async def notify_kitchen(self, order: Order) -> None: ...
    async def notify_delivery(self, order: Order) -> None: ...
    async def notify_cancel(self, order: Order) -> None: ...


def _kitchen_body(order: Order) -> str:
    lines = [f"  - {n} x {q}" for n, q in order.kitchen_dishes()]
    if order.irregular:
        lines.append(f"  📝 イレギュラー: {order.irregular}")
    return "\n".join(lines) if lines else "  （料理なし）"


def _all_items_body(order: Order) -> str:
    lines = [f"  - {n} x {q}" for n, q in order.items.items() if q > 0]
    if order.irregular:
        lines.append(f"  📝 イレギュラー: {order.irregular}")
    return "\n".join(lines) if lines else "  （商品なし）"


class LogNotifier:
    """Discord 連携を持たないデモ用 Notifier。"""

    async def startup(self) -> None:
        logger.info("LogNotifier: started (Discord 連携なし)")

    async def shutdown(self) -> None:
        logger.info("LogNotifier: stopped")

    async def notify_kitchen(self, order: Order) -> None:
        if not order.kitchen_dishes() and not order.irregular:
            return
        logger.info("🍳 Kitchen [注文ID %d]\n%s", order.id, _kitchen_body(order))

    async def notify_delivery(self, order: Order) -> None:
        logger.info("🚚 Delivery [注文ID %d]\n%s", order.id, _all_items_body(order))

    async def notify_cancel(self, order: Order) -> None:
        logger.info("❌ Cancel [注文ID %d]\n%s", order.id, _all_items_body(order))


class DiscordNotifier:
    """屋台運用版。会計確定時に厨房・提供チャンネルに送信、ボタンで状態遷移する。

    discord.py を遅延 import しているため、Discord を使わない採用担当が
    discord.py のインストール失敗で詰まることはない。
    """

    def __init__(
        self,
        *,
        token: str,
        kitchen_channel_id: int,
        delivery_channel_id: int,
        store,
    ) -> None:
        import asyncio
        import discord
        from discord.ext import commands

        self._asyncio = asyncio
        self._discord = discord
        self._token = token
        self._kitchen_channel_id = kitchen_channel_id
        self._delivery_channel_id = delivery_channel_id
        self._store = store

        intents = discord.Intents.default()
        self._bot = commands.Bot(command_prefix="!", intents=intents)
        self._kitchen_channel = None
        self._delivery_channel = None
        self._loop = None

        @self._bot.event
        async def on_ready():
            self._kitchen_channel = self._bot.get_channel(kitchen_channel_id)
            self._delivery_channel = self._bot.get_channel(delivery_channel_id)
            self._loop = asyncio.get_running_loop()
            logger.info(
                "Discord bot ready (kitchen=%s, delivery=%s)",
                self._kitchen_channel, self._delivery_channel,
            )

    async def startup(self) -> None:
        import threading
        threading.Thread(target=lambda: self._bot.run(self._token), daemon=True).start()

    async def shutdown(self) -> None:
        # daemon thread はプロセス終了時に自動で止まる
        pass

    def _schedule(self, coro) -> None:
        if self._loop is None:
            logger.warning("Discord bot not ready; notification skipped")
            return
        self._asyncio.run_coroutine_threadsafe(coro, self._loop)

    async def notify_kitchen(self, order: Order) -> None:
        async def _send() -> None:
            if self._kitchen_channel is None:
                return
            dishes = order.kitchen_dishes()
            if not dishes and not order.irregular:
                return
            taco_total = sum(q for n, q in dishes if "タコス" in n)
            lines = [f"　- {n} x {q}" for n, q in dishes]
            if order.irregular:
                lines.append(f"📝 イレギュラー: {order.irregular}")
            msg = f"**【注文ID: {order.id}】**\n\n"
            if taco_total > 0:
                msg += f"🌮 タコス計 {taco_total} 個\n"
            msg += "--------------------------------\n"
            msg += "**内容:**\n" + "\n".join(lines)
            await self._kitchen_channel.send(msg, view=self._kitchen_view(order.id))

        self._schedule(_send())

    async def notify_delivery(self, order: Order) -> None:
        async def _send() -> None:
            if self._delivery_channel is None:
                return
            lines = [f"- {n} x {q}" for n, q in order.items.items() if q > 0]
            if order.irregular:
                lines.append(f"📝 イレギュラー: {order.irregular}")
            body = "\n".join(lines) if lines else "（商品なし）"
            await self._delivery_channel.send(
                f"\n**【注文ID: {order.id}】**\n\n**内容:**\n{body}",
                view=self._delivery_view(order.id),
            )

        self._schedule(_send())

    async def notify_cancel(self, order: Order) -> None:
        async def _send() -> None:
            text = ", ".join(f"{n} x {q}" for n, q in order.items.items() if q > 0) or "商品なし"
            msg = f"❌ **注文ID {order.id} がキャンセルされました**\n📦 内容: {text}"
            for ch in (self._kitchen_channel, self._delivery_channel):
                if ch:
                    await ch.send(msg)

        self._schedule(_send())

    def _kitchen_view(self, order_id: int):
        discord = self._discord
        store = self._store

        class CompleteButton(discord.ui.View):
            def __init__(self) -> None:
                super().__init__(timeout=None)
                btn = discord.ui.Button(
                    label="調理中",
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"complete_{order_id}",
                )
                btn.callback = self.complete
                self.add_item(btn)

            async def complete(self, interaction) -> None:
                store.mark_in_kitchen(order_id)
                self.clear_items()
                self.add_item(
                    discord.ui.Button(
                        label="調理完了",
                        style=discord.ButtonStyle.success,
                        disabled=True,
                    )
                )
                await interaction.response.edit_message(view=self)

        return CompleteButton()

    def _delivery_view(self, order_id: int):
        discord = self._discord
        store = self._store

        class DeliverButton(discord.ui.View):
            def __init__(self) -> None:
                super().__init__(timeout=None)
                btn = discord.ui.Button(
                    label="提供完了",
                    style=discord.ButtonStyle.primary,
                    custom_id=f"deliver_{order_id}",
                )
                btn.callback = self.deliver
                self.add_item(btn)

            async def deliver(self, interaction) -> None:
                store.mark_delivered(order_id)
                self.clear_items()
                self.add_item(
                    discord.ui.Button(
                        label="提供済み",
                        style=discord.ButtonStyle.success,
                        disabled=True,
                    )
                )
                await interaction.response.edit_message(view=self)

        return DeliverButton()
