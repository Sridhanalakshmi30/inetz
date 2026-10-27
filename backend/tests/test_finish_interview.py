import unittest
from unittest.mock import patch
from fastapi import HTTPException
from routers.interview import finish_interview


class FinishInterviewTests(unittest.TestCase):
    @patch('routers.interview.voice_verification_service.clear_voice_embeddings')
    @patch('routers.interview.get_connection')
    def test_finish_and_retry(self, connect, clear):
        for status in ('in_progress', 'completed'):
            conn = connect.return_value
            cursor = conn.cursor.return_value
            cursor.fetchone.side_effect = [
                {'candidate_id': 4, 'status': status}, {'status': 'ACTIVE'}, {'count': 15},
            ]
            self.assertTrue(finish_interview(12)['finished'])
            sql = cursor.execute.call_args_list[-2].args[0]
            self.assertIn("status = 'completed'", sql)
            self.assertIn("status = 'in_progress'", sql)
            clear.assert_called_with(key='12', candidate_id=4)

    @patch('routers.interview.get_connection')
    def test_invalid_sessions_and_empty_interviews(self, connect):
        scenarios = [
            ([None], 404),
            ([{'candidate_id': 4, 'status': 'abandoned'}], 409),
            ([{'candidate_id': 4, 'status': 'in_progress'}, {'status': 'TERMINATED'}], 409),
            ([{'candidate_id': 4, 'status': 'in_progress'}, {'status': 'ACTIVE'}, {'count': 14}], 400),
        ]
        for rows, expected in scenarios:
            conn = connect.return_value
            conn.reset_mock()
            conn.cursor.return_value.fetchone.side_effect = rows
            with self.assertRaises(HTTPException) as error:
                finish_interview(12)
            self.assertEqual(error.exception.status_code, expected)
            conn.commit.assert_not_called()
            conn.rollback.assert_called_once()


if __name__ == '__main__':
    unittest.main()
