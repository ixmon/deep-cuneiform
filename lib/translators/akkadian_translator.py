"""
Akkadian ATF translator with specialized medical dictionaries.
"""

import os
import json
import re

class AkkadianTranslator:
    """Translator for Akkadian ATF texts with specialized medical dictionaries."""

    def __init__(self, dict_path=None):
        # Initialize with empty dictionaries - we'll load specialized ones
        self.specialized_dicts = {}
        self._load_specialized_dictionaries()

        # Initialize base translator attributes we need
        self.simple_signs = {}
        self.compound_signs = {}
        self.variant_signs = {}
        self.annotations = {}

    def _load_specialized_dictionaries(self):
        """Load specialized dictionaries in priority order."""
        base_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'dictionaries')

        # Priority order: most specific to most general
        dict_files = [
            'clauses/stock_medical_clauses.json',      # Most specific - stock clauses
            'medical/medical_compound_phrases.json',   # Critical for medical texts
            'plants/plants_and_minerals.json',         # Plants and minerals
            'ritual/ritual_terms.json',                # Ritual terms
            'akkadian_words.json',                     # Normal Akkadian vocabulary
            'sumerian_logograms.json',                 # Sumerian logograms (rarely needed)
        ]

        for dict_file in dict_files:
            full_path = os.path.join(base_path, dict_file)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Extract the actual dictionary content
                        dict_name = list(data.keys())[0]  # e.g., 'medical_compounds'
                        self.specialized_dicts[dict_name] = data[dict_name]
                        print(f"Loaded specialized dictionary: {dict_file} ({len(data[dict_name])} entries)")
                except Exception as e:
                    print(f"Failed to load {dict_file}: {e}")

        # Also try to load the comprehensive dictionary as fallback
        comprehensive_path = os.path.join(base_path, 'akkadian_converted.json')
        if os.path.exists(comprehensive_path):
            try:
                with open(comprehensive_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.specialized_dicts['comprehensive_fallback'] = data.get('simple', {})
                    print(f"Loaded comprehensive fallback dictionary ({len(data.get('simple', {}))} entries)")
            except Exception as e:
                print(f"Failed to load comprehensive dictionary: {e}")

    def get_language_name(self):
        return "Akkadian"

    def clean_sign(self, sign):
        """Clean sign by removing ATF markers and normalizing case."""
        # Remove damage/uncertainty markers
        clean = re.sub(r'[~#?\d].*', '', sign).strip('|').strip('_').upper()
        return clean

    def translate_sign(self, sign):
        """Translate an Akkadian sign using specialized dictionaries in priority order."""

        # Clean the sign for lookup
        cleaned_sign = self.clean_sign(sign)

        # Search specialized dictionaries in priority order
        for dict_name, dictionary in self.specialized_dicts.items():
            if cleaned_sign in dictionary:
                return (dictionary[cleaned_sign], [])

            # Also try original sign (without cleaning) for some dictionaries
            if sign in dictionary:
                return (dictionary[sign], [])

        # Fallback: return unknown
        return (f"[UNKNOWN:{sign}]", [])
