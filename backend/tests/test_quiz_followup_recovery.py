import unittest

from app.services.tutor_service import _build_retrieval_query, _is_assessment_followup
from app.services.assessment_generation import _has_prior_repeats


class QuizFollowupTests(unittest.TestCase):
    def test_more_quiz_is_followup(self):
        self.assertTrue(_is_assessment_followup("give me few more quiz", "quiz"))

    def test_followup_uses_previous_quiz_as_retrieval_seed(self):
        history = [
            {"role": "user", "content": "Give me some quiz on this chapter"},
            {"role": "assistant", "content": "**Question 1:** What did Rama Natha believe?\nA) Gold\nB) Dew\nC) Rain\nD) Water\n"},
            {"role": "user", "content": "1 A, 2 B, 3 C"},
            {"role": "assistant", "content": "Score: 67%"},
        ]
        query = _build_retrieval_query("give me few more quiz", history, "quiz")
        self.assertIn("Previous chapter quiz", query)
        self.assertIn("Rama Natha", query)

    def test_repetition_is_detected_for_retry_not_permanent_failure(self):
        current = "**Question 1:** What did Rama Natha believe?\nA) Gold\nB) Dew\nC) Rain\nD) Water"
        self.assertTrue(_has_prior_repeats(current, [current]))

    def test_non_assessment_mode_does_not_change_retrieval_query(self):
        self.assertEqual(_build_retrieval_query("explain this", [], "teaching"), "explain this")


if __name__ == "__main__":
    unittest.main()
