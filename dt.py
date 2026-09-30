#!/usr/bin/env python3
"""
Detect transliterated entries in an English->Persian dictionary JSON file.

A "transliteration" here means the Persian translation is just a phonetic
spelling of the English word (mapped to Persian letters), not a real
translation. Examples:
    "Eupomatiaceae" -> "یوپوماتیاسه"
    "Knapper"       -> "کناپپهر"
    "Overlander"    -> "ووهرلاندهر"

Usage:
    python detect_transliterated.py input.json

Outputs (next to input file):
    transliterated.json  - only the transliterated pairs
    cleaned.json         - original minus transliterated pairs
"""

import json
import re
import sys
from pathlib import Path





EN_TO_FA = {
    
    "a": ["ا", "آ"],
    "e": ["ا", "ه", "ی"],
    "i": ["ی", "ای"],
    "o": ["و", "ا"],
    "u": ["و", "یو"],
    "y": ["ی"],
    
    "b": ["ب"],
    "c": ["ک", "س"],
    "d": ["د"],
    "f": ["ف"],
    "g": ["گ", "ج"],
    "h": ["ه", "ح"],
    "j": ["ج"],
    "k": ["ک"],
    "l": ["ل"],
    "m": ["م"],
    "n": ["ن"],
    "p": ["پ"],
    "q": ["ق"],
    "r": ["ر"],
    "s": ["س", "ص", "ث"],
    "t": ["ت", "ط"],
    "v": ["و", "ف"],
    "w": ["و"],
    "x": ["کس", "ز", "خش"],
    "z": ["ز", "ذ", "ظ", "ض"],
}


PERSIAN_LETTERS = set("اآبپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی")




RARE_IN_TRANSLIT = set("ثحذصضطظعغ")


LATIN_WORD_RE = re.compile(r"^[A-Za-z][A-Za-z\-'. ]*$")
PERSIAN_RE = re.compile(r"^[\u0600-\u06FF\s\u200c]+$")



def normalize_en(word: str) -> str:
    w = word.lower()
    w = re.sub(r"[^a-z]", "", w)
    
    w = re.sub(r"(.)\1+", r"\1", w)
    return w


def normalize_fa(word: str) -> str:
    w = word.replace("\u200c", "").replace(" ", "").strip()
    
    w = w.replace("ي", "ی").replace("ك", "ک")
    return w


def is_latin(word: str) -> bool:
    return bool(LATIN_WORD_RE.match(word))


def is_persian(word: str) -> bool:
    return bool(PERSIAN_RE.match(word))


def english_skeleton(word: str) -> str:
    w = normalize_en(word)
    if not w:
        return ""
    skeleton = [w[0]]
    for ch in w[1:]:
        
        if ch != skeleton[-1]:
            skeleton.append(ch)
    return "".join(skeleton)


def persian_skeleton(word: str) -> str:
    w = normalize_fa(word)
    if not w:
        return ""
    
    fa_to_en = {
        "ا": "a", "آ": "a",
        "ب": "b", "پ": "p", "ت": "t", "ث": "s",
        "ج": "j", "چ": "c", "ح": "h", "خ": "kh",
        "د": "d", "ذ": "z", "ر": "r", "ز": "z",
        "ژ": "zh", "س": "s", "ش": "sh", "ص": "s",
        "ض": "z", "ط": "t", "ظ": "z", "ع": "a",
        "غ": "gh", "ف": "f", "ق": "gh", "ک": "k",
        "گ": "g", "ل": "l", "م": "m", "ن": "n",
        "و": "v", "ه": "h", "ی": "y",
    }
    out = []
    for ch in w:
        out.append(fa_to_en.get(ch, ""))
    latin = "".join(out)
    
    latin = re.sub(r"(.)\1+", r"\1", latin)
    return latin


def phonetic_similarity(en: str, fa: str) -> float:
    en_sk = english_skeleton(en)
    fa_sk = persian_skeleton(fa)
    if not en_sk or not fa_sk:
        return 0.0

    
    first = 1.0 if en_sk[0] == fa_sk[0] else 0.0

    
    def lcs(a, b):
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if a[i - 1] == b[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
        return dp[m][n]

    lcs_len = lcs(en_sk, fa_sk)
    lcs_ratio = lcs_len / max(len(en_sk), len(fa_sk))

    
    len_ratio = min(len(en_sk), len(fa_sk)) / max(len(en_sk), len(fa_sk))

    
    
    fa_norm = normalize_fa(fa)
    rare_hits = sum(1 for ch in fa_norm if ch in RARE_IN_TRANSLIT)
    rare_penalty = min(rare_hits * 0.15, 0.6)

    score = 0.45 * first + 0.35 * lcs_ratio + 0.20 * len_ratio
    score = max(0.0, score - rare_penalty)
    return score



PROGRAMMING_KEYWORDS = {
    "xor", "regex", "regexp", "ioctl", "stdio", "stdin", "stdout", "stderr",
    "argv", "argc", "malloc", "free", "sizeof", "typedef", "struct",
    "enum", "union", "volatile", "extern", "inline", "constexpr",
    "namespace", "template", "virtual", "override", "lambda", "async",
    "await", "yield", "boolean", "integer", "float", "double", "char",
    "string", "array", "hashmap", "json", "xml", "html", "http", "https",
    "ftp", "ssh", "tcp", "udp", "ip", "dns", "url", "uri", "api", "sdk",
    "ide", "cpu", "gpu", "ram", "rom", "usb", "pci", "bios", "os",
    "cli", "gui", "sql", "nosql", "css", "js", "ts", "php", "asp",
    "cgi", "csv", "tsv", "yaml", "toml", "ini", "conf", "log", "syslog",
    "kernel", "driver", "daemon", "socket", "thread", "process", "fork",
    "exec", "pipe", "buffer", "cache", "stack", "heap", "queue", "tree",
    "graph", "node", "edge", "bit", "byte", "word", "dword", "qword",
}

ROMAN_NUMERAL_RE = re.compile(
    r"^m{0,4}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$",
    re.IGNORECASE,
)


ABBREV_SUFFIXES = (
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "mt",
    "mgr", "comdr", "pvt", "sgt", "cpl", "capt", "lt", "col",
    "gen", "adm", "rev", "hon", "esq", "phd", "md", "ba", "ma",
    "bsc", "msc", "inc", "ltd", "co", "corp", "dept", "univ",
)


def is_programming_term(word: str) -> bool:
    return word.lower() in PROGRAMMING_KEYWORDS


def is_roman_numeral(word: str) -> bool:
    return bool(ROMAN_NUMERAL_RE.match(word))


def is_abbreviation(word: str) -> bool:
    w = word.lower().rstrip(".")
    if w in ABBREV_SUFFIXES:
        return True
    
    if word.isupper() and 2 <= len(word) <= 6:
        return True
    
    if word.endswith(".") and len(word) <= 8:
        return True
    return False


def looks_like_proper_noun(word: str) -> bool:
    return word[:1].isupper() and word[1:].islower() and word.isalpha()


def is_likely_transliteration(en_word: str, fa_translation: str) -> bool:
    if not is_latin(en_word) or not is_persian(fa_translation):
        return False

    en = en_word.strip()
    fa = fa_translation.strip()

    
    if is_programming_term(en):
        return False
    if is_roman_numeral(en):
        return False
    if is_abbreviation(en):
        return False

    
    fa_norm = normalize_fa(fa)
    if " " in fa.strip() and len(fa.strip().split()) > 1:
        
        
        return False

    
    score = phonetic_similarity(en, fa)
    return score >= 0.62



def main():
    if len(sys.argv) != 2:
        print("Usage: python detect_transliterated.py input.json")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.is_file():
        print(f"Error: file not found: {input_path}")
        sys.exit(1)

    out_dir = input_path.parent
    transliterated_path = out_dir / "transliterated.json"
    cleaned_path = out_dir / "cleaned.json"

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    
    transliterated = {}
    cleaned = {}
    total = 0

    for en_word, value in data.items():
        total += 1
        
        if isinstance(value, list):
            fa_translation = value[0] if value else ""
        else:
            fa_translation = str(value)

        if is_likely_transliteration(en_word, fa_translation):
            transliterated[en_word] = value
        else:
            cleaned[en_word] = value

    with transliterated_path.open("w", encoding="utf-8") as f:
        json.dump(transliterated, f, ensure_ascii=False, indent=2)

    with cleaned_path.open("w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"Input        : {input_path}")
    print(f"Total entries: {total}")
    print(f"Transliterated: {len(transliterated)}  ->  {transliterated_path}")
    print(f"Cleaned       : {len(cleaned)}  ->  {cleaned_path}")


if __name__ == "__main__":
    main()