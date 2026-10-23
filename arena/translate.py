#!/usr/bin/env python3
"""Apply curated batches, never guess missing translations. Stdlib only."""
import argparse
import json
import os
from pathlib import Path
import unicodedata

CATEGORIES = ('abbr', 'names', 'places', 'verbs', 'dic', 'tl')


def order(s):
    return s.casefold(), s


def load(path, default):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def inputs(root):
    entries = {}
    skipped = 0
    # en.txt determines first spelling, including capitalization exceptions.
    paths = sorted(root.glob('*.txt'), key=lambda p: (p.name != 'en.txt', p.name))
    for path in paths:
        if path.name in {'prompt.txt', 'failed.txt'}:
            continue
        for line in path.read_text(encoding='utf-8').splitlines():
            word = unicodedata.normalize('NFC', line.strip())
            if not word or word.startswith('#') or word.casefold() in entries:
                skipped += 1
                continue
            entries[word.casefold()] = word
    return entries, skipped


def check_values(word, values):
    if not isinstance(values, list) or not values or len(values) != len(set(values)):
        raise ValueError(f'Invalid translation array: {word}')
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'Empty translation: {word}')
        if unicodedata.normalize('NFC', value) != value:
            raise ValueError(f'Non-NFC translation: {word}')
        if any(c in value for c in 'يكـة') or any('\u064b' <= c <= '\u065f' for c in value):
            raise ValueError(f'Nonstandard Persian orthography: {word}')
        if not any('\u0600' <= c <= '\u06ff' for c in value) or any(c.isascii() and c.isalpha() for c in value):
            raise ValueError(f'Not Persian script: {word}')


def dump(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def process(root, dry_run=False, allow_partial=False):
    source, skipped = inputs(root)
    cats = {c: load(root / f'{c}.json', {}) for c in CATEGORIES}
    conflicts = load(root / 'conflicts.json', [])
    review = load(root / 'review.json', [])
    for path in sorted((root / 'arena/batches').glob('*.json')):
        batch = load(path, [])
        if len(batch) > 50:
            raise ValueError(f'Batch exceeds 50 entries: {path}')
        for record in batch:
            word = source.get(record['word'].casefold())
            if word is None:
                raise ValueError(f'Not in inputs: {record["word"]}')
            category, values = record['category'], record['translations']
            check_values(word, values)
            if category not in cats:
                raise ValueError(f'Unknown category: {category}')
            owners = [c for c in cats if word in cats[c]]
            if owners and category not in owners:
                raise ValueError(f'Category change requires explicit review: {word}')
            current = cats[category].setdefault(word, [])
            if record.get('contradicts_stored') and current and current != values:
                item = {'word': word, 'stored': current[:], 'proposed': values}
                if item not in conflicts:
                    conflicts.append(item)
            else:
                current.extend(v for v in values if v not in current)
            if record.get('reason'):
                item = {'word': word, 'translations': current[:], 'reason': record['reason']}
                if item not in review:
                    review.append(item)
        # JSON round trip and array validation after every batch.
        for data in cats.values():
            for word, values in json.loads(dump(data)).items():
                check_values(word, values)
    merged, owners, collisions = {}, {}, []
    for category in CATEGORIES:
        for word, values in cats[category].items():
            check_values(word, values)
            folded = word.casefold()
            if folded in owners:
                collision = {'word': word, 'winner': owners[folded], 'loser': category}
                collisions.append(collision)
                if collision not in conflicts:
                    conflicts.append(collision)
                continue
            owners[folded] = category
            merged[word] = values
    # Preserve the specified exact-key union even for case-variant legacy collisions.
    for category in reversed(CATEGORIES):
        merged.update(cats[category])
    union = set().union(*(set(data) for data in cats.values()))
    assert set(merged) == union
    failed_path = root / 'failed.txt'
    failed = {s.strip().casefold() for s in failed_path.read_text().splitlines() if s.strip()} if failed_path.exists() else set()
    if failed & set(owners):
        raise ValueError('Entries both translated and failed')
    extra = (set(owners) | failed) - set(source)
    if extra:
        raise ValueError(f'Entries outside input: {sorted(extra)}')
    pending = sorted((w for k, w in source.items() if k not in owners and k not in failed), key=order)
    report = {
        'complete': not pending and not collisions,
        'input_entries': len(source), 'skipped_lines': skipped,
        'processed': len(owners) + len(failed), 'pending_count': len(pending),
        'counts': {**{f'{c}.json': len(cats[c]) for c in CATEGORIES}, 'persian.json': len(merged), 'failed.txt': len(failed)},
        'transliterations': sorted(cats['tl'], key=order),
        'review': review, 'conflicts': conflicts, 'collisions': collisions,
    }
    print(dump(report), end='')
    if dry_run:
        print(dump({c: cats[c] for c in CATEGORIES}), end='')
    else:
        for c, data in {**cats, 'persian': merged}.items():
            (root / f'{c}.json').write_text(dump(dict(sorted(data.items(), key=lambda x: order(x[0])))), encoding='utf-8')
        for name, data in [('review', review), ('conflicts', conflicts)]:
            if data or (root / f'{name}.json').exists():
                (root / f'{name}.json').write_text(dump(data), encoding='utf-8')
        (root / 'arena/report.json').write_text(dump(report), encoding='utf-8')
        (root / 'arena/pending.json').write_text(dump(pending), encoding='utf-8')
    return 0 if report['complete'] or allow_partial else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--allow-partial', action='store_true', help='Explicitly permit an incomplete checkpoint')
    args = parser.parse_args()
    raise SystemExit(process(args.root, os.environ.get('DRY_RUN') == '1', args.allow_partial))
