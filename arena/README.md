# Persian dictionary checkpoint — incomplete

This is a **partial implementation**, not a completed translation of the corpus.
There are 259,730 distinct input entries; this checkpoint translates 50 common
words (20 ordinary words and 30 primarily verbs). The remaining 259,680 entries
are unprocessed, **not** classified as meaningless. No `failed.txt` entries have
been fabricated. No external lexicographic verification was performed for this
seed batch; translations were manually supplied using contemporary Persian.

The first 50 lines of `en.txt` contain rare historical/technical forms and possible
misspellings. Rather than guess their meanings, this seed selects 50 common words
from the input union. Subsequent batches must review those early lines as well.

## Run

```sh
python arena/translate.py                   # writes outputs; exits 1 while incomplete
DRY_RUN=1 python arena/translate.py         # prints proposals/report; writes nothing
python arena/translate.py --allow-partial   # explicitly accept a partial checkpoint
python -m unittest discover -s arena -p 'test_*.py' -v
```

Input order is `en.txt` first, then other root `.txt` files alphabetically.
`prompt.txt` is instructions, and `failed.txt` is output: neither is vocabulary.
Whitespace/comments/blanks are skipped and entries deduplicated case-insensitively,
retaining the first spelling. Root abbreviation/name/verb lists remain inputs,
not automatic classification rules: they contain ambiguous ordinary words.

Add curated JSON batches under `arena/batches/`, at most 50 records each:

```json
[
  {"word": "book", "category": "dic", "translations": ["کتاب", "رزرو کردن"]}
]
```

Categories are manually curated; this tool does not automatically determine
meaning, proper-name status, primary part of speech, or whether two meanings
contradict. A reviewer must explicitly set `contradicts_stored: true` for a
conflicting proposal. Existing translations are otherwise appended uniquely.
Optional `reason` records uncertainty in `review.json`. Category changes are
rejected for explicit human resolution. Existing cross-category collisions are
logged and resolved in `persian.json` using the requested category priority;
validation still reports failure until the category collision is fixed.

Every batch is JSON round-tripped and translation arrays checked. All category
files and `persian.json` are emitted sorted in UTF-8 with two-space indentation.
The merged file is rebuilt from category files every run. `arena/report.json`
records coverage, counts, loans, review items, and conflicts. The generated
`arena/pending.json` lists all remaining entries locally and is gitignored.
Default validation exits nonzero on missing coverage or collisions. Script checks
cannot replace linguistic review (e.g. infinitives and appropriate ZWNJ usage).

The helper source and tests are also packaged in `arena/helpers.tar.xz`.
This checkpoint should be reviewed via pull request; it should not be merged as
though the full corpus translation were complete.
