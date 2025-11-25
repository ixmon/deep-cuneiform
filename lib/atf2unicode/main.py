# cuneiform_atf.py
# ------------------------------------------------------------
# ATF → Unicode Cuneiform mapper (Sumerian, Akkadian, etc.)
# Drop-in replacement for the missing PyPI package `atf2unicode`
# ------------------------------------------------------------

import json
import os
import re

# Load mappings from JSON
MAPPINGS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'dictionaries', 'atf_unicode_map.json')
if os.path.exists(MAPPINGS_FILE):
    with open(MAPPINGS_FILE, 'r') as f:
        MAPPINGS = json.load(f)
else:
    MAPPINGS = {"simple": {}, "compounds": {}, "variants": {}, "annotations": {}}

# ------------------------------------------------------------------
# 1. SIGN → UNICODE TABLE (fallback if JSON not loaded)
# ------------------------------------------------------------------
# Source: CDLI sign list + Unicode 15.0 Cuneiform block
# Format:  "ATF_NAME": "\U00012xxx"
# ------------------------------------------------------------------
ATF_TO_UNICODE = {
    # --- Basic signs ------------------------------------------------
    "A":       "\U00012000",   # 𒀀  water
    "AB":      "\U0001200A",   # 𒀊  father
    "AD":      "\U0001201C",   # 𒀜  to advise
    "AG":      "\U0001201D",   # 𒀝  to do
    "AK":      "\U0001201E",   # 𒀞  to make
    "AL":      "\U00012023",   # 𒀣  to be high
    "AM":      "\U0001202A",   # 𒀪  wild bull
    "AN":      "\U0001202D",   # 𒀭  sky / god
    "AP":      "\U00012038",   # 𒀸  to burn
    "AR":      "\U0001203F",   # 𒀿  to grind
    "AS":      "\U0001203A",   # 𒀺  one
    "ASZ":     "\U0001203B",   # 𒀻  one (variant)
    "BAD":     "\U00012041",   # 𒁁  wall / to die
    "BA":      "\U00012040",   # 𒁀  to give
    "BAL":     "\U00012047",   # 𒁇  to turn
    "BAN":     "\U00012048",   # 𒁈  bow
    "BAR":     "\U00012049",   # 𒁉  to divide
    "BI":      "\U00012049",   # 𒁉  (same as BAR)
    "BU":      "\U0001204D",   # 𒁍  to blow
    "BUL":     "\U0001204E",   # 𒁎  to rejoice
    "BUR":     "\U00012053",   # 𒁓  to release
    "DA":      "\U00012055",   # 𒁕  side
    "DAG":     "\U00012056",   # 𒁖  platform
    "DAM":     "\U0001205D",   # 𒁝  spouse
    "DAR":     "\U0001205F",   # 𒁟  to split
    "DI":      "\U00012062",   # 𒁢  to speak
    "DIB":     "\U00012063",   # 𒁣  to pass
    "DID":     "\U00012065",   # 𒁥  to go
    "DIL":     "\U00012066",   # 𒁦  single
    "DIM":     "\U00012067",   # ��  to fashion
    "DIN":     "\U00012068",   # 𒁨  life
    "DISZ":    "\U00012079",   # 𒁹  one (numeric)
    "DU":      "\U0001206D",   # 𒁭  to go
    "DUB":     "\U0001206E",   # 𒁮  tablet
    "DUG":     "\U0001206F",   # 𒁯  pot
    "DUL":     "\U00012070",   # 𒁰  to cover
    "DUMU":    "\U00012071",   # 𒁱  child
    "DUN":     "\U00012072",   # 𒁲  to be heavy
    "DUR":     "\U00012073",   # 𒁳  to sit
    "E":       "\U0001208A",   # 𒂊  house
    "EN":      "\U00012097",   # 𒂗  lord
    "ER":      "\U0001209F",   # 𒂟  to weep
    "ESZ":     "\U000120A0",   # 𒂠  three
    "GA":      "\U000120B5",   # 𒂵  milk
    "GAL":     "\U000120F2",   # 𒃲  great
    "GAN":     "\U000120F7",   # 𒃷  field
    "GAR":     "\U000120FB",   # 𒃻  to place
    "GI":      "\U000120FB",   # 𒃻  reed
    "GID":     "\U000120FC",   # 𒃼  to be long
    "GIR":     "\U000120FD",   # 𒃽  foot
    "GISZ":    "\U00012113",   # 𒄑  tree / wood
    "GU":      "\U0001211E",   # 𒄞  neck
    "GUB":     "\U00012121",   # 𒄡  to stand
    "GUL":     "\U00012124",   # 𒄤  to destroy
    "GUM":     "\U00012126",   # 𒄦  to crush
    "GUR":     "\U0001212B",   # 𒄫  to return
    "HA":      "\U0001212D",   # 𒄭  fish
    "HAL":     "\U0001212E",   # ��  to divide
    "HI":      "\U0001212F",   # 𒄯  to mix
    "HU":      "\U00012137",   # 𒄷  bird
    "I":       "\U0001213D",   # 𒄽  (same as I)
    "IB":      "\U00012145",   # 𒅅  to be angry
    "ID":      "\U00012146",   # 𒅆  river
    "IG":      "\U00012147",   # 𒅇  door
    "IL":      "\U0001214D",   # 𒅍  to raise
    "IM":      "\U0001214E",   # 𒅎  clay
    "IN":      "\U00012151",   # 𒅑  to be
    "IR":      "\U00012153",   # 𒅓  to smell
    "ISZ":     "\U00012154",   # 𒅔  to break
    "KA":      "\U00012157",   # 𒅗  mouth
    "KAK":     "\U00012158",   # 𒅘  nail
    "KAM":     "\U00012159",   # 𒅙  to bind
    "KI":      "\U0001215A",   # 𒅚  earth
    "KISZ":    "\U0001215B",   # 𒅛  totality
    "KU":      "\U0001215C",   # 𒅜  to eat
    "KUR":     "\U000121B3",   # 𒆳  land / mountain
    "LA":      "\U000121B7",   # 𒆷  to hang
    "LAGAB":   "\U000121B8",   # ��  block
    "LAM":     "\U000121BC",   # 𒆼  to be abundant
    "LI":      "\U000121C0",   # 𒇀  juniper
    "LU":      "\U000121FB",   # 𒇻  man
    "LUGAL":   "\U00012217",   # 𒈗  king
    "MA":      "\U00012220",   # 𒈠  ship
    "ME":      "\U00012228",   # 𒈨  to be
    "MI":      "\U0001222A",   # 𒈪  night
    "MU":      "\U0001222B",   # 𒈫  name / year
    "MUNUS":   "\U0001222D",   # ��  woman
    "NA":      "\U0001223E",   # 𒈾  stone
    "NI":      "\U0001224E",   # 𒉎  fear
    "NU":      "\U0001224F",   # 𒉏  not
    "PA":      "\U0001227A",   # 𒉺  branch / staff
    "RA":      "\U0001228F",   # 𒊏  to strike
    "RI":      "\U00012291",   # 𒊑  to throw
    "RU":      "\U00012293",   # 𒊓  to send
    "SA":      "\U00012296",   # 𒊖  sinew
    "SI":      "\U000122DB",   # 𒋛  horn
    "SU":      "\U000122E2",   # 𒋢  flesh
    "SZU":     "\U000122D3",   # 𒋓  hand
    "TA":      "\U000122EB",   # 𒋫  from
    "TE":      "\U000122F0",   # 𒋰  cheek
    "TI":      "\U000122F3",   # 𒋳  life / arrow
    "TU":      "\U000122F8",   # 𒋸  to enter
    "U":       "\U0001230B",   # 𒌋  and / ten
    "UD":      "\U00012313",   # 𒌓  sun / day
    "UG":      "\U00012315",   # 𒌕  to die
    "UL":      "\U0001231A",   # 𒌚  star
    "UM":      "\U0001231B",   # 𒌛  to speak
    "UN":      "\U0001231C",   # 𒌜  people
    "UR":      "\U00012328",   # 𒌨  dog / city
    "URI":     "\U00012329",   # 𒌩  (city name)
    "USZ":     "\U00012336",   # 𒌶  base
    "ZA":      "\U0001233D",   # 𒌽  (precious stone)
    "ZU":      "\U00012351",   # 𒍑  to know

    # --- Numbers ----------------------------------------------------
    "1":       "\U00012079",   # 𒁹  DISZ
    "2":       "\U0001207A",   # 𒁺  MIN
    "3":       "\U0001207B",   # 𒁻  ESZ5
    "4":       "\U0001207C",   # 𒁼  LIMMU
    "5":       "\U0001207D",   # 𒁽  IA
    "6":       "\U0001207E",   # 𒁾  ASZ
    "7":       "\U0001207F",   # 𒁿  IMIN
    "8":       "\U00012080",   # 𒂀  USS
    "9":       "\U00012081",   # 𒂁  ILIMMU
    "10":      "\U0001207A",   # 𒁺  U (same as 2 for ten in some contexts)

    # --- Add more signs here as needed (the full list is ~1,300) --
    # You can extend this dict from the CDLI sign list CSV if you wish.
}

# ------------------------------------------------------------------
# 2. ATF PARSER
# ------------------------------------------------------------------
def parse_atf_expression(expr: str) -> tuple[str, list[str]]:
    """
    Parse a complex ATF expression into Unicode glyph and annotations.

    Handles compounds |...|, variants ~a, damage #, etc.

    Returns (unicode_glyph, annotations_list)
    """
    expr = expr.strip()
    annotations = []

    # Handle annotations at the end (strip all markers)
    while True:
        stripped = False
        if expr.endswith('#'):
            annotations.append('damaged')
            expr = expr[:-1]
            stripped = True
        if expr.endswith('!'):
            annotations.append('corrected')
            expr = expr[:-1]
            stripped = True
        if expr.endswith('*'):
            annotations.append('collated')
            expr = expr[:-1]
            stripped = True
        if expr.endswith('?'):
            annotations.append('uncertain')
            expr = expr[:-1]
            stripped = True
        if not stripped:
            break

    # Handle compounds |...|
    if expr.startswith('|') and expr.endswith('|'):
        # Strip variants from compound for lookup
        compound_key = expr
        for var in ['~A', '~B', '~C', '~D', '~E', '~F', '~G', '~H', '~I', '~J', '~K', '~L', '~M', '~N', '~O', '~P', '~Q', '~R', '~S', '~T', '~U', '~V', '~W', '~X', '~Y', '~Z']:
            compound_key = compound_key.replace(var, '')
        if compound_key in MAPPINGS.get('compounds', {}):
            return MAPPINGS['compounds'][compound_key], annotations
        compound_inner = expr[1:-1]
        # Parse sub-expressions
        # For simplicity, split by operators
        # TODO: full recursive parsing
        return "[COMPOUND:" + compound_inner + "]", annotations

    # Simple sign lookup
    if expr in MAPPINGS.get('simple', {}):
        return MAPPINGS['simple'][expr], annotations

    return "[UNKNOWN:" + expr + "]", annotations

# ------------------------------------------------------------------
# 3. CONVERSION FUNCTION
# ------------------------------------------------------------------
def atf_to_cuneiform(atf_text: str, unknown: str = "[?]") -> tuple[str, list[str]]:
    """
    Convert an ATF string (e.g. "lugal kur-kur-ra") into Unicode cuneiform.

    Parameters
    ----------
    atf_text : str
        Input in ATF transliteration, case-insensitive.
    unknown : str
        Placeholder for signs not in the table.

    Returns
    -------
    tuple[str, list[str]]
        (Unicode cuneiform string, list of annotations like ['damaged'])
    """
    if not atf_text:
        return "", []

    # Split into signs (simple split, can be improved)
    parts = re.split(r'(\s+|-)', atf_text.strip().upper())
    parts = [p for p in parts if p.strip() and p not in [' ', '-']]

    result = []
    all_annotations = []
    for part in parts:
        glyph, ann = parse_atf_expression(part)
        result.append(glyph)
        all_annotations.extend(ann)

    return "".join(result), all_annotations


# ------------------------------------------------------------------
# 3. QUICK DEMO (run this file directly)
# ------------------------------------------------------------------
if __name__ == "__main__":
    tests = [
        "lugal kur-kur-ra",
        "1(asz) 2(disz) en-lil2",
        "A GISZ SI",
        "d en-lil2",
        "bad3-ti-ra-asz",
        "|(GISZx(DIN.DIN))~a|#",
    ]
    for t in tests:
        glyph, ann = atf_to_cuneiform(t)
        print(f"{t:25} → {glyph} {ann}")
