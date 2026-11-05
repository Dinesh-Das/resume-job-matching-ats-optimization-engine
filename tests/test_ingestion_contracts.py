"""Offline regression cases for the public job-ingestion contract.

Fixtures are original synthetic jobs written to temporary directories. These
tests do not read the user's corpus or contact Oracle, model APIs, or websites.
"""

import json
from pathlib import Path
import tempfile
import unittest

from data_ingestion import ingest_jobs


class JobIngestionContractsTests(unittest.TestCase):
    def write_jobs(self, directory, records, filename="jobs.json"):
        target = Path(directory) / filename
        if target.suffix == ".jsonl":
            contents = "\n".join(json.dumps(record) for record in records) + "\n"
        else:
            contents = json.dumps(records)
        target.write_text(contents, encoding="utf-8")
        return str(target)

    def test_valid_json_lines_preserves_each_distinct_job(self):
        records = [
            {
                "title": "Data Engineer",
                "company_name": "Synthetic Analytics",
                "keyskills": "Python SQL",
                "jobdescription": "Build tested data pipelines.",
            },
            {
                "title": "AI Engineer",
                "company_name": "Synthetic Research",
                "keyskills": "Python retrieval",
                "jobdescription": "Evaluate document retrieval.",
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            result = ingest_jobs(self.write_jobs(directory, records, "jobs.jsonl"))

        self.assertEqual(result["title"].tolist(), ["Data Engineer", "AI Engineer"])
        self.assertEqual(len(result), 2)
        self.assertTrue(result["combined_text"].str.len().gt(0).all())

    def test_required_only_record_receives_optional_text_defaults(self):
        records = [{"title": "Data Engineer", "company_name": "Synthetic Analytics"}]
        with tempfile.TemporaryDirectory() as directory:
            result = ingest_jobs(self.write_jobs(directory, records))

        self.assertEqual(len(result), 1)
        self.assertEqual(result.loc[0, "title"], "Data Engineer")
        self.assertEqual(result.loc[0, "keyskills"], "")
        self.assertEqual(result.loc[0, "jobdescription"], "")
        self.assertEqual(result.loc[0, "combined_text"].strip(), "Data Engineer")

    def test_all_invalid_jobs_raise_clear_validation_error(self):
        records = [
            {"title": "", "company_name": "Synthetic Analytics"},
            {"title": "Valid title", "company_name": ""},
        ]
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "(?i)valid"):
                ingest_jobs(self.write_jobs(directory, records))

    def test_fallback_deduplication_preserves_field_boundaries(self):
        # Both concatenations equal "abcdef". They are different title and
        # description pairs and must not collapse into one corpus record.
        records = [
            {
                "title": "ab",
                "company_name": "Synthetic Analytics",
                "keyskills": "",
                "jobdescription": "cdef",
                "url": "",
            },
            {
                "title": "abc",
                "company_name": "Synthetic Analytics",
                "keyskills": "",
                "jobdescription": "def",
                "url": "",
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            result = ingest_jobs(self.write_jobs(directory, records))

        self.assertEqual(len(result), 2)
        self.assertEqual(result["title"].tolist(), ["ab", "abc"])


if __name__ == "__main__":
    unittest.main()
