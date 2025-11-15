import argparse
import csv
import json
import os
import re
import xml.etree.ElementTree as ET

# Paths
DICT_DIR = 'data/dictionaries'
SUMERIAN_DICT = os.path.join(DICT_DIR, 'manual_sumerian_dict.txt')
ASSYRIAN_DICT = os.path.join(DICT_DIR, 'assyrian_dict.json')
EPSD_XML = os.path.join(DICT_DIR, 'epsd_data.xml')
PROTOCUNEIFORM_SIGNS = os.path.join(DICT_DIR, 'protocuneiform_signs.csv')
STATE_FILE = 'data/download_state.json'
CSV_PATH = 'data/cdli-gh-data/cdli_cat.csv'
ANNOTATIONS_DIR = 'data/annotations'

def load_dictionaries():
    sumerian_dict = {}
    assyrian_dict = {}
    protocuneiform_dict = {}

    # Load Sumerian dict (tab-separated)
    if os.path.exists(SUMERIAN_DICT):
        with open(SUMERIAN_DICT, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    sign, english = parts[0], parts[1]
                    sumerian_dict[sign] = english

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
                    elif m_code and phonetic:
                        protocuneiform_dict[m_code] = f"[{phonetic}]"
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

    return sumerian_dict, assyrian_dict, protocuneiform_dict

def extract_signs_from_atf(atf_text):
    # Extract signs: standard like GISZ, or proto-cuneiform like M365, M365#, M263~1, |M157+M288|
    signs = re.findall(r'\b(?:\|[^|]+\||[A-Z]+(?:\d+)?(?:~[^ #\n]+)?(?:#[^ \n]+)?)\b', atf_text)
    return signs

def translate_atf(atf_text, language='sumerian'):
    sumerian_dict, assyrian_dict, protocuneiform_dict = load_dictionaries()
    signs = extract_signs_from_atf(atf_text)
    translations = []

    print(f"Extracted signs: {signs[:20]}")  # Debug

    for sign in signs:
        # Normalize sign: remove suffixes like #, ~, etc. for lookup
        clean_sign = re.sub(r'[~#?].*', '', sign).strip('|')
        if '+' in clean_sign:
            # For compounds like |M157+M288|, split and translate each
            parts = clean_sign.split('+')
            part_translations = []
            for part in parts:
                if part in sumerian_dict:
                    part_translations.append(sumerian_dict[part])
                elif part.startswith('M') and part in protocuneiform_dict:
                    part_translations.append(protocuneiform_dict[part])
                else:
                    part_translations.append(f'[{part}]')
            translations.append('+'.join(part_translations))
            continue

        translated = False
        if language == 'sumerian':
            if clean_sign in sumerian_dict:
                translations.append(sumerian_dict[clean_sign])
                translated = True
            elif clean_sign.startswith('M') and clean_sign in protocuneiform_dict:
                translations.append(protocuneiform_dict[clean_sign])
                translated = True
        elif language == 'assyrian' and clean_sign in assyrian_dict:
            translations.append(assyrian_dict.get(clean_sign, {}).get('english', ''))
            translated = True

        if not translated:
            translations.append(f'[{sign}]')  # Unknown

    return ' '.join(translations)

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

    translation = translate_atf(atf_text, language)
    reading_direction = determine_reading_direction(atf_text, period)

    print(f"Artifact ID: {artifact_id}")
    print(f"ATF File: {atf_path}")
    print(f"Period: {period}")
    print(f"Reading Direction: {reading_direction}")
    print(f"Original ATF:\n{atf_text}\n")
    print(f"Attempted {language.title()} Translation:\n{translation}")

def main():
    parser = argparse.ArgumentParser(description='Translate ATF text or lookup by artifact ID')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('atf_file', nargs='?', help='Path to ATF file (legacy mode)')
    group.add_argument('--artifact_id', help='Artifact ID to lookup and translate')
    parser.add_argument('--language', choices=['sumerian', 'assyrian'], default='sumerian', help='Language for translation')
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
        print(f"Original ATF:\n{atf_text}\n")
        print(f"Attempted {args.language.title()} Translation:\n{translation}")

if __name__ == '__main__':
    main()
