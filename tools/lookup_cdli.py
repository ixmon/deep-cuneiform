import argparse
import csv
import json
import os
import re
import requests
import xml.etree.ElementTree as ET

# Paths
STATE_FILE = 'data/download_state.json'
CSV_PATH = 'data/cdli-gh-data/cdli_cat.csv'
IMAGES_DIR = 'data/images'
ANNOTATIONS_DIR = 'data/annotations'
DICT_DIR = 'data/dictionaries'
SUMERIAN_DICT = os.path.join(DICT_DIR, 'manual_sumerian_dict.txt')
ASSYRIAN_DICT = os.path.join(DICT_DIR, 'assyrian_dict.json')
EPSD_XML = os.path.join(DICT_DIR, 'epsd_data.xml')
PROTOCUNEIFORM_SIGNS = os.path.join(DICT_DIR, 'protocuneiform_signs.csv')

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
            pass

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
            pass

    # Load Assyrian dict (JSON)
    if os.path.exists(ASSYRIAN_DICT):
        try:
            with open(ASSYRIAN_DICT, 'r') as f:
                assyrian_dict = json.load(f)
        except json.JSONDecodeError:
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

def get_english_translation(artifact_id):
    meta_url = f'https://cdli.earth/artifacts/{artifact_id}'
    try:
        response = requests.get(meta_url, headers={'Accept': 'application/json'}, timeout=10)
        if response.status_code == 200:
            metadata = response.json()[0]
            # Check for English translation in various possible fields
            english = ''
            designation = metadata.get('designation', '')
            if isinstance(designation, dict):
                english = designation.get('english', '')
            elif isinstance(designation, str):
                english = designation  # Often the designation is the English title

            if not english:
                english = metadata.get('translation', '') or metadata.get('inscription', {}).get('translation', '')

            return english or "No English translation available"
        else:
            return "Failed to fetch translation (API error)"
    except Exception as e:
        return f"Error fetching translation: {e}"

def lookup_artifact(artifact_id):
    # Load state
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
    else:
        state = {}

    # Get info from state
    if artifact_id in state:
        period = state[artifact_id].get('period', 'Unknown')
        quality_checked = state[artifact_id].get('quality_checked', False)
    else:
        print(f"Artifact ID {artifact_id} not found in state.json")
        return

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
        print(f"P-number not found for artifact ID {artifact_id} in CSV")
        return

    # Image path
    image_path = f"{IMAGES_DIR}/cdli_{pnumber}.jpg"

    # Annotation path and content
    ann_path = f"{ANNOTATIONS_DIR}/cdli_{pnumber}.atf"
    translation = "No annotation file found"
    if os.path.exists(ann_path):
        with open(ann_path, 'r', encoding='utf-8') as f:
            translation = f.read()

    # Get translations
    english_translation = get_english_translation(artifact_id)
    attempted_translation = translate_atf(translation, 'sumerian')

    # Print results
    print(f"Artifact ID: {artifact_id}")
    print(f"Image Path: {image_path}")
    print(f"Period: {period}")
    print(f"Quality Checked: {quality_checked}")
    print(f"Transliteration (ATF):\n{translation}")
    print(f"English Translation:\n{english_translation}")
    print(f"Attempted Sumerian Translation:\n{attempted_translation}")

def main():
    parser = argparse.ArgumentParser(description='Lookup CDLI artifact details by ID')
    parser.add_argument('artifact_id', type=str, help='The artifact ID to lookup')
    args = parser.parse_args()

    lookup_artifact(args.artifact_id)

if __name__ == '__main__':
    main()
