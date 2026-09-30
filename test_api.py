import sys

from google.cloud import translate_v2 as translate


def test_translate():
    try:
        translate_client = translate.Client()
        result = translate_client.translate("hello", target_language="fa")
        print(f"Translation: {result['translatedText']}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    test_translate()
