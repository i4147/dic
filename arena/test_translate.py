import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from translate import inputs, process


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "arena/batches").mkdir(parents=True)
        (self.root / "en.txt").write_text("book\nBook\n\n # comment\nrun\nunknown\n")
        (self.root / "prompt.txt").write_text("not vocabulary")
        self.batch = self.root / "arena/batches/0001.json"
        self.batch.write_text(
            json.dumps(
                [
                    {"word": "book", "category": "dic", "translations": ["کتاب"]},
                    {"word": "run", "category": "verbs", "translations": ["دویدن"]},
                ],
                ensure_ascii=False,
            )
        )

    def run_pipeline(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return process(self.root, **kwargs)

    def test_inputs(self):
        words, skipped = inputs(self.root)
        self.assertEqual(list(words.values()), ["book", "run", "unknown"])
        self.assertEqual(skipped, 3)

    def test_incomplete_is_failure_and_union_is_exact(self):
        self.assertEqual(self.run_pipeline(), 1)
        merged = json.loads((self.root / "persian.json").read_text())
        self.assertEqual(merged, {"book": ["کتاب"], "run": ["دویدن"]})
        self.assertEqual(json.loads((self.root / "arena/pending.json").read_text()), ["unknown"])

    def test_idempotent(self):
        self.run_pipeline()
        before = {p: p.read_bytes() for p in self.root.rglob("*.json")}
        self.run_pipeline()
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*.json")})

    def test_dry_run_writes_nothing(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.run_pipeline(dry_run=True)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_collision_priority_and_log(self):
        self.run_pipeline()
        (self.root / "tl.json").write_text(json.dumps({"book": ["بوک"]}))
        self.assertEqual(self.run_pipeline(), 1)
        merged = json.loads((self.root / "persian.json").read_text())
        self.assertEqual(merged["book"], ["کتاب"])
        self.assertTrue(json.loads((self.root / "conflicts.json").read_text()))

    def test_invalid_orthography_rejected(self):
        self.batch.write_text(json.dumps([{"word": "book", "category": "dic", "translations": ["كتاب"]}]))
        with self.assertRaises(ValueError):
            self.run_pipeline()

    def test_explicit_conflict_keeps_stored(self):
        self.run_pipeline()
        self.batch.write_text(
            json.dumps([{"word": "book", "category": "dic", "translations": ["درخت"], "contradicts_stored": True}])
        )
        self.run_pipeline()
        self.assertEqual(json.loads((self.root / "dic.json").read_text())["book"], ["کتاب"])
        self.assertTrue(json.loads((self.root / "conflicts.json").read_text()))

    def test_append_and_complete(self):
        self.run_pipeline()
        (self.root / "failed.txt").write_text("unknown\n")
        self.batch.write_text(json.dumps([{"word": "book", "category": "dic", "translations": ["کتاب", "رزرو کردن"]}]))
        self.assertEqual(self.run_pipeline(), 0)
        self.assertEqual(json.loads((self.root / "dic.json").read_text())["book"], ["کتاب", "رزرو کردن"])


if __name__ == "__main__":
    unittest.main()
