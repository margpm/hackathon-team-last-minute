from __future__ import annotations

import logging
import secrets
import time
from dataclasses import dataclass

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command

from app.bluesky_client import LiveSourceError
from app.config import settings
from app.contextproof import ContextProofRun, SourceIntegrityError, run_contextproof
from app.llm_client import ContextProofModelError

logger = logging.getLogger(__name__)

dp = Dispatcher()


@dataclass(frozen=True)
class PendingApproval:
    action: str
    user_id: int
    expires_at: float


class ApprovalStore:
    def __init__(self, ttl_seconds: int = 900):
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, PendingApproval] = {}

    def create(self, action: str, user_id: int, now: float | None = None) -> str:
        token = secrets.token_urlsafe(8)
        current_time = time.monotonic() if now is None else now
        self._items[token] = PendingApproval(
            action=action,
            user_id=user_id,
            expires_at=current_time + self.ttl_seconds,
        )
        return token

    def consume(
        self,
        token: str,
        user_id: int,
        now: float | None = None,
    ) -> PendingApproval | None:
        approval = self._items.get(token)
        current_time = time.monotonic() if now is None else now
        if approval is None or approval.user_id != user_id:
            return None
        self._items.pop(token, None)
        if approval.expires_at < current_time:
            return None
        return approval


approval_store = ApprovalStore()


def _clip(value: str, maximum: int = 360) -> str:
    clean = " ".join(value.split())
    if len(clean) <= maximum:
        return clean
    return clean[: maximum - 3].rstrip() + "..."


def format_contextproof(run: ContextProofRun) -> str:
    result = run.analysis
    lines = [
        "CONTEXTPROOF",
        "",
        f"Observed: {len(run.context.posts)} live Bluesky posts",
        "",
        "SUPPORTED SIGNAL",
    ]

    if result.supported_signals:
        for signal in result.supported_signals[:1]:
            lines.append(f"- {_clip(signal.claim, 300)}")
            lines.append(f"  Why: {_clip(signal.reason, 220)}")
    else:
        lines.append("- None established by the observed posts.")

    lines.extend(["", "CONFLICT"])
    if result.conflicts:
        for conflict in result.conflicts[:1]:
            lines.append(f"- {_clip(conflict.topic, 260)}")
            lines.append(f"  A: {_clip(conflict.position_a, 180)}")
            lines.append(f"  B: {_clip(conflict.position_b, 180)}")
    else:
        lines.append("- No material conflict identified.")

    lines.extend(["", "UNKNOWN"])
    if result.unknowns:
        for unknown in result.unknowns[:1]:
            lines.append(f"- {_clip(unknown.question, 280)}")
            lines.append(f"  Why: {_clip(unknown.reason, 220)}")
    else:
        lines.append("- No material unknown identified.")

    lines.extend(
        [
            "",
            "BEST NEXT ACTION",
            _clip(result.recommended_action.title, 320),
            f"Why: {_clip(result.recommended_action.reason, 240)}",
            "",
            "Evidence:",
        ]
    )
    if run.evidence:
        for index, post in enumerate(run.evidence[:5], start=1):
            lines.append(f"{index}. {post.author}: {post.url}")
    else:
        lines.append("No relevant source links were returned.")

    text = "\n".join(lines)
    return text if len(text) <= 3900 else text[:3897].rstrip() + "..."


def approval_markup(token: str) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="APPROVE",
                    callback_data=f"approve:{token}",
                )
            ]
        ]
    )


def format_failure(error: Exception) -> str:
    if isinstance(error, LiveSourceError):
        return f"LIVE_SOURCE_ERROR\n{error}\nNo analysis was generated."
    if isinstance(error, ContextProofModelError):
        return f"MODEL_ERROR\n{error}\nNo analysis was generated."
    if isinstance(error, SourceIntegrityError):
        return "MODEL_ERROR\nAnalysis failed source-integrity validation. No result was shown."
    return "CONTEXTPROOF_ERROR\nThe request failed before a verified result was produced."


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "ContextProof finds which public context matters before an agent acts.\n\n"
        "Send one real question. I will search live Bluesky posts, separate "
        "SUPPORTED SIGNAL / CONFLICT / UNKNOWN, and propose one action for approval."
    )


@dp.message(F.text)
async def handle_message(message: types.Message):
    user_id = message.from_user.id if message.from_user else 0
    logger.info("ContextProof request received from Telegram user %s.", user_id)
    loading_msg = await message.reply("Searching live Bluesky context...")
    try:
        run = await run_contextproof(message.text or "")
        token = approval_store.create(run.analysis.recommended_action.title, user_id)
        await loading_msg.edit_text(
            format_contextproof(run),
            reply_markup=approval_markup(token),
            disable_web_page_preview=True,
        )
    except Exception as error:
        logger.error("ContextProof request failed: %s", type(error).__name__)
        await loading_msg.edit_text(format_failure(error))


@dp.callback_query(F.data.startswith("approve:"))
async def approve_action(callback: types.CallbackQuery):
    token = (callback.data or "").partition(":")[2]
    approval = approval_store.consume(token, callback.from_user.id)
    if approval is None:
        await callback.answer("Approval expired or belongs to another user.", show_alert=True)
        return

    await callback.answer("Action approved")
    if callback.message:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(f"ACTION APPROVED\n\n{approval.action}")


async def start_bot():
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is required to start Telegram polling.")
    bot = Bot(token=settings.bot_token)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
