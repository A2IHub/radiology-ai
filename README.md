# Radiology AI PoC – SageMaker Pipeline

## Objective
Given uploaded radiology report images, produce:
- Short clinician-friendly summary
- Key findings & red flags
- Follow-up reminders
- Missing information detection

Frontend displays **all outputs** by reading **JSON files from S3**.

---

## Architecture Overview
radiology-ai/
│
├── README.md
├── requirements.txt
├── .gitignore
│
├── pipelines/
│   ├── pipeline.py              # Defines SageMaker Pipeline with FE JSON output
│   ├── parameters.py            # Pipeline parameters (S3 paths, model IDs)
│   └── utils.py                 # Shared helpers
│
├── steps/
│   ├── 01_preprocess/
│   │   ├── preprocess.py        # Image cleanup & validation
│   │   └── Dockerfile
│   │
│   ├── 02_ocr/
│   │   ├── ocr.py                # EasyOCR / Tesseract
│   │   └── Dockerfile
│   │
│   ├── 03_postprocess_text/
│   │   ├── clean_text.py         # Section detection, cleanup
│   │   └── Dockerfile
│   │
│   ├── 04_llm_analysis/
│   │   ├── analyze.py            # Bedrock prompt + structured JSON output
│   │   └── Dockerfile
│   │
│   └── 05_validation/
│       ├── validate_output.py    # JSON schema + status field
│       └── Dockerfile
│
├── schemas/
│   └── output_schema.json        # Enforced LLM output format
│
├── prompts/
│   └── radiology_prompt.txt
│
├── notebooks/
│   └── exploration.ipynb         # OCR & prompt experiments
│
├── infra/
│   ├── iam_policy.json
│   └── sagemaker_role.md
│
├── sample_data/
│   ├── images/
│   └── expected_output.json
│
└── frontend_integration/
    └── example_fetch_json.md     # Example FE code snippet to read JSON from S3


Frontend Upload → S3 (raw-images) → SageMaker Pipeline → S3 (outputs JSON) → Frontend Read & Display
1. User uploads images to:
s3://<bucket>/raw-images/

2. SageMaker Pipeline triggers processing:
- Preprocessing
- OCR extraction
- Text post-processing
- LLM analysis (Amazon Bedrock)
- Validation & JSON formatting
3. Pipeline writes **structured JSON** to:
s3://<bucket>/outputs/<report_id>.json

4. Frontend fetches this JSON via **pre-signed URL** and renders the fields:
- Summary
- Key findings
- Red flags
- Follow-up reminders
- Missing information

---

## Pipeline Steps

### Step 1: Preprocessing
- Clean & normalize images
- Validate formats (PNG, JPG, PDF)
- Save cleaned image to S3

### Step 2: OCR Extraction
- Extract text using **EasyOCR / Tesseract**
- Output raw text JSON for LLM input

### Step 3: Text Post-Processing
- Remove artifacts, normalize text
- Detect sections: Findings, Impression, Recommendations

### Step 4: LLM Analysis
- Structured prompt to Amazon Bedrock
- Output strictly in JSON with all required fields

### Step 5: Validation & Output Formatting
- Validate JSON against schema (`schemas/output_schema.json`)
- Add `"status": "completed"` or `"error"` field
- Save JSON to S3 for frontend consumption

---

## Example JSON Output
```json
{
"status": "completed",
"summary": "CT chest shows a 12 mm right upper lobe pulmonary nodule...",
"key_findings": ["12 mm right upper lobe nodule", "Irregular margins"],
"red_flags": ["Solitary pulmonary nodule >8 mm", "No comparison study"],
"follow_up_reminders": ["Follow-up CT in 3–6 months", "Consider PET-CT if indicated"],
"missing_information": ["Patient smoking history", "Prior imaging comparison"]
}
