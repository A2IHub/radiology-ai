import os
import io
import sys
import json
import logging
from PIL import Image, ImageOps, ImageFilter
from pdf2image import convert_from_bytes
from dotenv import load_dotenv
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
)
from  Helpers.S3Helper import S3Helper  

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = [".png", ".jpg", ".jpeg", ".pdf"]

# Initialize helper
s3_helper = S3Helper()


# -------------------------------
# Image Processing
# -------------------------------

def preprocess_image(img: Image.Image) -> Image.Image:
    img = ImageOps.grayscale(img)

    max_size = 2000
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size))

    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.SHARPEN)

    return img


def process_pdf(file_bytes):
    return convert_from_bytes(file_bytes)


# -------------------------------
# Main Processing Logic
# -------------------------------

def process_file(bucket, key, output_bucket, output_prefix):
    logger.info(f"Processing: {key}")

    ext = os.path.splitext(key)[1].lower()

    if ext not in SUPPORTED_FORMATS:
        logger.warning(f"Skipping unsupported file: {key}")
        return []

    file_bytes = s3_helper.download_file(bucket, key)

    processed_keys = []

    try:
        if ext == ".pdf":
            pages = process_pdf(file_bytes)

            for i, page in enumerate(pages):
                img = preprocess_image(page)

                out_key = f"{output_prefix}/{os.path.basename(key)}_page_{i}.png"
                s3_helper.upload_image(img, output_bucket, out_key)

                processed_keys.append(out_key)

        else:
            img = Image.open(io.BytesIO(file_bytes))
            img = preprocess_image(img)

            out_key = f"{output_prefix}/{os.path.basename(key)}"
            s3_helper.upload_image(img, output_bucket, out_key)

            processed_keys.append(out_key)

    except Exception as e:
        logger.error(f"Error processing {key}: {str(e)}")

    return processed_keys


# -------------------------------
# Entry Point
# -------------------------------

def main():
    load_dotenv()

    input_s3_uri = os.environ.get("INPUT_S3_URI")
    output_s3_uri = os.environ.get("OUTPUT_S3_URI")

    if not input_s3_uri or not output_s3_uri:
        raise ValueError("Missing INPUT_S3_URI or OUTPUT_S3_URI")

    input_bucket, input_prefix = s3_helper.parse_s3_uri(input_s3_uri)
    output_bucket, output_prefix = s3_helper.parse_s3_uri(output_s3_uri)

    logger.info(f"Input: {input_s3_uri}")
    logger.info(f"Output: {output_s3_uri}")

    files = s3_helper.list_files(input_bucket, input_prefix)

    logger.info(f"Found {len(files)} files")

    all_outputs = []

    for key in files:
        outputs = process_file(
            input_bucket,
            key,
            output_bucket,
            output_prefix
        )
        all_outputs.extend(outputs)

    # Save manifest
    manifest = {
        "processed_files": all_outputs
    }

    manifest_key = f"{output_prefix}/manifest.json"
    s3_helper.upload_json(manifest, output_bucket, manifest_key)

    logger.info(f"Manifest saved: {manifest_key}")


if __name__ == "__main__":
    main()