#!/usr/bin/env python3
import sys
import json
import re






NATIVE_PERSIAN_LETTERS = set("گچپژ")



COMMON_PERSIAN_LETTERS = set("شخزآذطظضثقفعهحغ")




TRANSLIT_PRONE_LETTERS = set("انرسهویکبتملدصزف")






TRANSLIT_SUFFIXES = {
    "اسه", "اسا", "سه", "سا", "ه", "یان", "ان", "ها", "ای",
    "وس", "وسه", "یده", "یدا", "تی", "تا", "کاسه", "کاسا",
    "نی", "نا", "ری", "را", "لی", "لا", "می", "ما",
}






LATIN_TO_TRANSLIT = {
    "aceae": ["اسه", "اسا", "سه"],
    "ae":    ["ه", "ای"],
    "us":    ["وس"],
    "um":    ["وم"],
    "es":    ["س", "اس"],
    "is":    ["یس", "یس"],
    "a":     ["ا", "آ"],
    "i":     ["ی"],
    "os":    ["وس"],
    "on":    ["ون"],
}






PERSIAN_TO_LATIN = {
    "ا": "a", "آ": "a", "ب": "b", "پ": "p", "ت": "t", "ث": "s",
    "ج": "j", "چ": "ch", "ح": "h", "خ": "kh", "د": "d", "ذ": "z",
    "ر": "r", "ز": "z", "ژ": "zh", "س": "s", "ش": "sh", "ص": "s",
    "ض": "z", "ط": "t", "ظ": "z", "ع": "", "غ": "gh", "ف": "f",
    "ق": "gh", "ک": "k", "گ": "g", "ل": "l", "م": "m", "ن": "n",
    "و": "v", "ه": "h", "ی": "y",
}


def _score_persian(s: str) -> int:
    score = 0
    for c in s:
        if c in NATIVE_PERSIAN_LETTERS:
            score += 3
        elif c in COMMON_PERSIAN_LETTERS:
            score += 2
        elif c in TRANSLIT_PRONE_LETTERS:
            score += 0
        else:
            score += 1  
    return score


def _translit_ratio(s: str) -> float:
    letters = [c for c in s if '\u0600' <= c <= '\u06FF']
    if not letters:
        return 0.0
    return sum(1 for c in letters if c in TRANSLIT_PRONE_LETTERS) / len(letters)


def _matches_translit_suffix(s: str) -> bool:
    for suf in TRANSLIT_SUFFIXES:
        if s.endswith(suf):
            return True
    return False


def _matches_latin_pattern(s: str, latin_word: str = "") -> bool:
    if not latin_word:
        return False
    reconstructed = "".join(PERSIAN_TO_LATIN.get(c, "") for c in s)
    latin_clean = re.sub(r"[^a-z]", "", latin_word.lower())
    recon_clean = re.sub(r"[^a-z]", "", reconstructed)
    if not recon_clean:
        return False
    
    if abs(len(recon_clean) - len(latin_clean)) <= 2:
        overlap = sum(1 for a, b in zip(recon_clean, latin_clean) if a == b)
        if overlap / max(len(latin_clean), 1) > 0.6:
            return True
    return False


def is_transliteration(s: str, latin_word: str = "") -> bool:
    if not s:
        return True

    
    if any(c in NATIVE_PERSIAN_LETTERS for c in s):
        return False

    
    ratio = _translit_ratio(s)
    suffix_hit = _matches_translit_suffix(s)

    
    if _matches_latin_pattern(s, latin_word):
        return True

    
    score = _score_persian(s)
    length = max(len(s), 1)

    
    if ratio > 0.9 and not any(c in COMMON_PERSIAN_LETTERS for c in s):
        return True

    
    if suffix_hit and score / length < 1.0:
        return True

    return False


def clean_entry(key: str, translations):
    if not isinstance(translations, list):
        return translations

    kept = [t for t in translations if not is_transliteration(t, key)]

    
    if not kept:
        kept = translations

    return kept


def main():
    if len(sys.argv) != 2:
        print("Usage: python clean_dict.py <dict.json>")
        sys.exit(1)

    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cleaned = {k: clean_entry(k, v) for k, v in data.items()}

    with open(path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"Updated {path}")


if __name__ == "__main__":
    main()