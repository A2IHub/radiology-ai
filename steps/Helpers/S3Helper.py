import io
import json
import boto3
import logging


class S3Helper:
    def __init__(self, region_name=None):
        """
        Initialize S3 client
        """
        self.s3 = boto3.client("s3", region_name=region_name)
        self.logger = logging.getLogger(__name__)

    # -------------------------------
    # URI Helpers
    # -------------------------------

    @staticmethod
    def parse_s3_uri(s3_uri):
        """Split S3 URI into bucket and key"""
        assert s3_uri.startswith("s3://"), "Invalid S3 path"
        parts = s3_uri.replace("s3://", "").split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        return bucket, key

    # -------------------------------
    # S3 Operations
    # -------------------------------

    def list_files(self, bucket, prefix):
        """List all files under a prefix"""
        paginator = self.s3.get_paginator("list_objects_v2")
        files = []

        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                files.append(obj["Key"])

        return files

    def download_file(self, bucket, key):
        """Download file from S3 into memory"""
        self.logger.info(f"Downloading: s3://{bucket}/{key}")
        response = self.s3.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()

    def upload_image(self, image, bucket, key):
        """Upload PIL image to S3 as PNG"""
        self.logger.info(f"Uploading image: s3://{bucket}/{key}")

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        self.s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=buffer,
            ContentType="image/png"
        )

    def upload_json(self, data, bucket, key):
        """Upload JSON to S3"""
        self.logger.info(f"Uploading JSON: s3://{bucket}/{key}")

        self.s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(data),
            ContentType="application/json"
        )

    def file_exists(self, bucket, key):
        """Check if file exists in S3"""
        try:
            self.s3.head_object(Bucket=bucket, Key=key)
            return True
        except Exception:
            return False