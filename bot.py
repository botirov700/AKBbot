import asyncio
import os
import tempfile

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile, Message
from mutagen.id3 import APIC, ID3, TIT2, TPE1, ID3NoHeaderError
from PIL import Image

TOKEN = os.getenv("BOT_TOKEN")

router = Router()


class Form(StatesGroup):
    title = State()
    artist = State()
    photo = State()


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Salom! Menga musiqa (audio) tashlang 🎵")


@router.message(F.audio)
async def got_audio(message: Message, state: FSMContext, bot: Bot):
    folder = tempfile.mkdtemp()
    path = os.path.join(folder, "music.mp3")
    await bot.download(message.audio, destination=path)
    await state.update_data(folder=folder, path=path)
    await state.set_state(Form.title)
    await message.answer("Musiqa nomini yozing:")


@router.message(Form.title, F.text)
async def got_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(Form.artist)
    await message.answer("Qo'shiqchi (ijrochi) nomini yozing:")


@router.message(Form.artist, F.text)
async def got_artist(message: Message, state: FSMContext):
    await state.update_data(artist=message.text)
    await state.set_state(Form.photo)
    await message.answer("Endi rasm yuboring 🖼")


@router.message(Form.photo, F.photo)
async def got_photo(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    folder, path = data["folder"], data["path"]
    title, artist = data["title"], data["artist"]

    await message.answer("Tayyorlanmoqda... ⏳")

    # Rasmni yuklab olish
    cover_path = os.path.join(folder, "cover.jpg")
    await bot.download(message.photo[-1], destination=cover_path)

    # Telegram uchun kichik thumbnail (JPEG, 320x320, <200KB)
    thumb_path = os.path.join(folder, "thumb.jpg")
    img = Image.open(cover_path).convert("RGB")
    img.thumbnail((320, 320))
    img.save(thumb_path, "JPEG", quality=85)

    # MP3 ichiga nom, ijrochi va rasm yozish
    try:
        try:
            tags = ID3(path)
        except ID3NoHeaderError:
            tags = ID3()
        tags.delall("APIC")
        tags.add(TIT2(encoding=3, text=title))
        tags.add(TPE1(encoding=3, text=artist))
        with open(cover_path, "rb") as f:
            tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=f.read()))
        tags.save(path)
    except Exception as e:
        print("Teg yozishda xato:", e)

    await message.answer_audio(
        audio=FSInputFile(path, filename=f"{artist} - {title}.mp3"),
        title=title,
        performer=artist,
        thumbnail=FSInputFile(thumb_path),
    )

    await state.clear()
    await message.answer("Tayyor! Yana musiqa tashlashingiz mumkin 🎵")


@router.message(Form.photo)
async def need_photo(message: Message):
    await message.answer("Iltimos, rasm yuboring 🖼")


async def main():
    bot = Bot(TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
