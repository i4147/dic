please extend this code by applying requested changes
## Additional flags / functionality
- consider multi-word exists in records
- add a fuzzy string distance threshold (add a flag for it)
- add -b,--backend flag to choose from (text-unidecode,unidecode,polyglot,anyascii,transliterate) libraries to detect more transliterated words
- `-n, --dry-run` — preview what would be removed, don't write
- `-o, --output PATH` — write cleaned JSON elsewhere instead of in-place
- `--removed-file PATH` — custom path for removed records (instead of hardcoded `tl.json`)
- `--backup` — write `file.bak` before modifying
- `-v, --verbose` / `-q, --quiet` — per-record logging vs silence
- `--report` — print stats (total, kept, removed, % transliterated, top offenders)
- `--threshold FLOAT` — require a confidence score (see below) before removal
- `--interactive` / `-i` — prompt per candidate (keep/remove/keep-all/remove-all)
- `--check` — CI mode: exit non-zero if any transliterations found
- `--allowlist FILE` — words/keys never to remove
- `--sort-keys`, `--indent N`, `--encoding` — output formatting
- `--jsonl` — stream JSON Lines for huge files
- `--multi FILE...` — batch process several files

## Extending transliteration detection

**Better Persian phonetics**
- convert arabic variant to Persian before processing: `ي→ی`, `ك→ک`, ZWNJ (`\u200c`), Arabic-Indic digits `۰-۹`
- Strip diacritics/tashdid via `unicodedata`
- Treat `و` as `v/u/o`, `ی` as `y/i/e`, silent final `ه` — map to *sets* of alternatives, not one char
- Handle digraphs explicitly (`خو`, `تش`, `سی`)

**Fuzzy matching instead of exact**
- Use `difflib.SequenceMatcher` / Levenshtein / Jaro-Winkler with a threshold (e.g. `ratio ≥ 0.80`) on the vowel-stripped forms
- Return a *score* so `--threshold` can gate removals and reports can rank them

**Alternative-based matching**
- Generate all phonetic variants (e.g. `ق→{gh,q}`, `خ→{kh,x}`, `چ→{ch,č}`) and test set-intersection with English variants
- Also strip vowels / normalize `ph→f`, `c→k`, `w→v`, `oo→u` on the English side

**Word-level**
- Split multi-word keys/values and match word-by-word (catches `{"ice cream": "آیس کریم"}`)

**Broaden "is transliterated" rules**
- Persian field contains **zero** Persian letters → transliteration/loanword
- Persian field is pure Latin, digits, or mixed-script
- Add a **loanword dictionary** (`کامپیوتر`, `رادیو`, `تلفن`…) — optionally *flag* rather than remove
- Bidirectional: also detect Persian keys whose value is Latin (swap check)
- Detect English keys written in Persian script even when transliteration is imperfect

**Libraries to consider**
- `unidecode`, `persiantools`, `hazm` (normalization), `python-Levenshtein` or `rapidfuzz` (fuzzy score)


import argparse
import json
import re
import sys
from pathlib import Path

# A robust phonetic map mapping Persian characters to their English/Latin sounds
PERSIAN_TO_LATIN = {
    'ا': 'a', 'آ': 'a', 'ب': 'b', 'پ': 'p', 'ت': 't', 'ث': 's', 'ج': 'j', 'چ': 'ch',
    'ح': 'h', 'خ': 'kh', 'د': 'd', 'ذ': 'z', 'ر': 'r', 'ز': 'z', 'ژ': 'zh', 'س': 's',
    'ش': 'sh', 'ص': 's', 'ض': 'z', 'ط': 't', 'ظ': 'z', 'ع': 'a', 'غ': 'gh', 'ف': 'f',
    'ق': 'gh', 'ک': 'k', 'گ': 'g', 'ل': 'l', 'م': 'm', 'ن': 'n', 'و': 'v', 'ه': 'h',
    'ی': 'y', 'ئ': 'e', 'ء': 'a',
    # Short vowels often omitted but captured if present explicitly
    'ِ': 'e', 'ُ': 'o', 'َ': 'a'
}

def normalize_text(text):
    """Removes punctuation, extra spaces, and forces lowercase for clean comparison."""
    text = str(text).lower().strip()
    return re.sub(r'[^\w\s]', '', text)

def convert_persian_to_latin_phonetics(fa_text):
    """Converts Persian characters to a simplified Finglish/Latin phonetic string."""
    normalized = normalize_text(fa_text)
    phonetic_chars = [PERSIAN_TO_LATIN.get(char, char) for char in normalized]
    return "".join(phonetic_chars)

def is_transliterated(en_key, fa_value):
    """
    Advanced detection for English-Persian transliterations.
    Catches exact copies, pure English values, and phonetic transliterations.
    """
    en_clean = normalize_text(en_key)
    fa_clean = normalize_text(fa_value)
    
    # 1. Catch exact or case-insensitive copies (e.g., {"water": "water"})
    if en_clean == fa_clean:
        return True
        
    # 2. Catch records where the Persian side contains only Latin characters (e.g., {"water": "vater"})
    if re.match(r'^[a-z0-9\s]+$', fa_clean):
        return True
        
    # 3. Phonetic matching (e.g., {"computer": "کامپیوتر"} -> converts to "kāmpiyutr")
    fa_phonetic = convert_persian_to_latin_phonetics(fa_clean)
    
    # Check if the phonetic version closely matches the English key
    # Handles exact matches or common vowel drops (e.g., 'computer' vs 'kompiuter')
    if fa_phonetic == en_clean:
        return True
        
    # Optional: strip vowels from both to catch zero-vowel Persian scripts (e.g., "dict" vs "دکت")
    vowels = r'[aeiouy]'
    if re.sub(vowels, '', fa_phonetic) == re.sub(vowels, '', en_clean):
        return True

    return False

def process_bilingual_json():
    parser = argparse.ArgumentParser(description="Remove transliterated records from an EN-FA JSON dictionary.")
    parser.add_argument("input_file", help="Path to the JSON file to process.")
    parser.add_argument("-m", action="store_true", help="Save removed transliterated records to 'tl.json'.")
    
    args = parser.parse_args()
    input_path = Path(args.input_file)
    
    if not input_path.is_file():
        print(f"Error: '{args.input_file}' is not a valid file.", file=sys.stderr)
        sys.exit(1)
        
    try:
        with input_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            
        if not isinstance(data, dict):
            print("Error: JSON root must be a dictionary/object.", file=sys.stderr)
            sys.exit(1)
            
        cleaned_data = {}
        removed_data = {}
        
        for key, value in data.items():
            if is_transliterated(key, value):
                removed_data[key] = value
            else:
                cleaned_data[key] = value
                
        # Inplace update
        with input_path.open("w", encoding="utf-8") as f:
            json.dump(cleaned_data, f, ensure_ascii=False, indent=4)
            
        if args.m:
            tl_path = input_path.parent / "tl.json"
            with tl_path.open("w", encoding="utf-8") as f:
                json.dump(removed_data, f, ensure_ascii=False, indent=4)
            print(f"Saved {len(removed_data)} transliterated records to {tl_path}", file=sys.stderr)
            
        print(f"Successfully updated '{args.input_file}' inplace. Keep count: {len(cleaned_data)}", file=sys.stderr)

    except json.JSONDecodeError:
        print(f"Error: '{args.input_file}' is not a valid JSON file.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error processing file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    process_bilingual_json()
