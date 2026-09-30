import json
import re
import sys
from pathlib import Path


def transliterate(word):
    mapping = {
        "ph": "ف",
        "ch": "چ",
        "sh": "ش",
        "th": "ت",
        "ae": "آ",
        "oe": "و",
        "aa": "آ",
        "c": "ک",
        "k": "ک",
        "q": "ک",
        "x": "کس",
        "a": "آ",
        "b": "ب",
        "d": "د",
        "e": "ه",
        "f": "ف",
        "g": "گ",
        "h": "ه",
        "i": "ی",
        "j": "ج",
        "l": "ل",
        "m": "م",
        "n": "ن",
        "o": "و",
        "p": "پ",
        "r": "ر",
        "s": "س",
        "t": "ت",
        "u": "و",
        "v": "و",
        "w": "و",
        "y": "ی",
        "z": "ز",
    }
    word = word.lower()
    res = ""
    i = 0
    while i < len(word):
        if word[i : i + 2] in ["ph", "ch", "sh", "th", "ae", "oe", "aa"]:
            res += mapping[word[i : i + 2]]
            i += 2
        elif word[i] == "c":
            if i + 1 < len(word) and word[i + 1] in ["e", "i", "y"]:
                res += "س"
            else:
                res += "ک"
            i += 1
        elif word[i] in mapping:
            res += mapping[word[i]]
            i += 1
        else:
            i += 1
    return res


common = {
    "Aves": "پرندگان",
    "aardvark": "مورچه‌خوار",
    "aardwolf": "پروتله",
    "Animalivora": "جانورخواران",
    "Anseres": "غازسانان",
    "Anseriformes": "غازسانان",
    "Araneae": "عنکبوت‌ها",
    "Arachnoidea": "عنکبوتیان",
    "Acipenseridae": "تاس‌ماهیان",
    "Accipiter": "قرقی",
    "Aceraceae": "افراسانان",
    "Apidae": "زنبوران عسل",
    "Apis": "زنبور عسل",
    "Aquifoliaceae": "خوش‌خارسانان",
    "Araceae": "گل‌شیپوریان",
    "Araliaceae": "عشقهیان",
    "Arcidae": "گوش‌ماهیان",
    "Ardeidae": "حواصیلان",
    "Asteraceae": "کاسنیان",
    "Balaenidae": "نهنگان راست",
    "Balaenoptera": "تیغ‌باله",
    "Balsaminaceae": "گل‌حنائیان",
    "Bambuseae": "خیزران",
    "Berberidaceae": "زرشکیان",
    "Betulaceae": "توسکان",
    "Bignoniaceae": "پیچ‌اناریان",
    "Boidae": "بوآیان",
    "Bombidae": "زنبوران درشت",
    "Bombycidae": "کرم ابریشم (خانواده)",
    "Boraginaceae": "گاوزبانیان",
    "Bovidae": "گاوسانان",
    "Brassicaceae": "شب‌بویان",
    "Bromeliaceae": "آناناسیان",
    "Bucerotidae": "نوک‌شاخان",
    "Bufonidae": "وزغ‌های حقیقی",
    "Buprestidae": "سوسک‌های جواهر",
    "Burseraceae": "بخوران",
    "Buxaceae": "شمشادیان",
    "Cacatuidae": "طوطی‌کاکلیان",
    "Camelidae": "شترسانان",
    "Campanulaceae": "گل‌استکانیان",
    "Canidae": "سگ‌سانان",
    "Canis": "سگ (سرده)",
    "Cannaceae": "اختران",
    "Caprimulgidae": "شب‌گردان",
    "Carangidae": "گیش‌ماهیان",
    "Caryophyllaceae": "میخکیان",
    "Casuariidae": "کاسوواریان",
    "Casuarinaceae": "کازواریناسه",
    "Cathartidae": "کرکس‌های جهان جدید",
    "Cebidae": "کپوچین‌واران",
    "Celastraceae": "خوش‌خارسانان",
    "Cerambycidae": "سوسک‌های شاخ‌بلند",
    "Ceratophyllaceae": "تخته‌شاخان",
    "Cercopithecidae": "کپی‌های جهان قدیم",
    "Certhiidae": "دارخزکان",
    "Cetorhinidae": "کوسه‌نهنگان",
    "Chaetodontidae": "پروانه‌ماهیان",
    "Charadriidae": "سلیمیان",
    "Chenopodiaceae": "سلمه‌ترهیان",
    "Chimaeridae": "موش‌ماهیان",
    "Chironomidae": "پشه‌های غیرگزنده",
    "Chrysomelidae": "سوسک‌های برگ‌خوار",
    "Cicadidae": "زنجره‌ها",
    "Ciconiidae": "لک‌لکان",
    "Cimicidae": "ساسان",
    "Cinclidae": "زیرآبروک‌ها",
    "Clupeidae": "شگ‌ماهیان",
    "Coccinellidae": "کفشدوزکان",
    "Coliidae": "موش‌مرغان",
    "Colubridae": "قمچه‌ماران",
    "Columbiformes": "کبوترسانان",
    "Combretaceae": "شانهیان",
    "Commelinaceae": "برگ‌بیدیان",
    "Conidae": "حلزون‌های مخروطی",
    "Convallariaceae": "مویه‌ایان",
    "Convolvulaceae": "نیلوفریان",
    "Coraciidae": "سبزقبایان",
    "Corvidae": "کلاغان",
    "Corylaceae": "فندقیان",
    "Cracidae": "کرکسان",
    "Crassulaceae": "گل‌نازیان",
    "Cricetidae": "همستران",
    "Crotalidae": "افعی‌های سرچاله",
    "Cruciferae": "چلیپائیان",
    "Cuculidae": "کوکویان",
    "Culicidae": "پشه‌ها",
    "Cucurbitaceae": "کدوئیان",
    "Cupressaceae": "سرویان",
    "Curculionidae": "سرخرطومیان",
    "Cyatheaceae": "سرخس‌های درختی",
    "Cycadaceae": "سیکاسیان",
    "Cyclostomata": "گرددهانان",
    "Cyperaceae": "اویارسلامیان",
    "Cypraeidae": "صدف‌های مروارید",
    "Cyprinidae": "کپورماهیان",
    "Dasyatidae": "لوزی‌ماهیان",
    "Dasypodidae": "آرمادیلوها",
    "Dasyuridae": "ستبردمان",
    "Delphacidae": "زنجره‌های جهنده",
    "Dermestidae": "سوسک‌های چرم‌خوار",
    "Didelphidae": "اپوسوم‌ها",
    "Diomedeidae": "آلباتروسان",
    "Dioscoreaceae": "یامیان",
    "Dipsacaceae": "خواجه‌باشیان",
    "Dipterocarpaceae": "دوبال‌میوگان",
    "Droseraceae": "شبنمیان",
    "Dytiscidae": "سوسک‌های غواص",
}


def translate_word(word):
    if word in common:
        return common[word]
    if word.lower() in common:
        return common[word.lower()]

    if word.endswith("aceae"):
        return transliterate(word[:-5]) + "آسه‌آ"
    if word.endswith("idae"):
        return transliterate(word[:-4]) + "ایدا"
    if word.endswith("ales"):
        return transliterate(word[:-4]) + "ال‌ها"
    if word.endswith("inae"):
        return transliterate(word[:-4]) + "اینه"
    if word.endswith("oidei"):
        return transliterate(word[:-5]) + "ویدئی"
    if word.endswith("iformes"):
        return transliterate(word[:-7]) + "شکلان"

    return transliterate(word)


def main():
    with open("en1.txt", "r", encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]
    translated = {word: translate_word(word) for word in words}
    outpath = Path("en1.json")
    if outpath.exists():
        sys.exit(1)
    with open("en5.json", "w", encoding="utf-8") as f:
        json.dump(translated, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
