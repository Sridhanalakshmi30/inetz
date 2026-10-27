import unittest
from unittest.mock import patch
from types import SimpleNamespace

from fastapi.testclient import TestClient
import httpx
from groq import RateLimitError
from main import app
from data.role_profiles import list_roles, get_role_profile
from routers.interview import StartInterviewRequest, start_interview
from routers.resume import create_role_candidate
from services.groq_service import MODEL_SMALL, _call_groq_json, generate_interview_plan, generate_next_question
from fastapi import HTTPException


class RoleInterviewTests(unittest.TestCase):
    @patch('services.groq_service.time.sleep')
    @patch('services.groq_service.get_client')
    def test_rate_limit_retries_once(self, get_client, sleep):
        response = httpx.Response(429, request=httpx.Request('POST', 'https://api.groq.com'))
        completion = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))])
        create = get_client.return_value.chat.completions.create
        create.side_effect = [RateLimitError('limited', response=response, body={}), completion]
        self.assertEqual(_call_groq_json('model', 'system', 'user'), {'ok': True})
        sleep.assert_called_once_with(2)
        self.assertEqual(create.call_count, 2)

    @patch('routers.resume.get_connection')
    def test_role_candidate_needs_no_resume(self, connect):
        cursor = connect.return_value.cursor.return_value
        cursor.lastrowid = 42
        with patch('routers.resume.issue_token', return_value='candidate-token'):
            result = create_role_candidate()
        self.assertEqual(result, {'candidateId': 42, 'accessToken': 'candidate-token'})
        self.assertEqual(cursor.execute.call_args.args[1], ('Candidate', '{}'))
        connect.return_value.commit.assert_called_once()

    def test_catalog_is_available_without_candidate_credentials(self):
        response = TestClient(app).get('/api/interview/roles')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['roles']), 9)
        self.assertNotIn('fresher', [role['key'] for role in response.json()['roles']])

    @patch('services.groq_service._call_groq_json')
    def test_fresher_plan_is_easy_and_contains_fundamentals(self, call):
        call.return_value = {
            'topics': [{'name': 'Invented project', 'type': 'project'}],
            'difficulty_start': 'hard',
        }
        profile = get_role_profile('fresher:python-full-stack')
        plan = generate_interview_plan({}, 15, profile)
        self.assertEqual(plan['difficulty_start'], 'easy')
        self.assertEqual(plan['level'], 'fresher')
        self.assertEqual(plan['role'], 'Fresher Python Full Stack')
        self.assertIn('Python fundamentals and OOP', [topic['name'] for topic in plan['topics']])
        self.assertNotIn('Invented project', [topic['name'] for topic in plan['topics']])
        call.assert_not_called()

    @patch('services.groq_service._call_groq_json')
    def test_questions_use_small_model_and_recent_history(self, call):
        call.return_value = {'question_text': 'Next?', 'topic': 'Python'}
        history = [{'answer_text': f'answer-{index}'} for index in range(5)]
        generate_next_question({}, {'topics': []}, history, 'Python')
        self.assertEqual(call.call_args.kwargs['model'], MODEL_SMALL)
        prompt = call.call_args.kwargs['user_prompt']
        self.assertNotIn('answer-0', prompt)
        self.assertIn('answer-4', prompt)

    @patch('routers.interview.generate_interview_plan')
    @patch('routers.interview.get_candidate_resume')
    def test_unknown_role_rejected_before_database_or_ai(self, resume, generate):
        with self.assertRaises(HTTPException) as error:
            start_interview(StartInterviewRequest(candidateId=1, roleKey='unknown'))
        self.assertEqual(error.exception.status_code, 400)
        resume.assert_not_called()
        generate.assert_not_called()

    @patch('services.groq_service._call_groq_json')
    def test_all_roles_keep_fundamentals_when_model_omits_them(self, call):
        for role in list_roles():
            with self.subTest(role=role['key']):
                call.return_value = {'topics': [], 'difficulty_start': 'easy'}
                profile = get_role_profile(role['key'])
                plan = generate_interview_plan({}, 15, profile)
                self.assertEqual([t['name'] for t in plan['topics']], profile['core_topics'])
                self.assertTrue(all(t['type'] == 'technical_skill' for t in plan['topics']))
                self.assertEqual(plan['role'], role['label'])
                self.assertEqual(plan['level'], 'intermediate')
                self.assertEqual(plan['difficulty_start'], 'medium')
        call.assert_not_called()

    @patch('services.groq_service._call_groq_json')
    def test_resume_only_plan_still_supported(self, call):
        call.return_value = {'topics': [{'name': 'Python', 'type': 'technical_skill'}]}
        self.assertEqual(generate_interview_plan({}, 15), call.return_value)


if __name__ == '__main__':
    unittest.main()
