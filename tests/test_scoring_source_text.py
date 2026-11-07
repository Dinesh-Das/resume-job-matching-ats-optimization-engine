"""Public scoring must retain dates, sentences and resume section boundaries."""
import ast
import logging
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi import FastAPI, Form, HTTPException
from httpx import ASGITransport, AsyncClient

from ats_simulator import extract_experience_years


class ExperienceDateTests(unittest.TestCase):
    def test_month_named_ranges_retain_complete_years(self):
        for text in ("Engineer 2018 - 2023", "Engineer Jan 2018 - Dec 2023"):
            with self.subTest(text=text):
                result = extract_experience_years(text)
                self.assertEqual(result["total_years"], 5)
                self.assertEqual(result["earliest_year"], 2018)
                self.assertEqual(result["latest_year"], 2023)


class QuickMatchSourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_quick_match_passes_original_resume_and_jd_to_composite(self):
        # Load the actual endpoint without optional application startup services.
        source = Path(__file__).resolve().parents[1] / "server.py"
        tree = ast.parse(source.read_text(encoding="utf-8-sig"))
        route = next(node for node in tree.body
                     if isinstance(node, ast.AsyncFunctionDef) and node.name == "quick_match")
        app = FastAPI()
        namespace = {"app": app, "Form": Form, "HTTPException": HTTPException,
                     "logger": logging.getLogger("test"), "log_banner": lambda *a: None,
                     "log_memory": lambda *a: None}
        exec(compile(ast.Module(body=[route], type_ignores=[]), str(source), "exec"), namespace)
        resume = "EXPERIENCE\nSenior Software Engineer\nJan 2018 - Dec 2023\nBuilt Python services."
        jd = "Senior Software Engineer\nAt least 5 years of experience.\nPython required."
        with patch("text_processor._get_nlp", return_value="fallback"), \
             patch("skill_extractor.extract_skills_from_text", return_value=["Python"]), \
             patch("skill_extractor.fuzzy_match_skills", return_value=[]), \
             patch("skill_extractor.infer_skills_from_context", return_value=[]), \
             patch("ats_simulator.compute_ats_parseability_score", return_value={"score": 80, "issues": [], "confidence": 0.8}), \
             patch("ats_simulator.analyze_career_progression", return_value={}), \
             patch("recommendation_engine.generate_general_tips", return_value=[]), \
             patch("composite_scorer.compute_composite_score", return_value={"overall_match_score": 80, "component_scores": {}}) as score:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/quick-match", data={"resume_text": resume, "jd_text": jd})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(score.call_args.kwargs["resume_text"], resume)
        self.assertEqual(score.call_args.kwargs["jd_text"], jd)


if __name__ == "__main__":
    unittest.main()
