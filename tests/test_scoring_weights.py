import unittest
from unittest.mock import patch

from composite_scorer import compute_composite_score


class ScoringWeightsTests(unittest.TestCase):
    def score(self, weights, available=False):
        semantic = {"available": available, "score": 25.0 if available else None, "confidence": "test"}
        with patch("matching_engine.compute_semantic_similarity", return_value=semantic):
            return compute_composite_score(
                "Python engineer", "SQL analyst", ["Python"], ["Python"],
                ats_score=50, weights=weights,
            )

    def test_custom_weights_control_score_with_or_without_semantic_model(self):
        for available in (False, True):
            with self.subTest(available=available):
                weights = {"skill_coverage": 1.0}
                result = self.score(weights, available)
                self.assertEqual(result["overall_match_score"], 100.0)
                self.assertEqual(result["weights_used"], weights)
                self.assertEqual(weights, {"skill_coverage": 1.0})

    def test_invalid_weight_configuration_is_rejected(self):
        for weights in ({}, {"typo": 1.0}, {"skill_coverage": -1.0},
                        {"skill_coverage": 0.3}, {"skill_coverage": float("nan")},
                        {"skill_coverage": True}, {"skill_coverage": "1.0"}):
            with self.subTest(weights=weights), self.assertRaises(ValueError):
                self.score(weights)

    def test_semantic_weight_requires_an_available_model(self):
        with self.assertRaises(ValueError):
            self.score({"semantic_similarity": 1.0})

    def test_semantic_weight_is_honored_when_available(self):
        result = self.score({"semantic_similarity": 1.0}, available=True)
        self.assertEqual(result["overall_match_score"], 25.0)


if __name__ == "__main__":
    unittest.main()
