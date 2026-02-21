import os
import logging
import tempfile
import asyncio
import httpx
from datetime import datetime
from typing import Optional

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from drive import DriveUploader

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = os.environ.get("GOOGLE_REFRESH_TOKEN")
GOOGLE_FOLDER_ID = os.environ.get("GOOGLE_FOLDER_ID")

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024

drive_uploader: Optional[DriveUploader] = None


async def download_video_streaming(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    file_id: str,
    temp_path: str,
) -> bool:
    try:
        file = await context.bot.get_file(file_id)
        total_size = file.file_size or 0
        
        downloaded = 0
        start_time = datetime.now()
        
        async with file.custom_request_context():
            url = file.file_path
            if not url:
                return False
            
            timeout = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    
                    with open(temp_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=CHUNK_SIZE):
                            f.write(chunk)
                            downloaded += len(chunk)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Downloaded {downloaded / (1024*1024):.2f} MB in {elapsed:.2f}s "
            f"({downloaded / elapsed / 1024 / 1024:.2f} MB/s)"
        )
        return True
        
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return False


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.video:
        return
    
    video = update.message.video
    file_id = video.file_id
    file_name = video.file_name or f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    file_size = video.file_size or 0
    
    logger.info(f"Received video: {file_name}, size: {file_size / (1024*1024):.2f} MB")
    
    if file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            f"Error: File too large. Maximum size is 2GB."
        )
        return
    
    status_message = await update.message.reply_text("Downloading video...")
    
    temp_file = None
    temp_path = None
    
    try:
        temp_file = tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=os.path.splitext(file_name)[1] or ".mp4",
            delete=False,
        )
        temp_path = temp_file.name
        temp_file.close()
        
        download_success = await download_video_streaming(
            update, context, file_id, temp_path
        )
        
        if not download_success:
            await status_message.edit_text("Error: Failed to download video.")
            return
        
        await status_message.edit_text("Uploading to Google Drive...")
        
        drive_link = await asyncio.to_thread(
            drive_uploader.upload_file,
            temp_path,
            file_name,
        )
        
        if drive_link:
            await status_message.edit_text(
                f"Video uploaded successfully!\n\n{drive_link}"
            )
        else:
            await status_message.edit_text("Error: Failed to upload to Google Drive.")
            
    except Exception as e:
        logger.error(f"Error processing video: {e}", exc_info=True)
        try:
            await status_message.edit_text(f"Error: {str(e)}")
        except Exception:
            await update.message.reply_text(f"Error: {str(e)}")
            
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info(f"Cleaned up temporary file: {temp_path}")
            except Exception as e:
                logger.error(f"Failed to delete temp file: {e}")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.document:
        return
    
    document = update.message.document
    
    mime_type = document.mime_type or ""
    if not mime_type.startswith("video/"):
        return
    
    file_id = document.file_id
    file_name = document.file_name or f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    file_size = document.file_size or 0
    
    logger.info(f"Received video document: {file_name}, size: {file_size / (1024*1024):.2f} MB")
    
    if file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            f"Error: File too large. Maximum size is 2GB."
        )
        return
    
    status_message = await update.message.reply_text("Downloading video...")
    
    temp_file = None
    temp_path = None
    
    try:
        temp_file = tempfile.NamedTemporaryFile(
            mode="wb",
            suffix=os.path.splitext(file_name)[1] or ".mp4",
            delete=False,
        )
        temp_path = temp_file.name
        temp_file.close()
        
        download_success = await download_video_streaming(
            update, context, file_id, temp_path
        )
        
        if not download_success:
            await status_message.edit_text("Error: Failed to download video.")
            return
        
        await status_message.edit_text("Uploading to Google Drive...")
        
        drive_link = await asyncio.to_thread(
            drive_uploader.upload_file,
            temp_path,
            file_name,
        )
        
        if drive_link:
            await status_message.edit_text(
                f"Video uploaded successfully!\n\n{drive_link}"
            )
        else:
            await status_message.edit_text("Error: Failed to upload to Google Drive.")
            
    except Exception as e:
        logger.error(f"Error processing video: {e}", exc_info=True)
        try:
            await status_message.edit_text(f"Error: {str(e)}")
        except Exception:
            await update.message.reply_text(f"Error: {str(e)}")
            
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info(f"Cleaned up temporary file: {temp_path}")
            except Exception as e:
                logger.error(f"Failed to delete temp file: {e}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)


async def post_init(application: Application) -> None:
    global drive_uploader
    
    required_vars = [
        "TELEGRAM_TOKEN",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_REFRESH_TOKEN",
        "GOOGLE_FOLDER_ID",
    ]
    
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    drive_uploader = DriveUploader(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        refresh_token=GOOGLE_REFRESH_TOKEN,
        folder_id=GOOGLE_FOLDER_ID,
    )
    
    logger.info("Bot initialized successfully")


def main() -> None:
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN environment variable is required")
    
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .read_timeout(300)
        .write_timeout(300)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
    )
    
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.Document.VIDEO, handle_document))
    application.add_error_handler(error_handler)
    
    logger.info("Starting bot with polling...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=False,
    )


if __name__ == "__main__":
    main()
