"""
Language detection for ATF texts.
"""

from .sumerian_translator import SumerianTranslator
from .akkadian_translator import AkkadianTranslator

def detect_language(atf_text, period=""):
    """
    Detect the language of an ATF text and return appropriate translator.

    Args:
        atf_text (str): The ATF text content
        period (str): Period information from metadata

    Returns:
        BaseTranslator: Appropriate translator instance
    """
    # Check ATF language tag first
    if '#atf: lang sux' in atf_text:
        return SumerianTranslator()
    elif '#atf: lang akk' in atf_text or '#atf: lang akk-x' in atf_text:
        return AkkadianTranslator()
    elif '#atf: lang qeb' in atf_text:
        # Eblaite - for now use Akkadian as fallback since they're related
        return AkkadianTranslator()

    # Fall back to period-based detection
    period_lower = period.lower()

    # Akkadian periods
    if any(term in period_lower for term in ['old babylonian', 'middle babylonian', 'neo-assyrian', 'neo-babylonian', 'assyrian', 'babylonian', 'ebla']):
        return AkkadianTranslator()

    # Sumerian periods (default)
    if any(term in period_lower for term in ['early dynastic', 'ed i', 'ed ii', 'ed iii', 'ur iii', 'lagash ii']):
        return SumerianTranslator()

    # Default to Sumerian for unknown periods
    return SumerianTranslator()
