# deep-cuneiform
DeepSeek OCR for cuneiform tablets using LoRA fine-tuning on Sumerian and Akkadian texts.

This project fine-tunes DeepSeek-OCR for recognizing cuneiform script from images, focusing on Early Dynastic to Old Babylonian periods (ca. 2900-1600 BCE).

## Setup

### Prerequisites
- Python 3.11+
- uv (Python package manager): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Git and Git LFS for data download

### Install Dependencies
```bash
uv sync
```

### Download CDLI Data
The project uses metadata from the CDLI GitHub data dump. Clone it into the `data/` directory:

```bash
git clone https://github.com/cdli-gh/data data/cdli-gh-data
cd data/cdli-gh-data
git lfs fetch --all  # Downloads large files like ATF texts
```

**Note**: This repo is large (~GB). Alternatively, you can download just the catalogue CSV manually from [CDLI's site](https://cdli.ucla.edu/downloads.html) and place `cdli_cat.csv` in `data/cdli-gh-data/`, but the full repo provides additional ATF files for reference.

## Usage

### Download Training Data
Download high-quality Sumerian tablets with images and transliterations, filtered by historical period:

```bash
uv run python tools/download_cdli.py
```

- Focuses on Early Dynastic to Old Babylonian periods
- Requires images and ATF transliterations
- Minimum ATF length for quality
- Resumable downloads with `data/download_state.json`
- Saves images to `data/images/` and ATF to `data/annotations/`

### Download Individual ATF Files
Download ATF transliteration for a specific tablet by artifact ID:

```bash
uv run python tools/download_cdli.py --artifact_id 663
```

- Fetches ATF directly from CDLI API
- Updates download state automatically
- Useful for getting specific tablets not in bulk download

### Lookup Artifacts
Get comprehensive details for a specific artifact by ID:

```bash
uv run python tools/lookup_cdli.py 663
```

- Shows image path, period, quality status
- Displays full ATF transliteration
- Fetches English translation from CDLI API
- Provides attempted Sumerian-to-English translation using dictionaries

### Translate ATF Text
Translate raw ATF files or input using built-in multi-language dictionaries:

```bash
uv run python tools/translate_atf.py data/annotations/cdli_P000723.atf
# Or for artifact ID with auto language detection:
uv run python tools/translate_atf.py --id 663
# Or specify language explicitly:
uv run python tools/translate_atf.py --id 241859 --language akkadian
```

- **Automatic language detection** based on ATF `#atf: lang` tags and period
- **Multi-language support**: Sumerian, Akkadian, and related languages
- **Extensible translator system** for adding new languages
- Uses specialized dictionaries for each language (`data/dictionaries/`)

### Visualize Tablets
Generate PNG images showing tablet structure with cuneiform glyphs, ATF text, and translations:

```bash
uv run python tools/visualize_tablet.py 663
```

- Header with artifact ID, period, quality
- Three-column layout: Line number | Cuneiform glyphs | ATF text | English translation
- Handles @/$ directives as separate lines
- Uses Unicode cuneiform fonts (Noto Sans Cuneiform prioritized)
- Outputs to `data/visualizations/{id}_tablet.png`

![Example Tablet Visualization](docs/images/example_tablet_visualization.png)
*Example visualization of CDLI artifact 663 showing cuneiform glyphs, ATF text, and English translations*

## Data Structure
- `data/images/`: Downloaded tablet images
- `data/annotations/`: ATF transliteration files
- `data/visualizations/`: Generated PNG visualizations
- `data/download_state.json`: Download progress and quality flags
- `data/dictionaries/`: Translation dictionaries (manual Sumerian, proto-cuneiform, etc.)

## Training (GPU Required)
Once sufficient data is downloaded:

```bash
uv run python train.py
```

## Language Support

The system now supports multiple cuneiform languages with automatic detection:

- **Sumerian**: Primary language with comprehensive dictionary
- **Akkadian**: Semitic language using cuneiform script
- **Auto-detection**: Based on ATF `#atf: lang` tags (sux, akk, qeb) or period metadata
- **Extensible**: Easy to add new languages by subclassing `BaseTranslator`

### Language Coverage

| Language | ATF Tag | Period Support | Dictionary Status |
|----------|---------|----------------|-------------------|
| Sumerian | `sux` | All periods | Comprehensive (~120 signs) |
| Akkadian | `akk` | OB, MB, NA, NB | Basic (~30 signs) |
| Eblaite | `qeb` | Ebla | Uses Akkadian fallback |
| Assyrian | `akk-x-stdbab` | Neo-Assyrian | Basic Akkadian support |

## Unicode & Font Support

| Script Type | Unicode Support | Font Status |
|-------------|-----------------|-------------|
| Standard Cuneiform (Sumerian/Akkadian) | Full (U+12000–U+123FF) | Noto Sans Cuneiform ✅ |
| Proto-Cuneiform (ED IIIa/b) | PUA glyphs only | Santakku, LAK fonts ✅ |

**Note**: The same Noto Sans Cuneiform font works for both Sumerian and Akkadian since they use the same cuneiform script.

## Notes
- GPU training requires Flash Attention and CUDA libraries (auto-installed via uv).
- Data is sourced from CDLI (Cuneiform Digital Library Initiative).
- ATF to Unicode conversion uses custom mapping via `lib/atf2unicode/main.py`; expand dictionaries for better coverage.
- Visualizations support Unicode cuneiform rendering in compatible viewers.
- Download script automatically resumes interrupted downloads.

### TODO: Fully Parse ATF Compound & Variant Signs

> **Goal**: Convert complex ATF like `|(GISZx(DIN.DIN))~a|#` → `U+12459` (𒑙) + damage marker

#### Current Status
- [x] Simple signs: `GISZ` → `U+12113`
- [x] Basic compounds: `GISZxDIN` → `U+12451`
- [x] Full ATF syntax: `|...|`, `(...)`, `~a`, `#`, `!`, `[...]`


