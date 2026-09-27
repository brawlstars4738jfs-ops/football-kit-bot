import asyncio
import io
import os
import tempfile

import requests
import replicate

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, BufferedInputFile


BOT_TOKEN = os.environ["BOT_TOKEN"]
REPLICATE_API_TOKEN = os.environ["REPLICATE_API_TOKEN"]


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# Временное хранение фотографии игрока
photos = {}


PROMPT = """
The first image is a football player.
The second image is a football kit.

Dress the football player in EXACTLY the football kit from the second image.

IMPORTANT:
- Preserve the player's face exactly.
- Preserve hairstyle exactly.
- Preserve body proportions.
- Preserve pose and position.
- Preserve the background.
- Replace only the player's clothing with the football kit.
- Reproduce the kit colors, patterns, logos, sponsors, badge and details as accurately as possible.
- Make the result photorealistic.
- Make the kit naturally fit the player's body.
- Do not change the player's identity.
"""


def generate_image(player_bytes, kit_bytes):
    # Создаём временные файлы
    with tempfile.NamedTemporaryFile(
        suffix=".png",
        delete=False
    ) as player_file:

        player_file.write(player_bytes)
        player_path = player_file.name

    with tempfile.NamedTemporaryFile(
        suffix=".png",
        delete=False
    ) as kit_file:

        kit_file.write(kit_bytes)
        kit_path = kit_file.name

    try:
        with open(player_path, "rb") as player_image, \
             open(kit_path, "rb") as kit_image:

            output = replicate.run(
                "flux-kontext-apps/multi-image-kontext-pro",
                input={
                    "input_image_1": player_image,
                    "input_image_2": kit_image,
                    "prompt": PROMPT,
                    "aspect_ratio": "match_input_image",
                    "output_format": "png"
                }
            )

        # Получаем ссылку на готовую картинку
        output_url = str(output)

        response = requests.get(
            output_url,
            timeout=120
        )

        response.raise_for_status()

        return response.content

    finally:
        # Удаляем временные файлы
        try:
            os.remove(player_path)
        except:
            pass

        try:
            os.remove(kit_path)
        except:
            pass


@dp.message(CommandStart())
async def start(message: Message):
    photos.pop(message.from_user.id, None)

    await message.answer(
        "⚽ Привет! Я Football Kit AI!\n\n"
        "Отправь фотографию футболиста,\n"
        "а затем фотографию формы."
    )


@dp.message(F.photo)
async def handle_photo(message: Message):
    user_id = message.from_user.id

    photo = message.photo[-1]

    file = await bot.download(photo)

    if file is None:
        await message.answer(
            "❌ Не получилось загрузить фотографию."
        )
        return

    photo_bytes = file.getvalue()

    # Первое фото — футболист
    if user_id not in photos:
        photos[user_id] = photo_bytes

        await message.answer(
            "✅ Футболист получен!\n\n"
            "Теперь отправь фотографию формы 👕"
        )

        return

    # Второе фото — форма
    player_bytes = photos.pop(user_id)
    kit_bytes = photo_bytes

    await message.answer(
        "🎨 Создаю новую форму...\n"
        "Это может занять некоторое время ⏳"
    )

    try:
        result = await asyncio.to_thread(
            generate_image,
            player_bytes,
            kit_bytes
        )

        await message.answer_photo(
            BufferedInputFile(
                result,
                filename="football_kit.png"
            ),
            caption="⚽ Готово! Форма заменена!"
        )

    except Exception as e:

        print("REPLICATE ERROR:", repr(e))

        await message.answer(
            "❌ Не получилось создать фото.\n\n"
            "Попробуй ещё раз позже."
        )


@dp.message()
async def other_messages(message: Message):
    await message.answer(
        "📸 Отправь фотографию футболиста,\n"
        "а затем фотографию формы."
    )


async def main():
    print("🤖 Football Kit AI запущен!")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
