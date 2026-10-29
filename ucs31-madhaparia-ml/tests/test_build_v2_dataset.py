
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_v2_dataset.py"


class TestV2DatasetBuilder(unittest.TestCase):

    def run_builder(self, output, seed=42, count=100):
        subprocess.run(
            [
                sys.executable,
                str(BUILDER),
                "--max-examples", str(count),
                "--seed", str(seed),
                "--output", str(output),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_reproducible_generation(self):
        with tempfile.TemporaryDirectory() as folder:
            first = Path(folder) / "first.jsonl"
            second = Path(folder) / "second.jsonl"

            self.run_builder(first)
            self.run_builder(second)

            self.assertEqual(
                first.read_bytes(),
                second.read_bytes()
            )

    def test_generated_dataset_structure(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "test.jsonl"

            self.run_builder(output)

            records = [
                json.loads(line)
                for line in output.read_text(
                    encoding="utf-8"
                ).splitlines()
            ]

            self.assertEqual(len(records), 100)

            with open(
                ROOT / "nlp/canonical_symptoms.json",
                encoding="utf-8"
            ) as f:
                canonical = json.load(f)

            with open(
                ROOT / "data/raw/release_evidences.json",
                encoding="utf-8"
            ) as f:
                metadata = json.load(f)

            with open(
                ROOT / "models/model_features.json",
                encoding="utf-8"
            ) as f:
                features = json.load(f)

            mapped = {
                code
                for symptom in canonical
                for code in symptom.get("features", [])
            }

            eligible = {
                code for code in features
                if code in mapped
                and code in metadata
                and metadata[code].get("data_type") == "B"
                and not metadata[code].get("is_antecedent", False)
            }

            source_rows = set()

            for record in records:
                present = set(record["present"])
                unknown = set(record["unknown"])

                self.assertEqual(
                    record["source_dataset"], "DDXPlus"
                )
                self.assertEqual(
                    record["source_split"], "train"
                )
                self.assertEqual(record["absent"], [])

                self.assertFalse(present & unknown)
                self.assertEqual(present | unknown, eligible)
                self.assertGreaterEqual(len(present), 1)
                self.assertLessEqual(len(present), 5)

                source = record["source_row"]
                self.assertNotIn(source, source_rows)
                source_rows.add(source)


if __name__ == "__main__":
    unittest.main()
