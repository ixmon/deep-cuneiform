"""
Base translator class for ATF (ASCII Transliteration Format) translation.
Provides common functionality for translating cuneiform signs to their meanings.
"""

import json
import os
import re
from abc import ABC, abstractmethod

class BaseTranslator(ABC):
    """Abstract base class for ATF translators."""

    def __init__(self, dict_path):
        self.dictionary = self.load_dictionary(dict_path)
        self.simple_signs = self.dictionary.get('simple', {})
        self.compound_signs = self.dictionary.get('compounds', {})
        self.variant_signs = self.dictionary.get('variants', {})
        self.annotations = self.dictionary.get('annotations', {})

    def load_dictionary(self, dict_path):
        """Load dictionary from JSON file."""
        if os.path.exists(dict_path):
            with open(dict_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def clean_sign(self, sign):
        """Clean sign by removing ATF markers and normalizing case."""
        # Remove damage/uncertainty markers
        clean = re.sub(r'[~#?\d].*', '', sign).strip('|').strip('_').upper()
        return clean

    def parse_atf_expression(self, expr):
        """Parse ATF expression and extract signs with annotations."""
        expr = expr.strip()
        annotations = []

        # Normalize the expression for lookup
        lookup_expr = self.clean_sign(expr)

        # Handle annotations at the end
        if expr.endswith('#'):
            annotations.append('damaged')
            expr = expr[:-1]
        if expr.endswith('!'):
            annotations.append('corrected')
            expr = expr[:-1]
        if expr.endswith('*'):
            annotations.append('collated')
            expr = expr[:-1]
        if expr.endswith('?'):
            annotations.append('uncertain')
            expr = expr[:-1]

        # Handle compounds |...|
        if expr.startswith('|') and expr.endswith('|'):
            # Strip variants from compound for lookup
            compound_key = lookup_expr
            for var in ['~A', '~B', '~C', '~D', '~E', '~F', '~G', '~H', '~I', '~J', '~K', '~L', '~M', '~N', '~O', '~P', '~Q', '~R', '~S', '~T', '~U', '~V', '~W', '~X', '~Y', '~Z',
                       '~a', '~b', '~c', '~d', '~e', '~f', '~g', '~h', '~i', '~j', '~k', '~l', '~m', '~n', '~o', '~p', '~q', '~r', '~s', '~t', '~u', '~v', '~w', '~x', '~y', '~z']:
                compound_key = compound_key.replace(var, '')
            if compound_key in self.compound_signs:
                return self.compound_signs[compound_key], annotations
            compound_inner = expr[1:-1]
            return f"[COMPOUND:{compound_inner}]", annotations

        # Simple sign lookup (case-insensitive)
        if lookup_expr in self.simple_signs:
            return self.simple_signs[lookup_expr], annotations

        # Try lowercase version
        lookup_expr_lower = lookup_expr.lower()
        if lookup_expr_lower in self.simple_signs:
            return self.simple_signs[lookup_expr_lower], annotations

        return f"[UNKNOWN:{expr}]", annotations

    def extract_signs_from_atf_line(self, line):
        """Extract individual signs from a single ATF line."""
        # Remove line numbers and other metadata
        line = re.sub(r'^\d+[\'"]*\.', '', line.strip())
        if not line:
            return []

        signs = []
        # Split by comma to get the transliteration part
        if ',' in line:
            parts = line.split(',')
            if len(parts) > 1:
                transliteration = parts[1].strip()
                # Split by spaces and extract potential signs
                candidates = re.split(r'\s+', transliteration)
                for candidate in candidates:
                    candidate = candidate.strip()
                    if candidate and not candidate.startswith('>>') and candidate != '[...]':
                        signs.append(candidate)

        return signs

    def translate_sign(self, sign):
        """Translate a single sign. Override in subclasses for language-specific logic."""
        glyph, ann = self.parse_atf_expression(sign)
        return glyph, ann

    def translate_atf(self, atf_text):
        """Translate full ATF text."""
        # Process ATF line by line
        lines = atf_text.split('\n')
        all_translations = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith('@') or line.startswith('$') or line.startswith('#'):
                continue

            signs = self.extract_signs_from_atf_line(line)
            line_translations = []

            for sign in signs:
                translation, ann = self.translate_sign(sign)
                line_translations.append(translation)

            if line_translations:
                all_translations.append(' '.join(line_translations))

        return '\n'.join(all_translations)

    @abstractmethod
    def get_language_name(self):
        """Return the language name (e.g., 'Sumerian', 'Akkadian')."""
        pass
