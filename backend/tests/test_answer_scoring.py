import unittest
from unittest.mock import patch

from services.groq_service import evaluate_answer_and_decide, generate_final_report


class AnswerScoringTests(unittest.TestCase):
    @patch('services.groq_service._call_groq_json')
    def test_exact_weighting(self, call):
        call.return_value = {
            'technical_score': 4, 'depth_score': 2, 'relevance_score': 6,
            'keyword_match_score': 8, 'rationale': 'Covers the main concepts.',
            'adaptive_decision': 'follow_up',
        }
        result = evaluate_answer_and_decide('What is a database index?', 'An index speeds up lookup.', {})
        self.assertEqual(result['technical_score'], 6.8)
        self.assertEqual(result['depth_score'], 6.2)
        self.assertEqual(result['relevance_score'], 7.4)
        self.assertIn('medium, balanced interview rubric', call.call_args.kwargs['system_prompt'])
        self.assertIn('medium rubric', result['rationale'])

    @patch('services.groq_service._call_groq_json')
    def test_empty_answer_receives_zero_without_model_call(self, call):
        result = evaluate_answer_and_decide('Question', '  ', {})
        self.assertEqual(result['technical_score'], 0)
        call.assert_not_called()

    @patch('services.groq_service._call_groq_json')
    def test_invalid_model_scores_are_rejected(self, call):
        for value in (float('nan'), float('inf'), -1, 11):
            call.return_value = {'keyword_match_score': value}
            with self.subTest(value=value), self.assertRaises(ValueError):
                evaluate_answer_and_decide('Question', 'Answer', {})

    @patch('services.groq_service._call_groq_json')
    def test_report_preserves_stored_weighted_scores(self, call):
        call.return_value = {'overall_score': 2, 'skill_scores': {}}
        turns = [
            {'technical_score': 6.8, 'depth_score': 6.2, 'relevance_score': 7.4},
            {'technical_score': 8.8, 'depth_score': 8.2, 'relevance_score': 9.4},
        ]
        result = generate_final_report({}, turns)
        self.assertEqual(result['overall_score'], 7.8)
        self.assertEqual(result['skill_scores'], {
            'technical_knowledge': 7.8, 'problem_depth': 7.2, 'communication_relevance': 8.4,
        })


if __name__ == '__main__':
    unittest.main()
