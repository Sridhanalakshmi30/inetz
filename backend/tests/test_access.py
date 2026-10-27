import hashlib
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from services.access_service import issue_token


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_every_private_route_rejects_missing_token(self):
        requests = [
            ('POST', '/api/interview/consent', {'candidateId': 1}),
            ('POST', '/api/interview/start', {'candidateId': 1}),
            ('GET', '/api/interview/1/report', None),
            ('POST', '/api/interview/1/quit', None),
            ('POST', '/api/interview/1/finish', None),
            ('POST', '/api/interview/1/next-question', None),
            ('POST', '/api/interview/proctoring/start', {'session_id': 1}),
            ('POST', '/api/interview/proctoring/event', {'session_id': 1, 'event_type': 'TAB_SWITCH'}),
            ('GET', '/api/interview/proctoring/status/1', None),
            ('POST', '/api/interview/proctoring/terminate/1', None),
            ('GET', '/api/interview/proctoring/summary/1', None),
        ]
        for method, url, body in requests:
            with self.subTest(url=url):
                self.assertEqual(self.client.request(method, url, json=body).status_code, 401)
        self.assertEqual(self.client.post('/api/interview/1/answer', data={'turnId': 1, 'answerText': 'Text'}).status_code, 401)

    @patch('services.access_service.get_connection')
    def test_wrong_session_token_denied(self, connect):
        cursor = connect.return_value.cursor.return_value
        cursor.fetchone.return_value = {'token_hash': hashlib.sha256(b'owner-token').hexdigest()}
        result = self.client.get('/api/interview/2/report', headers={'Authorization': 'Bearer someone-elses-token'})
        self.assertEqual(result.status_code, 403)
        self.assertEqual(cursor.execute.call_args.args[1], ('session', 2))

    @patch('routers.interview.get_connection')
    @patch('services.access_service.get_connection')
    def test_valid_token_allows_report(self, auth_connect, route_connect):
        auth_connect.return_value.cursor.return_value.fetchone.return_value = {'token_hash': hashlib.sha256(b'valid-token').hexdigest()}
        route_connect.return_value.cursor.return_value.fetchone.return_value = {'skill_scores': {}, 'strengths': [], 'weaknesses': [], 'overall_score': 8}
        result = self.client.get('/api/interview/2/report', headers={'Authorization': 'Bearer valid-token'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['overall_score'], 8)

    @patch('services.access_service.get_connection')
    def test_candidate_scope_is_separate(self, connect):
        connect.return_value.cursor.return_value.fetchone.return_value = None
        result = self.client.post('/api/interview/start', json={'candidateId': 9}, headers={'Authorization': 'Bearer session-token'})
        self.assertEqual(result.status_code, 403)
        self.assertEqual(connect.return_value.cursor.return_value.execute.call_args.args[1], ('candidate', 9))

    def test_voice_routes_retired(self):
        for path in ('baseline', 'verify', 'repeat-check', 'clear'):
            self.assertEqual(self.client.post('/api/interview/voice/' + path).status_code, 410)

    def test_only_hash_is_stored(self):
        cursor = MagicMock()
        first = issue_token(cursor, 'session', 1)
        stored = cursor.execute.call_args.args[1][2]
        self.assertNotEqual(first, stored)
        self.assertEqual(stored, hashlib.sha256(first.encode()).hexdigest())
        self.assertNotEqual(first, issue_token(cursor, 'session', 2))


if __name__ == '__main__':
    unittest.main()
