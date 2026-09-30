import json
import re


def phonetic_reduce(word, is_persian=False):
    word = word.lower()
    if is_persian:
        
        groups = {
            "ب": "b",
            "پ": "p",
            "ت": "t",
            "ط": "t",
            "د": "d",
            "ث": "s",
            "س": "s",
            "ص": "s",
            "ذ": "z",
            "ز": "z",
            "ض": "z",
            "ظ": "z",
            "ک": "k",
            "گ": "g",
            "ق": "k",
            "غ": "k",
            "خ": "k",
            "ج": "j",
            "چ": "c",
            "ش": "s",
            "ژ": "j",
            "ف": "f",
            "ل": "l",
            "ر": "r",
            "م": "m",
            "ن": "n",
            "ح": "h",
            "ه": "h",
            
            "و": "",
            "ی": "",
            "ا": "",
            "آ": "",
            "ع": "",
            "ئ": "",
            "ء": "",
            " ": "",
            "-": "",
        }
    else:
        
        word = re.sub(r"[aeiouywh]", "", word)
        
        groups = {
            "b": "b",
            "p": "p",
            "t": "t",
            "d": "d",
            "s": "s",
            "z": "z",
            "c": "k",
            "x": "s",
            "k": "k",
            "g": "g",
            "q": "k",
            "j": "j",
            "f": "f",
            "v": "v",
            "l": "l",
            "r": "r",
            "m": "m",
            "n": "n",
        }

    res = []
    for char in word:
        if char in groups:
            val = groups[char]
            if val:
                res.append(val)

    return "".join(res)


def is_transliterated(en, fa):
    en_p = phonetic_reduce(en, is_persian=False)
    fa_p = phonetic_reduce(fa, is_persian=True)

    if not en_p or not fa_p:
        return False

    
    if en_p == fa_p:
        return True

    
    if abs(len(en_p) - len(fa_p)) <= 1:
        
        if en_p in fa_p or fa_p in en_p:
            return True

    return False



test_data = {
    "Aaronic": "هارونیک",
    "Aaronical": "هارونیکال",
    "Abdominales": "شکم",
    "Table": "تیبل",
    "Chair": "صندلی",
    "Computer": "کامپیوتر",
    "Apple": "سیب",
    "Orange": "پرتقال",
}

for en, fa in test_data.items():
    en_p = phonetic_reduce(en, is_persian=False)
    fa_p = phonetic_reduce(fa, is_persian=True)
    res = is_transliterated(en, fa)
    print(f"{en} ({en_p}) -> {fa} ({fa_p}): {res}")
