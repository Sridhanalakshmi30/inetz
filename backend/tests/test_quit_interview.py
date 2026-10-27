import unittest
from unittest.mock import patch

from fastapi import HTTPException
from routers.interview import quit_interview


class QuitInterviewTests(unittest.TestCase):
    @patch('routers.interview.voice_verification_service.clear_voice_embeddings')
    @patch('routers.interview.get_connection')
    def test_quit_preserves_answers_and_clears_biometrics(self, connect, clear):
        conn = connect.return_value
        cursor = conn.cursor.return_value
        cursor.fetchone.return_value = {'candidate_id': 4, 'status': 'in_progress'}
        self.assertEqual(quit_interview(12)['status'], 'abandoned')
        statements = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertIn('FOR UPDATE', statements[0])
        self.assertIn("status = 'abandoned'", statements[1])
        self.assertIn("status != 'TERMINATED'", statements[2])
        self.assertFalse(any('interview_turns' in sql for sql in statements))
        conn.commit.assert_called_once()
        clear.assert_called_once_with(key='12', candidate_id=4)
        conn.close.assert_called_once()

    @patch('routers.interview.get_connection')
    def test_missing_session_rolls_back(self, connect):
        conn = connect.return_value
        conn.cursor.return_value.fetchone.return_value = None
        with self.assertRaises(HTTPException) as error:
            quit_interview(999)
        self.assertEqual(error.exception.status_code, 404)
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    @patch('routers.interview.voice_verification_service.clear_voice_embeddings')
    @patch('routers.interview.get_connection')
    def test_repeated_quit_and_completed_sessions(self, connect, clear):
        cursor = connect.return_value.cursor.return_value
        for status in ('abandoned', 'completed'):
            cursor.fetchone.return_value = {'candidate_id': 4, 'status': status}
            self.assertEqual(quit_interview(12)['status'], status)
            self.assertIn("status = 'in_progress'", cursor.execute.call_args_list[-2].args[0])


if __name__ == '__main__':
    unittest.main()
