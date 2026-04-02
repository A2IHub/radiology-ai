import os
import sys
import json
import logging
import io
import numpy as np
from PIL import Image
from dotenv import load_dotenv

# Fix import path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
)

from Helpers.S3Helper import S3Helper

import easyocr

# -------------------------------
# Setup
# -------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

s3_helper = S3Helper()


# -------------------------------
# Utils
# -------------------------------

def convert_to_serializable(obj):
    """Convert numpy types to JSON-serializable"""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, list):
        return [convert_to_serializable(i) for i in obj]
    elif isinstance(obj, tuple):
        return [convert_to_serializable(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    else:
        return obj


# -------------------------------
# OCR Engine
# -------------------------------

def init_ocr():
    return easyocr.Reader(['en'], gpu=False)


def run_ocr(reader, image_np):
    results = reader.readtext(image_np)
    text = " ".join([r[1] for r in results])
    return text, results


# -------------------------------
# Processing
# -------------------------------

def process_image(reader, bucket, key, output_bucket, output_prefix):
    logger.info(f"OCR Processing: {key}")

    try:
        file_bytes = s3_helper.download_file(bucket, key)

        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        image_np = np.array(image)

        text, raw = run_ocr(reader, image_np)

        if not text.strip():
            logger.warning(f"Empty OCR result: {key}")
            return None

        result = {
            "source_image": key,
            "extracted_text": text,
            "raw_ocr": convert_to_serializable(raw)  # ✅ FIX
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

    input_s3_uri = os.environ.get("INPUT_S3_URI")
    output_s3_uri = os.environ.get("OUTPUT_S3_URI")

    if not input_s3_uri or not output_s3_uri:
        raise ValueError("Missing INPUT_S3_URI or OUTPUT_S3_URI")

    input_bucket, input_prefix = s3_helper.parse_s3_uri(input_s3_uri)
    output_bucket, output_prefix = s3_helper.parse_s3_uri(output_s3_uri)

    logger.info(f"Input: {input_s3_uri}")
    logger.info(f"Output: {output_s3_uri}")


    # -------------------------------
    # Load manifest (FIXED PATH)
    # -------------------------------

    manifest_key = f"{output_prefix}/manifest.json"  # ✅ FIX HERE

    logger.info(f"Loading manifest: {output_s3_uri}/{manifest_key}")

    manifest_bytes = s3_helper.download_file(output_bucket, manifest_key)
    print("loading manifest was done")
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
    # Save manifest
    # -------------------------------

    output_manifest = {
        "ocr_outputs": output_files
    }

    manifest_out_key = f"{output_prefix}/ocr_manifest.json"

    s3_helper.upload_json(output_manifest, output_bucket, manifest_out_key)

    logger.info(f"OCR manifest saved: {manifest_out_key}")
    logger.info("OCR step completed!")


if __name__ == "__main__":
    main()