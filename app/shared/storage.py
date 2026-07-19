import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

from app.core.config import settings

if settings.R2_ENDPOINT_URL:
    s3_client = boto3.client(
        's3',
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name='auto',
        config=Config(signature_version='s3v4')
    )
else:
    s3_client = None


def upload_file(file_bytes: bytes, key: str, content_type: str) -> str:
    s3_client.put_object(
        Bucket=settings.R2_BUCKET_NAME,
        Key=key,
        Body=file_bytes,
        ContentType=content_type
    )
    return key


def delete_file(key: str) -> None:
    try:
        s3_client.delete_object(
            Bucket=settings.R2_BUCKET_NAME,
            Key=key
        )
    except ClientError as e:
        if e.response['Error']['Code'] != 'NoSuchKey':
            raise


def generate_presigned_url(key: str, expires_in: int = 3600) -> str:
    return s3_client.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': settings.R2_BUCKET_NAME,
            'Key': key
        },
        ExpiresIn=expires_in
    )