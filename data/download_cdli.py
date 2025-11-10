import argparse
import csv
import os
import requests

# Create directories
os.makedirs('data/images', exist_ok=True)
os.makedirs('data/annotations', exist_ok=True)

def main():
    parser = argparse.ArgumentParser(description='Download CDLI images and annotations from cdli_cat.csv')
    parser.add_argument('--limit', type=int, default=None, help='Limit to first N rows for testing')
    args = parser.parse_args()

    csv_path = 'data/cdli-gh-data/cdli_cat.csv'
    if not os.path.exists(csv_path):
        print(f'Error: {csv_path} not found')
        return

    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader):
            if args.limit is not None and i >= args.limit:
                break

            # Print fields nicely
            print(f'\nRow {i+1}:')
            for key, value in row.items():
                print(f'  {key}: {value}')

            # Download image
            pnumber_raw = row.get('id_text')
            if pnumber_raw:
                # Construct P-number: assume id_text is numeric, format as PXXXXXX
                try:
                    pnumber = f"P{int(pnumber_raw):06d}"
                except ValueError:
                    pnumber = pnumber_raw  # Fallback if not numeric
                img_url = f'https://cdli.ucla.edu/dl/photo/{pnumber}.jpg'
                img_path = f'data/images/cdli_{pnumber}.jpg'
                try:
                    response = requests.get(img_url)
                    if response.status_code == 200:
                        with open(img_path, 'wb') as f:
                            f.write(response.content)
                        print(f'  Downloaded image to {img_path}')
                    else:
                        print(f'  Failed to download image: {response.status_code}')
                except Exception as e:
                    print(f'  Error downloading image: {e}')

            # Get numeric ID from CSV (assume 'id' field exists)
            numeric_id = row.get('id')
            if numeric_id:
                # Fetch ATF via API using numeric ID
                meta_url = f'https://cdli.earth/artifacts/{numeric_id}'
                response = requests.get(meta_url, headers={'Accept': 'application/json'})
                if response.status_code == 200:
                    try:
                        metadata = response.json()[0]
                        inscription = metadata.get('inscription', {})
                        atf_text = inscription.get('atf', '')
                        if atf_text:
                            ann_path = f'data/annotations/cdli_{pnumber}.atf'
                            with open(ann_path, 'w', encoding='utf-8') as f:
                                f.write(atf_text)
                            print(f'  Fetched and saved ATF via API to {ann_path}')
                        else:
                            print('  No ATF in inscription.')
                    except (IndexError, KeyError) as e:
                        print(f'  Error parsing API response: {e}')
                else:
                    print(f'  API failed: {response.status_code}')
            else:
                print('  No numeric ID in CSV for API fetch.')

    print(f'\nProcessed {i+1} rows')

if __name__ == '__main__':
    main()
