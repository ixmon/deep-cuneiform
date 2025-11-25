#!/usr/bin/env python3
"""
Convert the comprehensive Akkadian dictionary from SemanticDictionary
to our simple format for use in the translation system.
"""

import json
import os
import sys

def convert_akkadian_dictionary():
    """Convert the comprehensive Akkadian dictionary to our format."""

    input_file = 'data/dictionaries/akkadian.json'
    output_file = 'data/dictionaries/akkadian_converted.json'

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found")
        return

    print("Loading comprehensive Akkadian dictionary...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    entries = data['dictentries']['dictentry']
    print(f"Processing {len(entries)} entries...")

    # Our format: simple dictionary with ATF -> English mappings
    converted = {
        "simple": {},
        "compounds": {},
        "metadata": {
            "source": "SemanticDictionary (situx/SemanticDictionary)",
            "license": "GPLv3",
            "entries": len(entries),
            "converted_by": "convert_akkadian_dict.py"
        }
    }

    for entry in entries:
        translation_data = entry.get('translation', {})
        if isinstance(translation_data, list):
            translation = translation_data[0].get('content', '') if translation_data else ''
        else:
            translation = translation_data.get('content', '')
        if not translation:
            continue

        # Get all transliterations
        translits = entry.get('transliteration', [])
        if not isinstance(translits, list):
            continue

        for trans in translits:
            if not isinstance(trans, dict):
                continue

            transcription = trans.get('transcription', '')
            if not transcription:
                continue

            # Use the basic form without hyphens for lookup
            atf_key = transcription.replace('-', '')

            # Skip if already have this entry
            if atf_key in converted['simple']:
                continue

            converted['simple'][atf_key] = translation

            # Also add the hyphenated form
            if transcription != atf_key:
                converted['simple'][transcription] = translation

    print(f"Converted {len(converted['simple'])} simple entries")
    print(f"Sample entries: {dict(list(converted['simple'].items())[:10])}")

    # Save the converted dictionary
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(converted, f, ensure_ascii=False, indent=2)

    print(f"Saved converted dictionary to {output_file}")

    return converted

def test_conversion():
    """Test the conversion with some known terms."""
    convert_akkadian_dictionary()

    with open('data/dictionaries/akkadian_converted.json', 'r') as f:
        data = json.load(f)

    test_terms = ['abarakku', 'be', 'ina', 'nu', 'te', 'ana', 'sza']
    print("\nTesting conversion:")
    for term in test_terms:
        if term in data['simple']:
            print(f"{term} -> {data['simple'][term]}")
        else:
            print(f"{term} -> NOT FOUND")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_conversion()
    else:
        convert_akkadian_dictionary()
