import argparse
import csv
import json
import os
import requests
import time

# Create directories
os.makedirs('data/images', exist_ok=True)
os.makedirs('data/annotations', exist_ok=True)

# Configuration
TARGET_PERIODS = [
    "Early Dynastic", "ED I", "ED II", "ED III", "Akkadian", "Lagash II",
    "Ur III", "Old Babylonian", "Isin-Larsa"
]
TARGET_LANGUAGE = "Sumerian"  # Or "Akkadian"
MIN_ATF_LENGTH = 100  # Minimum ATF length for quality
STATE_FILE = 'data/download_state.json'  # For resumable downloads

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def is_good_quality(atf_text, img_path):
    # Basic quality checks: ATF long enough, image exists and not tiny
    if len(atf_text) < MIN_ATF_LENGTH:
        return False
    if not os.path.exists(img_path):
        return False
    img_size = os.path.getsize(img_path)
    if img_size < 50000:  # Arbitrary threshold for image size
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description='Download filtered CDLI images and annotations with resumable state')
    parser.add_argument('--limit', type=int, default=None, help='Limit to N items')
    parser.add_argument('--resume', action='store_true', help='Resume from saved state')
    args = parser.parse_args()

    # Load or initialize state
    state = load_state() if args.resume else {}

    csv_path = 'data/cdli-gh-data/cdli_cat.csv'
    if not os.path.exists(csv_path):
        print(f'Error: {csv_path} not found. Please clone cdli-gh-data repo.')
        return

    processed = 0
    downloaded_good = 0

    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader):
            if args.limit is not None and processed >= args.limit:
                break

            numeric_id = row.get('id', '')
            if numeric_id in state and state[numeric_id].get('downloaded', False):
                print(f'Skipping already processed artifact {numeric_id}')
                continue

            # Filter by period, language, and availability
            period = row.get('period', '')
            language = row.get('language', '')
            photo_up = row.get('photo_up', '').strip()
            atf_up = row.get('atf_up', '').strip()
            if (not any(p in period for p in TARGET_PERIODS) or
                language != TARGET_LANGUAGE or
                not photo_up or
                not atf_up):
                continue

            print(f'\nProcessing Row {i+1} (ID: {numeric_id}, Period: {period})')
            processed += 1

            # Initialize state for this ID
            if numeric_id not in state:
                state[numeric_id] = {'period': period, 'downloaded': False, 'quality_checked': False}

            # Construct P-number
            pnumber_raw = row.get('id_text')
            if not pnumber_raw:
                continue
            try:
                pnumber = f"P{int(pnumber_raw):06d}"
            except ValueError:
                pnumber = pnumber_raw

            img_path = f'data/images/cdli_{pnumber}.jpg'
            ann_path = f'data/annotations/cdli_{pnumber}.atf'

            # Fetch ATF first (always try, even if image fails)
            atf_text = ''
            if not os.path.exists(ann_path):
                meta_url = f'https://cdli.earth/artifacts/{numeric_id}'
                try:
                    response = requests.get(meta_url, headers={'Accept': 'application/json'}, timeout=10)
                    if response.status_code == 200:
                        metadata = response.json()[0]
                        inscription = metadata.get('inscription', {})
                        atf_text = inscription.get('atf', '')
                        if atf_text:
                            with open(ann_path, 'w', encoding='utf-8') as f:
                                f.write(atf_text)
                            print(f'  Fetched and saved ATF to {ann_path}')
                        else:
                            print('  No ATF available.')
                            # Continue to next if no ATF
                            continue
                    else:
                        print(f'  API failed: {response.status_code}')
                        continue
                except Exception as e:
                    print(f'  Error fetching ATF: {e}')
                    continue

            # Download image if not exists (optional, even if ATF succeeded)
            if not os.path.exists(img_path):
                img_url = f'https://cdli.ucla.edu/dl/photo/{pnumber}.jpg'
                try:
                    response = requests.get(img_url, timeout=10)
                    if response.status_code == 200:
                        with open(img_path, 'wb') as f:
                            f.write(response.content)
                        print(f'  Downloaded image to {img_path}')
                    else:
                        print(f'  Failed to download image: {response.status_code} (continuing without image)')
                except Exception as e:
                    print(f'  Error downloading image: {e} (continuing without image)')

            # Quality check
            if is_good_quality(atf_text, img_path):
                state[numeric_id]['downloaded'] = True
                state[numeric_id]['quality_checked'] = True
                downloaded_good += 1
                print(f'  Quality check passed for {numeric_id}')
            else:
                print(f'  Quality check failed for {numeric_id} - removing files')
                if os.path.exists(img_path):
                    os.remove(img_path)
                if os.path.exists(ann_path):
                    os.remove(ann_path)
                state[numeric_id]['downloaded'] = False

            # Save state periodically
            if processed % 10 == 0:
                save_state(state)
                print(f'Saved state after {processed} processed items')

            # Rate limit
            time.sleep(1)

    save_state(state)
    print(f'\nCompleted. Processed: {processed}, Good downloads: {downloaded_good}')

if __name__ == '__main__':
    main()
