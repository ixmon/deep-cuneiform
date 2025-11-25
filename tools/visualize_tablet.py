import argparse
import csv
import json
import os
import re
import sys
from PIL import Image, ImageDraw, ImageFont

# Add lib to path for custom imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from translators import detect_language

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
    """
    Render cuneiform line with color coding.
    Returns list of (glyph, is_known) tuples for per-character coloring.
    """
    glyph_info = []  # List of (glyph, is_known) tuples
    all_annotations = []
    for sign in signs:
        try:
            converted, ann = atf_to_cuneiform(sign)
            if converted and not converted.startswith('[') and converted != sign:
                # Check if this is a "pure" cuneiform glyph or a compound with unknowns
                # If it contains '[UNKNOWN:' it's not really a known glyph
                if '[UNKNOWN:' in converted:
                    # Compound with unknown parts - treat as unknown
                    glyph_info.append(('□', False))
                else:
                    # Pure cuneiform glyph
                    glyph_info.append((converted, True))
                    all_annotations.extend(ann)
            else:
                # Unknown - use placeholder square
                glyph_info.append(('□', False))
        except Exception as e:
            # Error - use placeholder
            glyph_info.append(('□', False))
    return glyph_info, all_annotations

def generate_translation_image(sections, translator, artifact_id, period, quality_checked, output_path):
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
                    cuneiform_info, annotations = render_cuneiform_line(signs, cuneiform_font)
                    atf_part = after.strip()
                    trans_line = translate_signs(signs, translator)
                else:
                    cuneiform_info, annotations = render_cuneiform_line(signs, cuneiform_font)
                    atf_part = atf_line
                    trans_line = translate_signs(signs, translator)
                # Determine color based on annotations
                base_color = 'red' if 'damaged' in annotations else 'white'
                # Store cuneiform_info (list of tuples) along with other data
                lines.append((line_num, cuneiform_info, atf_part, trans_line, base_color))
    # Calculate image size with better column layout
    # Use monospaced font for consistent alignment
    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("LiberationMono-Regular.ttf", font_size)
        except:
            pass  # Keep original font if monospaced not available

    char_width = font.getbbox('W')[2] - font.getbbox('W')[0]  # Use 'W' for wider character
    cuneiform_char_width = cuneiform_font.getbbox('𒀀')[2] - cuneiform_font.getbbox('𒀀')[0] if cuneiform_font != font else char_width

    # Define column widths in characters for better alignment
    line_num_width = 4  # "1. 2." (reduced)
    cuneiform_width = 24  # Space for cuneiform glyphs (doubled for wider column)
    atf_width = 25  # Space for ATF text
    trans_width = 20  # Space for translation

    total_char_width = line_num_width + cuneiform_width + atf_width + trans_width
    max_width = total_char_width * char_width + 100  # Extra padding
    height = len(lines) * (max(font_size, cuneiform_font_size) + 8) + 80
    
    # Draw directly on black background
    img = Image.new('RGB', (max_width, height), color='black')
    draw = ImageDraw.Draw(img)

    # Add header and ensure image is wide enough
    header = f"Artifact ID {artifact_id}    Period: {period}    Quality Checked: {quality_checked}"
    print(f"Drawing header: {header}")

    # Calculate header width to ensure image accommodates it
    header_bbox = font.getbbox(header)
    header_width = header_bbox[2] - header_bbox[0] if header_bbox else len(header) * char_width
    min_width = max(max_width, header_width + 60)  # More padding for safety

    # Recreate image if needed
    if min_width > max_width:
        max_width = min_width
        img = Image.new('RGB', (max_width, height), color='black')
        draw = ImageDraw.Draw(img)

    draw.text((10, 10), header, fill='white', font=font)
    y = 40  # Start below header

    for line_item in lines:
        # Check if this is a data line (5-tuple) or a header (string)
        if isinstance(line_item, tuple) and len(line_item) == 5:
            # Data line: (line_num, cuneiform_info, atf_part, trans_line, base_color)
            line_num, cuneiform_info, atf_part, trans_part, base_color = line_item

            print(f"Drawing data line: num='{line_num}', cuneiform_count={len(cuneiform_info)}, atf='{atf_part[:20]}...', trans='{trans_part[:15]}...' color={base_color}")

            x = 10  # Reduced left margin
            # Draw line number
            draw.text((x, y), f"{line_num:<{line_num_width-1}}", fill='cyan', font=font)
            x += (line_num_width - 1) * char_width  # Tighter spacing

            # Draw cuneiform with per-character coloring
            cuneiform_x = x
            if cuneiform_info:
                for glyph, is_known in cuneiform_info:
                    if is_known:
                        # Known glyph - use base color (white or red for damaged)
                        glyph_color = base_color
                    else:
                        # Unknown glyph - use dark gray
                        glyph_color = (64, 64, 64)
                    draw.text((cuneiform_x, y-14), glyph, fill=glyph_color, font=cuneiform_font)
                    # Advance x position by glyph width
                    glyph_bbox = cuneiform_font.getbbox(glyph)
                    glyph_width = glyph_bbox[2] - glyph_bbox[0] if glyph_bbox else 20
                    cuneiform_x += glyph_width
            else:
                # No cuneiform at all - draw subtle placeholder
                placeholder = "□□□"
                draw.text((cuneiform_x, y), placeholder, fill=(48, 48, 48), font=cuneiform_font)

            x += cuneiform_width * char_width
        elif isinstance(line_item, tuple) and len(line_item) == 2:
            # Old format: (line, color)
            line, color = line_item
            if line in ['OBVERSE', 'REVERSE'] or 'COLUMN' in line:
                print(f"Drawing section header: {line}")
                draw.text((10, y), line, fill='cyan', font=font)
            elif line.startswith('  ') and line.strip().isupper():
                print(f"Drawing column header: {line}")
                draw.text((10, y), line, fill='cyan', font=font)
            elif line.startswith('  @') or line.startswith('  $'):
                print(f"Drawing @/$ line: {line}")
                draw.text((10, y), line, fill='cyan', font=font)
            y += max(font_size, cuneiform_font_size) + 8
            continue
        else:
            # String header
            line = line_item
            color = 'cyan'
            if line in ['OBVERSE', 'REVERSE'] or 'COLUMN' in line:
                print(f"Drawing section header: {line}")
                draw.text((10, y), line, fill='cyan', font=font)
            elif line.startswith('  ') and line.strip().isupper():
                print(f"Drawing column header: {line}")
                draw.text((10, y), line, fill='cyan', font=font)
            elif line.startswith('  @') or line.startswith('  $'):
                print(f"Drawing @/$ line: {line}")
                draw.text((10, y), line, fill='cyan', font=font)
            y += max(font_size, cuneiform_font_size) + 8
            continue

        # Draw ATF (for data lines - 5-tuple)
        if isinstance(line_item, tuple) and len(line_item) == 5:
            if atf_part:
                # Truncate very long ATF lines
                if len(atf_part) > atf_width - 2:
                    atf_part = atf_part[:atf_width-3] + "…"
                draw.text((x, y), f"{atf_part:<{atf_width-1}}", fill='cyan', font=font)
            x += atf_width * char_width

            # Draw translation
            if trans_part and trans_part != '—':
                # Truncate very long translations
                if len(trans_part) > trans_width - 2:
                    trans_part = trans_part[:trans_width-3] + "…"
                draw.text((x, y), f"{trans_part:<{trans_width-1}}", fill='cyan', font=font)

        y += max(font_size, cuneiform_font_size) + 8

    img.save(output_path)
    print(f"Visualization saved to {output_path}")


def generate_stacked_image(sections, translator, artifact_id, period, quality_checked, output_path, image_width=800):
    """
    Generate a stacked layout visualization where each line has:
    1. Line number + Cuneiform (wrapping if needed)
    2. ATF text (indented, wrapping)
    3. English translation (indented, wrapping)
    """
    # Load fonts
    font_size = 14
    cuneiform_font_size = 28

    # Regular font for text
    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", font_size)
    except:
        try:
            font = ImageFont.truetype("LiberationMono-Regular.ttf", font_size)
        except:
            font = ImageFont.load_default()

    # Load cuneiform font
    cuneiform_font = font
    font_files = ['NotoSansCuneiform-Regular.ttf', 'Santakku.ttf', 'Assurbanipal.ttf', 'Ullikummi.ttf']
    for font_file in font_files:
        font_path = os.path.join(FONT_DIR, font_file)
        if os.path.exists(font_path):
            try:
                cuneiform_font = ImageFont.truetype(font_path, cuneiform_font_size)
                print(f"Loaded cuneiform font: {font_file} at size {cuneiform_font_size}")
                break
            except Exception as e:
                print(f"Failed to load {font_file}: {e}")

    # Calculate character widths
    char_width = font.getbbox('W')[2] - font.getbbox('W')[0]
    cuneiform_char_width = cuneiform_font.getbbox('𒀀')[2] - cuneiform_font.getbbox('𒀀')[0] if cuneiform_font != font else char_width

    # Margins and layout
    margin = 20
    indent = 30  # Indentation for ATF and translation lines
    usable_width = image_width - (2 * margin)
    line_spacing = 8
    block_spacing = 20  # Extra space between line blocks

    # First pass: calculate total height needed
    legend_height = 50  # Space for color legend
    y = 60 + legend_height  # Start below header and legend

    # Process sections to build line data
    line_blocks = []  # List of (line_num, cuneiform_info, atf_text, translation)

    for section, columns in sections.items():
        if section == 'main':
            continue
        # Add section header
        line_blocks.append(('header', section.upper(), None, None))

        for col, col_lines in columns.items():
            if col == 'main' and any(c.startswith('column_') for c in columns):
                continue
            if col != 'main':
                line_blocks.append(('header', f"  {col.replace('_', ' ').upper()}", None, None))

            for item in col_lines:
                try:
                    line_num, atf_line, signs = item
                except ValueError:
                    if isinstance(item, tuple) and len(item) == 2:
                        if item[0] == 'header':
                            line_blocks.append(('header', f"  {item[1]}", None, None))
                            continue
                        else:
                            line_num, signs = item
                            atf_line = ' '.join(signs)
                    else:
                        continue

                # Parse ATF
                if ',' in atf_line:
                    before, after = atf_line.split(',', 1)
                    signs = after.strip().split()
                    atf_text = after.strip()
                else:
                    # No comma - treat entire ATF line as signs to process
                    signs = atf_line.strip().split()
                    atf_text = atf_line

                cuneiform_info, annotations = render_cuneiform_line(signs, cuneiform_font)
                trans_text = translate_signs(signs, translator)
                base_color = 'red' if 'damaged' in annotations else 'white'

                line_blocks.append(('data', line_num, cuneiform_info, atf_text, trans_text, base_color))

    # Calculate height
    for block in line_blocks:
        if block[0] == 'header':
            y += font_size + line_spacing
        else:
            # Data block: cuneiform line + ATF line + translation line + spacing
            y += cuneiform_font_size + line_spacing  # Cuneiform
            y += font_size + line_spacing  # ATF
            y += font_size + line_spacing  # Translation
            y += block_spacing  # Extra spacing between blocks

    height = y + margin

    # Ensure minimum width for header
    header = f"Artifact ID {artifact_id}    Period: {period}    Quality Checked: {quality_checked}"
    header_bbox = font.getbbox(header)
    header_width = header_bbox[2] - header_bbox[0] if header_bbox else len(header) * char_width
    image_width = max(image_width, header_width + 2 * margin)

    # Create image
    img = Image.new('RGB', (image_width, height), color='black')
    draw = ImageDraw.Draw(img)

    # Draw header
    draw.text((margin, 12), header, fill='white', font=font)

    # Draw color legend
    legend_y = 35
    legend_items = [
        ("■ Line #", 'yellow'),
        ("■ Cuneiform", 'white'),
        ("■ Damaged", 'red'),
        ("■ Unknown", (64, 64, 64)),
        ("■ ATF", 'cyan'),
        ("■ English", (144, 238, 144)),
    ]
    legend_x = margin
    for label, color in legend_items:
        draw.text((legend_x, legend_y), label, fill=color, font=font)
        legend_x += len(label) * char_width + 15

    # Separator line
    draw.line([(margin, legend_y + font_size + 8), (image_width - margin, legend_y + font_size + 8)], fill=(60, 60, 60), width=1)

    y = legend_y + font_size + 20  # Start below legend

    # Draw blocks
    for block in line_blocks:
        if block[0] == 'header':
            _, header_text, _, _ = block
            draw.text((margin, y), header_text, fill='cyan', font=font)
            y += font_size + line_spacing
        else:
            _, line_num, cuneiform_info, atf_text, trans_text, base_color = block

            # Line 1: Line number + Cuneiform (on SAME row, same Y position)
            row_y = y  # Save the row's Y position
            x = margin

            # Draw line number at same Y as cuneiform (both start at row_y)
            line_label = f"{line_num}. " if line_num else ""
            draw.text((x, row_y), line_label, fill='yellow', font=font)
            x += len(line_label) * char_width + 5  # Small gap after line number

            # Draw cuneiform on SAME row as line number
            cuneiform_start_x = x

            # Calculate proper baseline alignment
            if cuneiform_font != font:
                line_bbox = font.getbbox('1')  # Sample for line number font
                cuneiform_bbox = cuneiform_font.getbbox('𒀀')  # Sample for cuneiform font

                # Calculate baseline alignment with refined positioning
                bottom_diff = line_bbox[3] - cuneiform_bbox[3]  # Font baseline differences
                baseline_offset = bottom_diff // 2 + 2  # Half offset + 2px upward nudge
                cuneiform_row_y = row_y + baseline_offset
            else:
                cuneiform_row_y = row_y
                print(f"Debug: Using same Y position")

            if cuneiform_info:
                cuneiform_x = cuneiform_start_x
                for glyph, is_known in cuneiform_info:
                    glyph_color = base_color if is_known else (64, 64, 64)
                    glyph_bbox = cuneiform_font.getbbox(glyph)
                    glyph_width = glyph_bbox[2] - glyph_bbox[0] if glyph_bbox else cuneiform_char_width

                    # Check if we need to wrap
                    if cuneiform_x + glyph_width > image_width - margin:
                        cuneiform_row_y += cuneiform_font_size + line_spacing
                        cuneiform_x = cuneiform_start_x

                    draw.text((cuneiform_x, cuneiform_row_y), glyph, fill=glyph_color, font=cuneiform_font)
                    cuneiform_x += glyph_width

                # Update y to be after the last cuneiform row
                y = cuneiform_row_y + cuneiform_font_size + line_spacing + 15  # Extra spacing
            else:
                # No cuneiform - just move past line number row
                y = row_y + cuneiform_font_size + line_spacing + 10

            # Line 2: ATF text (indented)
            if atf_text:
                x = margin + indent
                # Simple word wrapping for ATF
                words = atf_text.split()
                for word in words:
                    word_width = len(word) * char_width
                    if x + word_width > image_width - margin:
                        y += font_size + line_spacing
                        x = margin + indent
                    draw.text((x, y), word + " ", fill='cyan', font=font)
                    x += word_width + char_width
            y += font_size + line_spacing

            # Line 3: Translation (indented, different color)
            if trans_text and trans_text != '—':
                x = margin + indent
                # Simple word wrapping for translation
                words = trans_text.split()
                for word in words:
                    word_width = len(word) * char_width
                    if x + word_width > image_width - margin:
                        y += font_size + line_spacing
                        x = margin + indent
                    draw.text((x, y), word + " ", fill=(144, 238, 144), font=font)  # Light green
                    x += word_width + char_width
            y += font_size + line_spacing

            # Extra spacing between blocks
            y += block_spacing

    img.save(output_path)
    print(f"Stacked visualization saved to {output_path}")


def translate_signs(signs, translator):
    """Translate signs using the translator object. Clean version for visualization."""
    translations = []
    for sign in signs:
        translation, ann = translator.translate_sign(sign)
        if translation and not translation.startswith('[') and translation != '[UNKNOWN:' + sign + ']':
            # Only include successful translations, skip unknowns and damage markers
            if not any(marker in sign for marker in ['#', '?', '!', '*']):
                translations.append(translation)
    # Return joined translations, or a minimal indicator if none found
    return ' '.join(translations) if translations else '—'

def visualize_tablet(artifact_id, layout='stacked', image_width=800):
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

    # Get appropriate translator for this ATF text
    translator = detect_language(atf_text, period)

    output_path = f"data/visualizations/{artifact_id}_tablet.png"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if layout == 'stacked':
        generate_stacked_image(sections, translator, artifact_id, period, quality_checked, output_path, image_width)
    else:
        generate_translation_image(sections, translator, artifact_id, period, quality_checked, output_path)

def main():
    parser = argparse.ArgumentParser(description='Visualize tablet with ATF and translations')
    parser.add_argument('artifact_id', help='Artifact ID')
    parser.add_argument('--layout', choices=['columns', 'stacked'], default='stacked',
                        help='Layout style: "columns" for 3-column layout, "stacked" for single-column with wrapped lines (default: stacked)')
    parser.add_argument('--width', type=int, default=800,
                        help='Image width in pixels (default: 800)')
    args = parser.parse_args()

    visualize_tablet(args.artifact_id, layout=args.layout, image_width=args.width)

if __name__ == '__main__':
    main()
