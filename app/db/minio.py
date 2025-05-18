import base64
from io import BytesIO
from typing import List

import aioboto3
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.core.config import settings
from app.core.logging import logger


class AsyncMinIOManager:
    def __init__(self):
        self.session = aioboto3.Session()
        self.bucket_name = settings.minio_bucket_name
        self.minio_url = settings.minio_url
        self.access_key = settings.minio_access_key
        self.secret_key = settings.minio_secret_key

    async def init_minio(self):
        try:
            await self.create_bucket()
        except Exception as e:
            logger.error(f"Error initializing MinIO: {e}")

    async def create_bucket(self):
        async with self.session.client(
            "s3",
            endpoint_url=self.minio_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            use_ssl=False,
        ) as client:
            try:
                buckets = await client.list_buckets()
                if self.bucket_name not in [
                    bucket["Name"] for bucket in buckets["Buckets"]
                ]:
                    await client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Bucket '{self.bucket_name}' created.")
                else:
                    logger.info(f"Bucket '{self.bucket_name}' already exists.")
            except Exception as e:
                logger.error(f"Error checking or creating bucket: {e}")
                raise e

    async def upload_image(self, file_name: str, image_stream: BytesIO):
        async with self.session.client(
            "s3",
            endpoint_url=settings.minio_url,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            use_ssl=False,
        ) as client:
            try:
                image_stream.seek(0)
                await client.put_object(
                    Bucket=self.bucket_name,
                    Key=file_name,
                    Body=image_stream,
                    ContentType="image/png",
                )
            except Exception as e:
                logger.exception(f"MinIO error upload_image: {e}")
                raise e

    async def upload_file(self, file_name: str, upload_file: UploadFile):
        async with self.session.client(
            "s3",
            endpoint_url=settings.minio_url,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            use_ssl=False,
        ) as client:
            try:
                file_data = await upload_file.read()

                await client.put_object(
                    Bucket=self.bucket_name,
                    Key=file_name,
                    Body=file_data,
                    ContentType=upload_file.content_type,
                )
            except Exception as e:
                logger.exception(f"MinIO error upload_file: {e}")
                raise e

    async def download_image_and_convert_to_base64(self, file_name: str):
        async with self.session.client(
            "s3",
            endpoint_url=settings.minio_url,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            use_ssl=False,
        ) as client:
            try:
                response = await client.get_object(
                    Bucket=self.bucket_name, Key=file_name
                )
                image_data = await response["Body"].read()
                base64_image = base64.b64encode(image_data).decode("utf-8")
                return base64_image
            except Exception as e:
                logger.exception(f"Error downloading image: {e}")
                raise e

    async def create_presigned_url(self, file_name: str, expires: int = 3153600000):
        async with self.session.client(
            "s3",
            endpoint_url=settings.minio_url,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            use_ssl=False,
        ) as client:
            try:
                url = await client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket_name, "Key": file_name},
                    ExpiresIn=expires,
                )
                logger.info(f"Generated presigned URL: {url}")
                return url
            except Exception as e:
                logger.exception(f"Error generating presigned URL: {e}")
                raise e

    async def get_file_from_minio(self, minio_filename):
        async with self.session.client(
            "s3",
            endpoint_url=settings.minio_url,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            use_ssl=False,
        ) as client:
            try:
                response = await client.get_object(
                    Bucket=self.bucket_name, Key=minio_filename
                )
                file_data = await response["Body"].read()  # Read image data
                logger.info(f"Get minio object: {minio_filename}")
                return file_data
            except Exception as e:
                logger.exception(f"Error getting minio object: {e}")
                raise e

    async def bulk_delete(self, keys: List[str]):

        unique_keys = list(set(keys))  # Deduplicate keys
        if not unique_keys:
            return

        async with self.session.client(
            "s3",
            endpoint_url=settings.minio_url,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            use_ssl=False,
        ) as client:
            try:

                for i in range(0, len(unique_keys), 1000):
                    chunk = unique_keys[i : i + 1000]
                    response = await client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={"Objects": [{"Key": k} for k in chunk]},
                    )

                    if errors := response.get("Errors", []):
                        for err in errors:
                            logger.error(
                                f"MinIO delete failed | Key: {err['Key']} "
                                f"| Code: {err['Code']} | Message: {err['Message']}"
                            )
                            raise

            except Exception as e:
                logger.exception(f"MinIO bulk delete error: {str(e)}")
                raise

    async def validate_file_existence(self, filename: str) -> bool:
        try:
            async with self.session.client(
                "s3",
                endpoint_url=settings.minio_url,
                aws_access_key_id=settings.minio_access_key,
                aws_secret_access_key=settings.minio_secret_key,
                use_ssl=False,
            ) as client:
                await client.head_object(Bucket=self.bucket_name, Key=filename)
                return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise


async_minio_manager = AsyncMinIOManager()
