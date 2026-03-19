"""Vision service for analyzing images with Claude."""

import base64
import logging

logger = logging.getLogger(__name__)


def analyze_image(image_bytes: bytes, api_key: str) -> str:
    """Analyze image with Claude Vision and return description."""
    if not api_key:
        return ""

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": """Опиши что на этом изображении. Если это скриншот профиля Telegram или другой соцсети — извлеки: имя, username (@...), описание/bio, количество подписчиков. Если это визитка — извлеки имя, должность, компанию, контакты. Если другое — кратко опиши. Отвечай на русском, кратко и по делу.""",
                        },
                    ],
                }
            ],
        )

        result = message.content[0].text
        logger.info("Vision analysis complete: %s", result[:100])
        return result

    except Exception as e:
        logger.exception("Vision analysis failed")
        return f"[Анализ фото недоступен: {e}]"
