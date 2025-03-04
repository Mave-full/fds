import asyncio
import logging
import os
import tempfile
import sys
from typing import Dict, Any, Optional

import aiohttp
import whisper
from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from pydub import AudioSegment

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token='7643196810:AAGIK7X6khk1e3pjP77fWKiZzBXFd8jlM70')
dp = Dispatcher()

# Router for handling messages
router = Router()
dp.include_router(router)


# Check if FFmpeg is installed
def check_ffmpeg():
    try:
        import subprocess
        if sys.platform.startswith('win'):
            # On Windows, check if ffmpeg is in PATH
            result = subprocess.run(['where', 'ffmpeg'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                logging.warning("FFmpeg not found in PATH. Please install FFmpeg and add it to your PATH.")
                return False
        else:
            # On Unix-like systems
            result = subprocess.run(['which', 'ffmpeg'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 0:
                logging.warning("FFmpeg not found. Please install FFmpeg.")
                return False
        return True
    except Exception as e:
        logging.error(f"Error checking FFmpeg: {e}")
        return False


# Initialize whisper model (small model for faster processing)
try:
    model = whisper.load_model("small")
    logging.info("Whisper model loaded successfully")
except Exception as e:
    logging.error(f"Error loading Whisper model: {e}")
    model = None

# User data storage
user_data = {}


# Function to transcribe audio using Whisper
async def transcribe_audio(file_path: str) -> str:
    if model is None:
        return "Error: Whisper model not loaded properly."

    try:
        # Run transcription in a separate thread to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: model.transcribe(file_path)
        )
        return result["text"]
    except Exception as e:
        logging.error(f"Error during transcription: {e}")
        return f"Error during transcription: {e}"


# Function to generate summary using API
async def generate_summary(text: str) -> str:
    url = "https://api.hyperbolic.xyz/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtYXR2ZWpuZWJ1ZG92aWNAZ21haWwuY29tIiwiaWF0IjoxNzM4MTQyOTA1fQ.57fd6cA9Aja0Rc2bIj6vMu8JGfv1xxl4Ofuqx8mqEUw"
    }
    data = {
        "messages": [
            {
                "role": "user",
                "content": f"Создай краткий и структурированный конспект из следующего текста: {text}"
            }
        ],
        "model": "meta-llama/Llama-3.3-70B-Instruct",
        "max_tokens": 512,
        "temperature": 0.1,
        "top_p": 0.9
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    response_json = await response.json()
                    content = response_json['choices'][0]['message']['content']
                    return content
                else:
                    error_text = await response.text()
                    logging.error(f"API error: {response.status}, {error_text}")
                    return f"Error: API returned status code {response.status}"
        except Exception as e:
            logging.error(f"Error during API request: {e}")
            return f"Error during summary generation: {e}"


# Start command handler
@router.message(CommandStart())
async def cmd_start(message: Message):
    ffmpeg_installed = check_ffmpeg()
    if not ffmpeg_installed:
        await message.answer(
            "Привет! Для работы бота требуется FFmpeg, но он не найден в системе. "
            "Пожалуйста, установите FFmpeg:\n"
            "- Windows: Скачайте с https://ffmpeg.org/download.html и добавьте в PATH\n"
            "- Linux: sudo apt-get install ffmpeg\n"
            "- macOS: brew install ffmpeg"
        )
    else:
        await message.answer(
            "Привет! Я бот для расшифровки голосовых сообщений и видео. "
            "Отправь мне голосовое сообщение или видео, и я расшифрую его текст. "
            "Затем ты сможешь создать конспект на основе расшифровки."
        )


# Voice message handler
@router.message(F.voice)
async def handle_voice(message: Message):
    user_id = message.from_user.id

    # Check if FFmpeg is installed
    if not check_ffmpeg():
        await message.answer(
            "Для обработки аудио требуется FFmpeg, но он не найден в системе. "
            "Пожалуйста, установите FFmpeg и перезапустите бота."
        )
        return

    # Send processing message
    processing_msg = await message.answer("Обрабатываю голосовое сообщение...")

    try:
        # Download voice message
        voice_file = await bot.get_file(message.voice.file_id)
        voice_path = voice_file.file_path

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_voice:
            voice_file_path = temp_voice.name

        await bot.download_file(voice_path, destination=voice_file_path)

        # Convert ogg to wav for better compatibility with whisper
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            wav_file_path = temp_wav.name

        try:
            audio = AudioSegment.from_ogg(voice_file_path)
            audio.export(wav_file_path, format="wav")
        except Exception as e:
            logging.error(f"Error converting audio: {e}")
            await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
            await message.answer(
                f"Ошибка при конвертации аудио: {e}\n"
                "Убедитесь, что FFmpeg установлен и добавлен в PATH."
            )
            # Clean up files
            try:
                os.unlink(voice_file_path)
                os.unlink(wav_file_path)
            except:
                pass
            return

        # Transcribe audio
        transcription = await transcribe_audio(wav_file_path)

        # Store transcription for this user
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['transcription'] = transcription

        # Create keyboard with summarize button
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="Конспектировать", callback_data="summarize"))

        # Send transcription with button
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
        await message.answer(
            f"Расшифровка:\n\n{transcription}",
            reply_markup=keyboard.as_markup()
        )

        # Clean up temporary files
        try:
            os.unlink(voice_file_path)
            os.unlink(wav_file_path)
        except Exception as e:
            logging.error(f"Error cleaning up files: {e}")

    except Exception as e:
        logging.error(f"Error processing voice message: {e}")
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
        await message.answer(f"Произошла ошибка при обработке голосового сообщения: {e}")


# Video message handler
@router.message(F.video)
async def handle_video(message: Message):
    user_id = message.from_user.id

    # Check if FFmpeg is installed
    if not check_ffmpeg():
        await message.answer(
            "Для обработки видео требуется FFmpeg, но он не найден в системе. "
            "Пожалуйста, установите FFmpeg и перезапустите бота."
        )
        return

    # Send processing message
    processing_msg = await message.answer("Обрабатываю видео...")

    try:
        # Download video
        video_file = await bot.get_file(message.video.file_id)
        video_path = video_file.file_path

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
            video_file_path = temp_video.name

        await bot.download_file(video_path, destination=video_file_path)

        # Extract audio from video
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            wav_file_path = temp_wav.name

        try:
            audio = AudioSegment.from_file(video_file_path, format="mp4")
            audio.export(wav_file_path, format="wav")
        except Exception as e:
            logging.error(f"Error extracting audio from video: {e}")
            await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
            await message.answer(
                f"Ошибка при извлечении аудио из видео: {e}\n"
                "Убедитесь, что FFmpeg установлен и добавлен в PATH."
            )
            # Clean up files
            try:
                os.unlink(video_file_path)
                os.unlink(wav_file_path)
            except:
                pass
            return

        # Transcribe audio
        transcription = await transcribe_audio(wav_file_path)

        # Store transcription for this user
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['transcription'] = transcription

        # Create keyboard with summarize button
        keyboard = InlineKeyboardBuilder()
        keyboard.add(InlineKeyboardButton(text="Конспектировать", callback_data="summarize"))

        # Send transcription with button
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
        await message.answer(
            f"Расшифровка:\n\n{transcription}",
            reply_markup=keyboard.as_markup()
        )

        # Clean up temporary files
        try:
            os.unlink(video_file_path)
            os.unlink(wav_file_path)
        except Exception as e:
            logging.error(f"Error cleaning up files: {e}")

    except Exception as e:
        logging.error(f"Error processing video: {e}")
        await bot.delete_message(chat_id=message.chat.id, message_id=processing_msg.message_id)
        await message.answer(f"Произошла ошибка при обработке видео: {e}")


# Callback query handler for summarize button
@router.callback_query(F.data == "summarize")
async def process_summarize_callback(callback: CallbackQuery):
    user_id = callback.from_user.id

    # Check if user has transcription
    if user_id not in user_data or 'transcription' not in user_data[user_id]:
        await callback.answer("Нет доступной расшифровки. Пожалуйста, отправьте голосовое сообщение или видео.")
        return

    # Get transcription
    transcription = user_data[user_id]['transcription']

    # Send processing message
    await callback.message.edit_text(
        f"Расшифровка:\n\n{transcription}\n\nСоздаю конспект...",
        reply_markup=None
    )

    try:
        # Generate summary
        summary = await generate_summary(transcription)

        # Send summary
        await callback.message.edit_text(
            f"Расшифровка:\n\n{transcription}\n\nКонспект:\n\n{summary}"
        )

    except Exception as e:
        logging.error(f"Error generating summary: {e}")
        await callback.message.edit_text(
            f"Расшифровка:\n\n{transcription}\n\nПроизошла ошибка при создании конспекта: {e}"
        )


# Main function to start the bot
async def main():
    # Check FFmpeg at startup
    ffmpeg_installed = check_ffmpeg()
    if not ffmpeg_installed:
        logging.warning("FFmpeg not found. Audio/video processing will not work correctly.")

    # Skip pending updates
    await bot.delete_webhook(drop_pending_updates=True)
    # Start polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())