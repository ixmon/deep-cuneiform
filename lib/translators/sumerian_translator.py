"""
Sumerian ATF translator.
"""

import os
from .base_translator import BaseTranslator

class SumerianTranslator(BaseTranslator):
    """Translator for Sumerian ATF texts."""

    def __init__(self, dict_path=None):
        if dict_path is None:
            dict_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'dictionaries', 'atf_unicode_map.json')
        super().__init__(dict_path)

    def get_language_name(self):
        return "Sumerian"

    def translate_sign(self, sign):
        """Translate a Sumerian sign with special handling."""
        # For Sumerian, we can add specific logic if needed
        return super().translate_sign(sign)
