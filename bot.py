import asyncio
import io
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from google import genai
from PIL import Image

BOT_TOKEN = os.environ["BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

MODEL = "gemini-3.1-flash-lite-image"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = genai.Client(api_key=GEMINI_API_KEY)

# Временное хранение первой фотографии
photos = {}

PROMPT = """
The first image shows a football player.
The second image shows a football kit.

Dress the player in exactly this kit.
Preserve the player's face, hairstyle,
body proportions, pose and background.

Reproduce the kit's colors, logos,
sponsors and design as accurately as possible.

Create a photorealistic edited image.
"""

@dp.message(CommandStart())
async def start(message: Message):
    photos.pop(message.from_user.id, None)
    await message.answer(
        "⚽ Привет! Я Football Kit AI!\n\n"
        "Отправь фотографию футболиста, "
        "а затем фотографию формы."
    )


def generate(player_bytes, kit_bytes):
    player = Image.open(
        io.BytesIO(player_bytes)
    ).convert("RGB")

    kit = Image.open(
        io.BytesIO(kit_bytes)
    ).convert("RGB")

    response = client.models.generate_content(
        model=MODEL,
        contents=[PROMPT, player, kit],
    )

    for part in response.parts or []:
        if part.inline_data:
            return part.inline_data.data

    raise RuntimeError("Gemini не вернул изображение")


@dp.message(F.photo)
async def handle_photo(message: Message):
    user_id = message.from_user.id

    photo = message.photo[-1]
    file = await bot.download(photo)

    if user_id not in photos:
        photos[user_id] = file.getvalue()
        await message.answer(
            "✅ Футболист получен!\n"
            "Теперь отправь фотографию формы."
        )
        return

    player_bytes = photos.pop(user_id)
    kit_bytes = file.getvalue()

    await message.answer(
        "🎨 Создаю фотографию. Подожди..."
    )

    try:
        result = await asyncio.to_thread(
            generate,
            player_bytes,
            kit_bytes
        )

        output = io.BytesIO(result)
        output.name = "football_kit.png"

        from aiogram.types import BufferedInputFile

        await message.answer_photo(
            BufferedInputFile(
                output.getvalue(),
                filename="football_kit.png"
            ),
            caption="⚽ Готово! Новая форма!"
        )

    except Exception:
        await message.answer(
            "❌ Не получилось создать фото.\n"
            "Проверь доступ к Gemini API "
            "и попробуй ещё раз."
        )


@dp.message()
async def other_messages(message: Message):
    await message.answer(
        "Отправь фотографию футболиста "
        "и затем фотографию формы. ⚽"
    )


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
