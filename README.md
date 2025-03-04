# Telegram Transcription and Summarization Bot

This bot transcribes voice messages and videos sent by users, then offers to create a summary of the transcribed text.

## Features

- Processes voice messages and videos from multiple users simultaneously
- Transcribes audio using OpenAI's Whisper model
- Generates summaries using the Hyperbolic API
- Handles multiple requests from the same user
- Provides a simple interface with inline buttons

## Requirements

- Python 3.7+
- FFmpeg installed on your system
- Telegram Bot Token

## Installation

1. Install FFmpeg on your system:
   - Ubuntu/Debian: `sudo apt-get install ffmpeg`
   - macOS: `brew install ffmpeg`
   - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set your Telegram Bot Token:
   ```
   export BOT_TOKEN="your_bot_token_here"
   ```
   Or edit the `bot.py` file and replace `YOUR_BOT_TOKEN_HERE` with your actual token.

## Usage

1. Start the bot:
   ```
   python bot.py
   ```

2. In Telegram, send a voice message or video to the bot.

3. The bot will transcribe the audio and display the text.

4. Click the "Конспектировать" button to generate a summary.

## Technical Details

- Uses aiogram 3.0 for Telegram API interaction
- Implements OpenAI's Whisper for speech recognition
- Uses aiohttp for asynchronous API requests
- Handles file conversions with pydub
- Implements proper error handling and user session management

## Limitations

- The Whisper "small" model is used by default for faster processing. For better accuracy but slower processing, you can change to "medium" or "large" in the code.
- Processing large videos may take some time depending on your server's capabilities.
- The API has rate limits that may affect the bot's performance with many simultaneous users.