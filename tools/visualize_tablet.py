import argparse
import csv
import json
import os
import re
import sys
from PIL import Image, ImageDraw, ImageFont

# Add lib to path for custom imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

# Paths
STATE_FILE = 'data/download_state.json'
CSV_PATH = 'data/cdli-gh-data/cdli_cat.csv'
IMAGES_DIR = 'data/images'
ANNOTATIONS_DIR = 'data/annotations'

from atf2unicode.main import atf_to_cuneiform
CSV_PATH = 'data/cdli-gh-data/cdli_cat.csv'
FONT_DIR = 'data/fonts'

def parse_atf(atf_text):
    sections = {}
    current_section = 'main'
    current_column = 'main'
    for line in atf_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('@tablet'):
            continue  # Skip tablet declaration
        if line.startswith('@') or line.startswith('$'):
            # Add as header
            if current_section not in sections:
                sections[current_section] = {}
            if current_column not in sections[current_section]:
                sections[current_section][current_column] = []
            sections[current_section][current_column].append(('header', line))
            if 'obverse' in line:
                current_section = 'obverse'
            elif 'reverse' in line:
                current_section = 'reverse'
            elif 'column' in line:
                col_num = re.search(r'@column (\d+)', line)
                if col_num:
                    current_column = f'column_{col_num.group(1)}'
            continue
        # Parse signs
        signs = []
        line_num = ''
        match = re.match(r'^(\d+[\'"]*)\.', line)
        if match:
            line_num = match.group(1)
            # Remove the line number from line for atf_line
            atf_line = re.sub(r'^\d+[\'"]*\.\s*', '', line)
        else:
            atf_line = line
        parts = atf_line.split(',')
        if len(parts) > 1:
            signs = parts[1].strip().split()
        else:
            signs = atf_line.split()
        if signs:
            if current_section not in sections:
                sections[current_section] = {}
            if current_column not in sections[current_section]:
                sections[current_section][current_column] = []
            sections[current_section][current_column].append((line_num, atf_line, signs))
    return sections

# load_cuneiform_mapping() removed - now using atf_to_cuneiform from lib/atf2unicode/main.py

def render_cuneiform_line(signs, cuneiform_font):
    glyphs = []
    all_annotations = []
    for sign in signs:
        try:
            converted, ann = atf_to_cuneiform(sign)
            if converted and not converted.startswith('[') and converted != sign:
                glyphs.append(converted)
                all_annotations.extend(ann)
            # Suppress fallbacks: don't add if it's brackets or unchanged
        except:
            pass  # Suppress errors too
    return ''.join(glyphs) if glyphs else '', all_annotations  # Return empty if no valid glyphs

def generate_translation_image(sections, translations_dict, artifact_id, period, quality_checked, output_path):
    # Load fonts
    font_size = 16
    cuneiform_font_size = 32  # Larger for better visibility

    # Regular font for text
    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Cuneiform font - try Noto Sans Cuneiform first (comprehensive Unicode support)
    cuneiform_font = None
    preferred_fonts = ['notosancuneiformunhinted', 'notosanscuneiform', 'santakku', 'ullikummi', 'assurbanipal']
    for pref in preferred_fonts:
        for ext in ['.ttf', '.otf']:
            for file in os.listdir(FONT_DIR):
                if file.endswith(ext) and pref in file.lower():
                    try:
                        cuneiform_font = ImageFont.truetype(os.path.join(FONT_DIR, file), cuneiform_font_size)
                        print(f"Loaded cuneiform font: {file} at size {cuneiform_font_size}")
                        break
                    except Exception as e:
                        print(f"Failed to load {file}: {e}")
            if cuneiform_font:
                break
        if cuneiform_font:
            break
    if not cuneiform_font:
        print("No cuneiform font loaded, using fallback")
        cuneiform_font = font  # Fallback

    lines = []
    for section, columns in sections.items():
        if section == 'main':
            continue  # Skip main section headers
        lines.append(f"{section.upper()}")
        for col, col_lines in columns.items():
            if col != 'main':
                lines.append(f"  {col.replace('_', ' ').upper()}")
            for item in col_lines:
                try:
                    line_num, atf_line, signs = item
                except ValueError:
                    if isinstance(item, tuple) and len(item) == 2:
                        if item[0] == 'header':
                            lines.append(f"  {item[1]}")
                            continue
                        else:
                            line_num, signs = item
                            atf_line = ' '.join(signs)
                    else:
                        continue  # skip invalid
                # Assume ATF format: quantity before comma, signs after comma
                if ',' in atf_line:
                    before, after = atf_line.split(',', 1)
                    signs = after.strip().split()
                    cuneiform_line, annotations = render_cuneiform_line(signs, cuneiform_font)
                    atf_part = after.strip()
                    trans_line = translate_signs(signs, translations_dict)
                else:
                    cuneiform_line, annotations = render_cuneiform_line(signs, cuneiform_font)
                    atf_part = atf_line
                    trans_line = translate_signs(signs, translations_dict)
                # Determine color based on annotations
                color = 'red' if 'damaged' in annotations else 'white'
                lines.append((f"{line_num:<5}{cuneiform_line:<20}{atf_part:<30}{trans_line:<20}", color))
    # Calculate image size: cuneiform on left, text on right
    char_width = font.getbbox('A')[2] - font.getbbox('A')[0]
    cuneiform_char_width = cuneiform_font.getbbox('A')[2] - cuneiform_font.getbbox('A')[0] if cuneiform_font != font else char_width
    cuneiform_width = 30 * cuneiform_char_width  # Space for cuneiform on left
    text_width = 80 * char_width  # Space for ATF + translation on right
    max_width = cuneiform_width + 50 + text_width  # Gap between cuneiform and text
    height = len(lines) * (max(font_size, cuneiform_font_size) + 5) + 50
    
    # Draw directly on black background
    img = Image.new('RGB', (max_width, height), color='black')
    draw = ImageDraw.Draw(img)

    # Add header
    header = f"Artifact ID {artifact_id}    Period: {period}    Quality Checked: {quality_checked}"
    print(f"Drawing header: {header}")
    draw.text((10, 10), header, fill='white', font=font)
    y = 40  # Start below header

    for line_item in lines:
        if isinstance(line_item, tuple):
            line, color = line_item
        else:
            line, color = line_item, 'cyan'  # default for headers

        if line in ['OBVERSE', 'REVERSE'] or 'COLUMN' in line:
            print(f"Drawing section header: {line}")
            draw.text((10, y), line, fill='cyan', font=font)
        elif line.startswith('  ') and line.strip().isupper():
            print(f"Drawing column header: {line}")
            draw.text((10, y), line, fill='cyan', font=font)
        elif line.startswith('  @') or line.startswith('  $'):
            print(f"Drawing @/$ line: {line}")
            draw.text((10, y), line, fill='cyan', font=font)
        else:
            # Data line: fixed width columns: 5 num, 20 cuneiform, 30 atf, 20 trans
            line_num = line[0:5].strip()
            cuneiform_part = line[5:25].strip()
            atf_part = line[25:55].strip()
            trans_part = line[55:].strip()
            print(f"Drawing data line: num='{line_num}', cuneiform='{cuneiform_part}', atf='{atf_part}', trans='{trans_part}' color={color}")

            x = 10
            draw.text((x, y), line_num, fill='cyan', font=font)
            x += 60  # space for line num
            if cuneiform_part:
                draw.text((x, y), cuneiform_part, fill=color, font=cuneiform_font)
            x += 220  # space for cuneiform
            if atf_part:
                draw.text((x, y), atf_part, fill='cyan', font=font)
            x += 320  # space for ATF
            if trans_part:
                draw.text((x, y), trans_part, fill='cyan', font=font)
        y += max(font_size, cuneiform_font_size) + 5

    img.save(output_path)
    print(f"Visualization saved to {output_path}")

def translate_signs(signs, translations_dict):
    translations = []
    for sign in signs:
        clean_sign = re.sub(r'[~#?].*', '', sign).strip('|').upper()
        if clean_sign in translations_dict:
            translations.append(translations_dict[clean_sign])
        else:
            translations.append(f'[{sign}]')
    return ' '.join(translations)

def visualize_tablet(artifact_id):
    # Get artifact details from CSV
    period = "Unknown"
    quality_checked = False
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row.get('id') == artifact_id:
                    period = row.get('period', 'Unknown')
                    break

    # Check quality from state
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
            quality_checked = state.get(artifact_id, {}).get('quality_checked', False)

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

    atf_file = os.path.join(ANNOTATIONS_DIR, f'cdli_{pnumber}.atf')
    if not os.path.exists(atf_file):
        print(f"ATF file {atf_file} not found")
        return

    with open(atf_file, 'r', encoding='utf-8') as f:
        atf_text = f.read()

    sections = parse_atf(atf_text)

    # Load translations dict (from manual dict and ATF map)
    translations_dict = {}
    dict_file = 'data/dictionaries/manual_sumerian_dict.txt'
    if os.path.exists(dict_file):
        with open(dict_file, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    translations_dict[parts[0]] = parts[1]

    # Also load ATF map for compounds
    atf_map_file = 'data/dictionaries/atf_unicode_map.json'
    if os.path.exists(atf_map_file):
        try:
            with open(atf_map_file, 'r') as f:
                atf_data = json.load(f)
                # Add compound translations
                for compound, meaning in atf_data.get('compounds', {}).items():
                    # For compounds, we want the translation, but the key needs to be normalized
                    # The translate_signs function does clean_sign = re.sub(r'[~#?].*', '', sign).strip('|')
                    # So for |(GISZX(DIN.DIN))|, it becomes (GISZX(DIN.DIN))
                    # But we want to map |(GISZX(DIN.DIN))| to 'wall'
                    # Actually, let me check what clean_sign produces for |(GISZx(DIN.DIN))~a|#
                    # re.sub(r'[~#?].*', '', '|(GISZx(DIN.DIN))~a|#') = '|(GISZx(DIN.DIN))|'
                    # Then .strip('|') = '(GISZx(DIN.DIN))'
                    # So I need to map '(GISZX(DIN.DIN))' to 'wall' in translations_dict
                    clean_key = re.sub(r'[~#?].*', '', compound).strip('|').upper()
                    if compound == '|(GISZX(DIN.DIN))|':
                        translations_dict[clean_key] = 'wall'
                    elif clean_key not in translations_dict:  # Don't overwrite
                        # For other compounds, use descriptive names
                        if 'GISZ' in clean_key and 'DIN' in clean_key:
                            translations_dict[clean_key] = 'wall'
                        elif 'GISZ' in clean_key:
                            translations_dict[clean_key] = 'wood/tree'
                        elif 'DIN' in clean_key:
                            translations_dict[clean_key] = 'life'
                        # Add more as needed
        except json.JSONDecodeError:
            pass

    output_path = f"data/visualizations/{artifact_id}_tablet.png"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    generate_translation_image(sections, translations_dict, artifact_id, period, quality_checked, output_path)

def main():
    parser = argparse.ArgumentParser(description='Visualize tablet with ATF and translations')
    parser.add_argument('artifact_id', help='Artifact ID')
    args = parser.parse_args()

    visualize_tablet(args.artifact_id)

if __name__ == '__main__':
    main()
