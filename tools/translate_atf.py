import argparse
import csv
import json
import os
import re
import sys

# Add lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from atf2unicode.main import atf_to_cuneiform
from translators import detect_language

# Paths
STATE_FILE = 'data/download_state.json'
CSV_PATH = 'data/cdli-gh-data/cdli_cat.csv'
ANNOTATIONS_DIR = 'data/annotations'

def load_dictionaries():
    sumerian_dict = {}
    assyrian_dict = {}
    protocuneiform_dict = {}

    # Load ATF map for compounds and complex signs
    atf_map = {}
    if os.path.exists(ATF_MAP):
        try:
            with open(ATF_MAP, 'r') as f:
                data = json.load(f)
                # Create translation mappings from ATF signs to English meanings
                # For now, we'll use placeholder meanings for compounds
                # In a real implementation, you'd have a separate translation dict
                for sign in data.get('simple', {}):
                    # Simple signs: try to get meaning from manual dict or use sign name
                    pass  # Will be handled below
                for compound, unicode_val in data.get('compounds', {}).items():
                    # For compounds, add known meanings
                    if compound == '|(GISZX(DIN.DIN))|':
                        atf_map[compound] = 'wall'
                    elif compound == '|GISZ.DIN|':
                        atf_map[compound] = 'tree-life'
                    elif compound == '|GISZXDIN|':
                        atf_map[compound] = 'tree-life'
                    elif compound == '|LAGAB+LAGAB|':
                        atf_map[compound] = 'brick'
                    elif compound == '|DU.DU|':
                        atf_map[compound] = 'du-du'
                    elif 'LAGAB' in compound:
                        atf_map[compound] = 'block'
                    else:
                        # General patterns only for unknown compounds
                        if 'GISZ' in compound and 'DIN' in compound:
                            atf_map[compound] = 'wall'
                        elif 'GISZ' in compound:
                            atf_map[compound] = 'wood/tree'
                        elif 'DIN' in compound:
                            atf_map[compound] = 'life'
                        else:
                            atf_map[compound] = f'compound-sign'
        except json.JSONDecodeError:
            print("Warning: ATF map JSON is invalid.")

    # Load Sumerian dict (tab-separated)
    if os.path.exists(SUMERIAN_DICT):
        with open(SUMERIAN_DICT, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    sign, english = parts[0], parts[1]
                    sumerian_dict[sign] = english
                    # Also add to compounds if it's a compound sign
                    atf_map[sign] = english

    # Load ePSD XML for Sumerian (if available)
    if os.path.exists(EPSD_XML):
        try:
            tree = ET.parse(EPSD_XML)
            root = tree.getroot()
            for entry in root.findall('.//entry'):
                cf = entry.find('cf')
                if cf is not None:
                    sign = cf.text
                    meanings = []
                    for sense in entry.findall('.//sense'):
                        def_elem = sense.find('def')
                        if def_elem is not None:
                            meanings.append(def_elem.text)
                    if meanings:
                        sumerian_dict[sign] = '; '.join(meanings)
                        atf_map[sign] = '; '.join(meanings)
        except ET.ParseError:
            print("Warning: Failed to parse ePSD XML.")

    # Load Proto-cuneiform signs (CSV)
    if os.path.exists(PROTOCUNEIFORM_SIGNS):
        try:
            with open(PROTOCUNEIFORM_SIGNS, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    m_code = row.get('sign', '').strip()
                    english = row.get('english', '').strip() or row.get('meaning', '').strip()
                    phonetic = row.get('phonetic', '').strip()
                    if m_code and english:
                        protocuneiform_dict[m_code] = english
                        atf_map[m_code] = english
                    elif m_code and phonetic:
                        protocuneiform_dict[m_code] = f"[{phonetic}]"
                        atf_map[m_code] = f"[{phonetic}]"
        except Exception as e:
            print(f"Warning: Failed to load proto-cuneiform signs: {e}")

    # Load Assyrian dict (JSON)
    if os.path.exists(ASSYRIAN_DICT):
        try:
            with open(ASSYRIAN_DICT, 'r') as f:
                assyrian_dict = json.load(f)
        except json.JSONDecodeError:
            print("Warning: Assyrian dictionary JSON is invalid or empty.")
            assyrian_dict = {}

    return sumerian_dict, assyrian_dict, protocuneiform_dict, atf_map

def extract_signs_from_atf_line(line):
    """Extract individual signs from a single ATF line."""
    # Remove line numbers and other metadata
    line = re.sub(r'^\d+[\'"]*\.', '', line.strip())
    if not line:
        return []

    signs = []
    # Split by comma to get the transliteration part
    if ',' in line:
        parts = line.split(',')
        if len(parts) >= 2:
            transliteration = parts[1].strip()
            # Split by spaces and extract potential signs
            candidates = re.split(r'\s+', transliteration)
            for candidate in candidates:
                candidate = candidate.strip()
                if candidate and not candidate.startswith('>>') and candidate != '[...]':
                    # Check if it's a valid ATF sign by trying to parse it
                    try:
                        glyph, ann = atf_to_cuneiform(candidate)
                        if glyph and not glyph.startswith('['):
                            signs.append(candidate)
                    except:
                        pass

    return signs

def translate_atf(atf_text, language='auto', period=''):
    """
    Translate ATF text using appropriate translator based on language detection.

    Args:
        atf_text (str): The ATF text to translate
        language (str): Language override ('sumerian', 'akkadian', or 'auto' for detection)
        period (str): Period information for language detection

    Returns:
        str: English translation
    """
    if language == 'auto':
        translator = detect_language(atf_text, period)
    elif language == 'sumerian':
        from translators import SumerianTranslator
        translator = SumerianTranslator()
    elif language == 'akkadian':
        from translators import AkkadianTranslator
        translator = AkkadianTranslator()
    else:
        # Default to Sumerian
        from translators import SumerianTranslator
        translator = SumerianTranslator()

    return translator.translate_atf(atf_text)

def determine_reading_direction(atf_text, period):
    # Basic heuristic: If @column is present, likely columnar (top to bottom per column, left to right across)
    # Otherwise, assume row-based (left to right, top to bottom)
    if '@column' in atf_text:
        return "Columnar: Read top to bottom within each column, then left to right across columns"
    else:
        return "Row-based: Read left to right, top to bottom"

def lookup_and_translate(artifact_id, language='sumerian'):
    # Load state
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)

    if artifact_id not in state:
        print(f"Artifact ID {artifact_id} not found in state.")
        return

    period = state[artifact_id].get('period', 'Unknown')

    # Find pnumber from CSV
    pnumber = None
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row.get('id') == artifact_id:
                    pnumber_raw = row.get('id_text')
                    if pnumber_raw:
                        try:
                            pnumber = f"P{int(pnumber_raw):06d}"
                        except ValueError:
                            pnumber = pnumber_raw
                    break

    if not pnumber:
        print(f"P-number not found for {artifact_id}")
        return

    atf_path = os.path.join(ANNOTATIONS_DIR, f'cdli_{pnumber}.atf')
    if not os.path.exists(atf_path):
        print(f"ATF file not found: {atf_path}")
        return

    with open(atf_path, 'r', encoding='utf-8') as f:
        atf_text = f.read()

    translation = translate_atf(atf_text, language, period)
    reading_direction = determine_reading_direction(atf_text, period)

    # Detect the actual language used for translation
    translator = detect_language(atf_text, period)
    language_name = translator.get_language_name()

    print(f"Artifact ID: {artifact_id}")
    print(f"ATF File: {atf_path}")
    print(f"Period: {period}")
    print(f"Reading Direction: {reading_direction}")
    print(f"Detected Language: {language_name}")
    print(f"Original ATF:\n{atf_text}\n")
    print(f"Attempted {language_name} Translation:\n{translation}")

def main():
    parser = argparse.ArgumentParser(description='Translate ATF text or lookup by artifact ID')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('atf_file', nargs='?', help='Path to ATF file (legacy mode)')
    group.add_argument('--artifact_id', help='Artifact ID to lookup and translate')
    parser.add_argument('--language', choices=['auto', 'sumerian', 'akkadian'], default='auto', help='Language for translation (auto-detects from ATF)')
    args = parser.parse_args()

    if args.artifact_id:
        lookup_and_translate(args.artifact_id, args.language)
    else:
        # Legacy mode
        if not os.path.exists(args.atf_file):
            print(f"ATF file not found: {args.atf_file}")
            return

        with open(args.atf_file, 'r', encoding='utf-8') as f:
            atf_text = f.read()

        translation = translate_atf(atf_text, args.language)
        translator = detect_language(atf_text, '')
        language_name = translator.get_language_name()
        print(f"Original ATF:\n{atf_text}\n")
        print(f"Attempted {language_name} Translation:\n{translation}")

if __name__ == '__main__':
    main()
