# deep-cuneiform
DeepSeek OCR for cuneiform

As far as I know, this is the first-ever DeepSeek-OCR fine-tuned on Sumerian cuneiform.

Placeholder for results

Zero-shot on test.jpg: ...

After 60-step fine-tune: ....

## Setup
- Install: `uv sync`
- Python: 3.11.9 (pinned in .python-version)

## Usage
1. Download data: `uv run python data/download_cdli.py --limit 10` (downloads from CDLI using cdli_cat.csv; adjust limit as needed)
2. Fine-tune: `uv run python train.py` (saves to models/)