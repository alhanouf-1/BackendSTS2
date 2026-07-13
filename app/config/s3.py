import os
import shutil
import boto3
from botocore.exceptions import ClientError
from typing import BinaryIO
from app.config.settings import settings

class StorageManager:
    def __init__(self):
        self.use_local = settings.USE_LOCAL_STORAGE
        self.local_dir = settings.LOCAL_STORAGE_DIR
        
        if self.use_local:
            os.makedirs(self.local_dir, exist_ok=True)
        else:
            self.s3_client = boto3.client(
                "s3",
                region_name=settings.S3_REGION,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY
            )
            self.bucket_name = settings.S3_BUCKET

    def upload_file(self, file_content: BinaryIO, filename: str, folder: str = "documents") -> str:
        """
        Uploads file to local storage or S3.
        Returns the local path or S3 URL.
        """
        safe_filename = f"{folder}/{filename}"
        
        if self.use_local:
            dest_path = os.path.join(self.local_dir, folder)
            os.makedirs(dest_path, exist_ok=True)
            full_path = os.path.join(dest_path, filename)
            
            with open(full_path, "wb") as buffer:
                shutil.copyfileobj(file_content, buffer)
            
            # Return relative local path
            return f"/static/{safe_filename}"
        else:
            try:
                self.s3_client.upload_fileobj(
                    file_content,
                    self.bucket_name,
                    safe_filename,
                    ExtraArgs={"ACL": "public-read"}
                )
                return f"https://{self.bucket_name}.s3.{settings.S3_REGION}.amazonaws.com/{safe_filename}"
            except ClientError as e:
                # Fallback to local or raise
                raise RuntimeError(f"Failed to upload to S3: {str(e)}")

    def delete_file(self, file_url: str) -> bool:
        """Deletes file from storage. Returns True if deleted successfully."""
        if self.use_local:
            if file_url.startswith("/static/"):
                relative_path = file_url.replace("/static/", "", 1)
                full_path = os.path.join(self.local_dir, relative_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
                    return True
            return False
        else:
            try:
                # Extract key from URL
                key = file_url.split(f"{settings.S3_BUCKET}.s3.{settings.S3_REGION}.amazonaws.com/")[-1]
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
                return True
            except Exception:
                return False

storage_manager = StorageManager()
