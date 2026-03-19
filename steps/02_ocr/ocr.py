import os
import sys
import json
import logging
import io
from PIL import Image
from dotenv import load_dotenv
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
)
from Helpers.S3Helper import S3Helper

# OCR engine
import easyocr

# -------------------------------
# Setup
# -------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

s3_helper = S3Helper()


# -------------------------------
# OCR Engine
# -------------------------------

def init_ocr():
    """Initialize EasyOCR reader"""
    reader = easyocr.Reader(['en'], gpu=False)
    return reader


def run_ocr(reader, image):
    """Run OCR and return clean text + raw output"""
    results = reader.readtext(image)

    text = " ".join([r[1] for r in results])

    return text, results


# -------------------------------
# Processing
# -------------------------------

def process_image(reader, bucket, key, output_bucket, output_prefix):
    logger.info(f"OCR Processing: {key}")

    try:
        file_bytes = s3_helper.download_file(bucket, key)
        image = Image.open(io.BytesIO(file_bytes))

        text, raw = run_ocr(reader, image)

        result = {
            "source_image": key,
            "extracted_text": text,
            "raw_ocr": raw
        }

        out_key = f"{output_prefix}/{os.path.basename(key)}.json"

        s3_helper.upload_json(result, output_bucket, out_key)

        return out_key

    except Exception as e:
        logger.error(f"Error processing {key}: {str(e)}")
        return None


# -------------------------------
# Main
# -------------------------------

def main():
    load_dotenv()

    input_s3_uri = os.environ.get(
        "INPUT_S3_URI"    )

    output_s3_uri = os.environ.get(
        "OUTPUT_S3_URI"    )

    input_bucket, input_prefix = s3_helper.parse_s3_uri(input_s3_uri)
    output_bucket, output_prefix = s3_helper.parse_s3_uri(output_s3_uri)

    logger.info(f"Input: {input_s3_uri}")
    logger.info(f"Output: {output_s3_uri}")

    # -------------------------------
    # Load manifest from preprocessing
    # -------------------------------

    manifest_key = f"{input_prefix}/manifest.json"

    manifest_bytes = s3_helper.download_file(input_bucket, manifest_key)
    manifest = json.loads(manifest_bytes)

    image_keys = manifest.get("processed_files", [])

    logger.info(f"Found {len(image_keys)} images")

    # -------------------------------
    # Init OCR
    # -------------------------------

    reader = init_ocr()

    output_files = []

    for key in image_keys:
        out = process_image(
            reader,
            input_bucket,
            key,
            output_bucket,
            output_prefix
        )
        if out:
            output_files.append(out)

    # -------------------------------
    # Save manifest for next step
    # -------------------------------

    output_manifest = {
        "ocr_outputs": output_files
    }

    manifest_out_key = f"{output_prefix}/manifest.json"

    s3_helper.upload_json(output_manifest, output_bucket, manifest_out_key)

    logger.info(f"OCR manifest saved: {manifest_out_key}")
    logger.info("OCR step completed!")


if __name__ == "__main__":
    main()