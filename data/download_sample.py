import os
import requests
from datasets import load_dataset
from huggingface_hub import snapshot_download

# Create directories
os.makedirs('data/images', exist_ok=True)
os.makedirs('data/annotations', exist_ok=True)

# Focus on HeiCuBeDa Zenodo download
# HeiCuBeDa is at https://zenodo.org/record/4575680
zenodo_url = 'https://zenodo.org/api/records/4575680/files'  # Confirmed API endpoint for HeiCuBeDa

response = requests.get(zenodo_url)
if response.status_code != 200:
    print(f'Error fetching Zenodo files: {response.status_code}')
    exit(1)

files = response.json()['files'][:100]  # Subsample 100 (HeiCuBeDa has ~100 tablets)

downloaded = 0
for j, file in enumerate(files):
    key = file['key'].lower()
    if '.png' in key:  # HeiCuBeDa has PNG photos
        img_url = file['links']['self']
        img_path = f'data/images/heicubeda_{j}.png'  # Note: PNG, adjust if needed
        with open(img_path, 'wb') as f:
            f.write(requests.get(img_url).content)
        
        # Find paired annotation (HeiCuBeDa uses XML for annotations)
        ann_key = key.replace('.png', '.xml')  # Assuming XML annotations
        ann_file = next((f for f in files if f['key'].lower() == ann_key), None)
        if ann_file:
            ann_url = ann_file['links']['self']
            ann_path = f'data/annotations/heicubeda_{j}.atf'  # Save as .atf, but it's XML; need conversion
            ann_content = requests.get(ann_url).text
            with open(ann_path, 'w') as f:
                f.write(ann_content)  # For now, save raw XML; TODO: parse to ATF
            print(f'Downloaded image and annotation for {key}')
            downloaded += 1
        if downloaded >= 100:
            break

print(f'Downloaded {downloaded} samples from HeiCuBeDa to data/')

# Note: HeiCuBeDa annotations are in XML format. For ATF, you'll need to add parsing logic (e.g., extract transliterations from XML).
# For ElectronicBabylonianLiterature, data is on GitHub: https://github.com/ElectronicBabylonianLiterature/ebl-cuneiform-data
# Consider adding a section to clone and sample from there.
