import os
import logging
import time
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError, ResumableUploadError

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
RETRY_DELAY = 2
RETRY_BACKOFF = 2


class DriveUploader:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        folder_id: str,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.folder_id = folder_id
        self.service = None
        self._init_service()

    def _init_service(self) -> None:
        try:
            credentials = Credentials(
                token=None,
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
            )
            
            credentials.refresh(Request())
            
            self.service = build("drive", "v3", credentials=credentials)
            logger.info("Google Drive service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Drive service: {e}")
            raise

    def _ensure_service(self) -> None:
        if self.service is None:
            self._init_service()

    def upload_file(
        self,
        file_path: str,
        file_name: str,
    ) -> Optional[str]:
        self._ensure_service()
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
        
        file_size = os.path.getsize(file_path)
        logger.info(f"Starting upload: {file_name} ({file_size / (1024*1024):.2f} MB)")
        
        file_metadata = {
            "name": file_name,
            "parents": [self.folder_id],
        }
        
        media = MediaFileUpload(
            file_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024 * 10,
        )
        
        request = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name",
            supportsAllDrives=True,
        )
        
        response = None
        retries = 0
        
        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    if progress % 10 == 0:
                        logger.info(f"Upload progress: {progress}%")
                        
            except ResumableUploadError as e:
                retries += 1
                if retries > MAX_RETRIES:
                    logger.error(f"Upload failed after {MAX_RETRIES} retries: {e}")
                    return None
                
                delay = RETRY_DELAY * (RETRY_BACKOFF ** (retries - 1))
                logger.warning(
                    f"Resumable upload error (attempt {retries}/{MAX_RETRIES}): {e}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)
                
                try:
                    self._init_service()
                    request = self.service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields="id, name",
                        supportsAllDrives=True,
                    )
                except Exception as service_error:
                    logger.error(f"Failed to reinitialize service: {service_error}")
                    
            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504]:
                    retries += 1
                    if retries > MAX_RETRIES:
                        logger.error(f"Upload failed after {MAX_RETRIES} retries: {e}")
                        return None
                    
                    delay = RETRY_DELAY * (RETRY_BACKOFF ** (retries - 1))
                    logger.warning(
                        f"HTTP error {e.resp.status} (attempt {retries}/{MAX_RETRIES}). "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    
                    try:
                        self._init_service()
                        request = self.service.files().create(
                            body=file_metadata,
                            media_body=media,
                            fields="id, name",
                            supportsAllDrives=True,
                        )
                    except Exception as service_error:
                        logger.error(f"Failed to reinitialize service: {service_error}")
                else:
                    logger.error(f"HTTP error during upload: {e}")
                    return None
                    
            except Exception as e:
                logger.error(f"Unexpected error during upload: {e}", exc_info=True)
                return None
        
        if response:
            file_id = response.get("id")
            logger.info(f"Upload completed: {file_name} (ID: {file_id})")
            
            try:
                shareable_link = self._make_shareable(file_id)
                return shareable_link
            except Exception as e:
                logger.error(f"Failed to make file shareable: {e}")
                return f"https://drive.google.com/file/d/{file_id}/view"
        
        return None

    def _make_shareable(self, file_id: str) -> str:
        permission = {
            "type": "anyone",
            "role": "reader",
        }
        
        self.service.permissions().create(
            fileId=file_id,
            body=permission,
            supportsAllDrives=True,
        ).execute()
        
        return f"https://drive.google.com/file/d/{file_id}/view"
