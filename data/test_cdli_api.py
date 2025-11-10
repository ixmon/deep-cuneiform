import argparse
import requests
import time
from bs4 import BeautifulSoup  # For parsing search HTML if needed

def main():
    parser = argparse.ArgumentParser(description='Test CDLI API and downloads')
    parser.add_argument('--id', type=str, default='1', help='CDLI numeric artifact ID to fetch (e.g., 1 for P000001)')
    args = parser.parse_args()

    artifact_id = args.id  # Now numeric

    # Get artifact metadata (JSON) which includes ATF in inscription.atf
    meta_url = f'https://cdli.earth/artifacts/{artifact_id}'
    response = requests.get(meta_url, headers={'Accept': 'application/json'})
    if response.status_code == 200:
        try:
            metadata = response.json()[0]  # API returns array, take first item
            inscription = metadata.get('inscription', {})
            atf_text = inscription.get('atf', '')
            if atf_text:
                print(f"ATF for artifact {artifact_id}:\n{atf_text}")
            else:
                print("No ATF found in inscription.")
            # Get P-number for image download
            external_resources = metadata.get('external_resources', [])
            pnumber = None
            for res in external_resources:
                if res.get('external_resource_key', '').startswith('P'):
                    pnumber = res['external_resource_key']
                    break
            if not pnumber:
                pnumber = f"P{int(artifact_id):06d}"  # Fallback: assume P000001 for id 1, etc.
        except (IndexError, KeyError) as e:
            print(f"Error parsing metadata: {e}")
            pnumber = None
    else:
        print(f"Error fetching metadata: {response.status_code}")
        print(f"Response content: {response.text[:500]}...")  # Print first 500 chars for debug
        pnumber = None

    # Example 3: Check image using P-number
    if pnumber:
        img_url = f'https://cdli.ucla.edu/dl/photo/{pnumber}.jpg'
        response = requests.get(img_url)
        if response.status_code == 200:
            print(f"Image available for {pnumber}")
        else:
            print(f"Error fetching image: {response.status_code}")
    else:
        print("No P-number found for image download.")

    # Delay
    time.sleep(1)

if __name__ == '__main__':
    main()
