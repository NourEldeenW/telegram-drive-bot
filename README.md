# Telegram to Google Drive Video Bot

A production-ready Telegram bot that automatically uploads received videos to Google Drive.

## Features

- Polling-based (no webhook required)
- Supports videos up to 2GB
- Streaming download (no memory buffering)
- Resumable upload with retry logic
- Automatic file sharing link generation
- Proper error handling and logging
- Optimized for free hosting platforms

## Prerequisites

- Python 3.10+
- Telegram Bot Token
- Google Cloud Project with Drive API enabled
- Google OAuth2 credentials

## Setup

### 1. Clone and Install

```bash
git clone <your-repo>
cd telegram-drive-bot
pip install -r requirements.txt
```

### 2. Get Telegram Bot Token

1. Open Telegram and search for `@BotFather`
2. Send `/newbot` command
3. Follow the prompts to create your bot
4. Copy the API token

### 3. Get Google OAuth2 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Drive API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Drive API"
   - Click "Enable"
4. Create OAuth2 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Web application"
   - Add authorized redirect URI: `http://localhost`
   - Click "Create"
   - Note the Client ID and Client Secret

### 4. Get Google Refresh Token

Run this script to obtain your refresh token:

```python
import requests

CLIENT_ID = "your_client_id"
CLIENT_SECRET = "your_client_secret"
REDIRECT_URI = "http://localhost"

# Step 1: Get authorization URL
auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=https://www.googleapis.com/auth/drive.file&access_type=offline&prompt=consent"

print(f"Visit this URL:\n{auth_url}")
print("\nAfter authorization, you'll be redirected to localhost with a 'code' parameter.")
print("Copy that code value and paste it below:")

code = input("Enter the code: ")

# Step 2: Exchange code for tokens
token_url = "https://oauth2.googleapis.com/token"
data = {
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": code,
    "redirect_uri": REDIRECT_URI,
    "grant_type": "authorization_code",
}

response = requests.post(token_url, data=data)
tokens = response.json()

print(f"\nRefresh Token: {tokens['refresh_token']}")
```

### 5. Get Google Drive Folder ID

1. Open Google Drive
2. Navigate to the folder where you want videos uploaded
3. Look at the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
4. Copy the FOLDER_ID from the URL

### 6. Configure Environment Variables

Create a `.env` file (for local development) or set environment variables:

```env
TELEGRAM_TOKEN=your_telegram_bot_token
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REFRESH_TOKEN=your_google_refresh_token
GOOGLE_FOLDER_ID=your_google_drive_folder_id
```

## Local Development

```bash
python bot.py
```

## Deploy on Render

### Create Render Account

1. Go to [Render](https://render.com/) and sign up
2. Connect your GitHub/GitLab repository

### Create Background Worker

1. Click "New" > "Background Worker"
2. Connect your repository
3. Configure:
   - **Name**: telegram-drive-bot
   - **Region**: Choose closest to your users
   - **Branch**: main (or your branch)
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Instance Type**: Free (or paid for better performance)

4. Add Environment Variables:
   - `TELEGRAM_TOKEN`
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REFRESH_TOKEN`
   - `GOOGLE_FOLDER_ID`

5. Click "Create Background Worker"

### Important Notes

- Free tier spins down after inactivity. For 24/7 operation, consider paid tier.
- The bot uses polling, so it will reconnect automatically if connection drops.
- All environment variables must be set before deployment.

## Usage

1. Start the bot (locally or on Render)
2. Open your Telegram bot
3. Send a video file (up to 2GB)
4. The bot will:
   - Confirm receipt
   - Download the video
   - Upload to Google Drive
   - Return a shareable link

## Error Handling

The bot handles:
- Network interruptions with automatic retry
- Upload failures with exponential backoff
- Invalid credentials with proper error messages
- Disk space issues
- File size limits
- Unexpected crashes with cleanup

## Logs

Check Render logs for:
- Download progress
- Upload progress
- Error messages
- Connection status

## License

MIT License
