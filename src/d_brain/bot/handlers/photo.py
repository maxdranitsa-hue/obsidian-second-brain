"""Photo message handler."""

import logging
from datetime import datetime

from aiogram import Bot, Router
from aiogram.types import Message

from d_brain.config import get_settings
from d_brain.services.session import SessionStore
from d_brain.services.storage import VaultStorage
from d_brain.services.vision import analyze_image

router = Router(name="photo")
logger = logging.getLogger(__name__)


@router.message(lambda m: m.photo is not None)
async def handle_photo(message: Message, bot: Bot) -> None:
    """Handle photo messages."""
    if not message.photo or not message.from_user:
        return

    settings = get_settings()
    storage = VaultStorage(settings.vault_path)

    # Get largest photo
    photo = message.photo[-1]

    try:
        file = await bot.get_file(photo.file_id)
        if not file.file_path:
            await message.answer("Failed to download photo")
            return

        file_bytes = await bot.download_file(file.file_path)
        if not file_bytes:
            await message.answer("Failed to download photo")
            return

        timestamp = datetime.fromtimestamp(message.date.timestamp())
        photo_bytes = file_bytes.read()

        # Determine extension from file path
        extension = "jpg"
        if file.file_path and "." in file.file_path:
            extension = file.file_path.rsplit(".", 1)[-1]

        # Save photo and get relative path
        relative_path = storage.save_attachment(
            photo_bytes,
            timestamp.date(),
            timestamp,
            extension,
        )

        # Analyze image with Claude Vision
        await message.answer("📷 Анализирую фото...")
        vision_result = analyze_image(photo_bytes, settings.anthropic_api_key)

        # Build content with embed + vision analysis + caption
        content = f"![[{relative_path}]]"
        if vision_result:
            content += f"\n\n🔍 **Анализ:** {vision_result}"
        if message.caption:
            content += f"\n\n📝 **Подпись:** {message.caption}"

        storage.append_to_daily(content, timestamp, "[photo]")

        # Log to session
        session = SessionStore(settings.vault_path)
        session.append(
            message.from_user.id,
            "photo",
            path=relative_path,
            caption=message.caption,
            vision=vision_result[:100] if vision_result else None,
            msg_id=message.message_id,
        )

        # Reply with analysis result
        reply = "📷 ✓ Сохранено"
        if vision_result:
            reply += f"\n\n🔍 {vision_result}"
        await message.answer(reply)
        logger.info("Photo saved with vision: %s", relative_path)

    except Exception as e:
        logger.exception("Error processing photo")
        await message.answer(f"Error: {e}")
