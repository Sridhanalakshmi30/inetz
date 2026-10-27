import unittest
from unittest.mock import MagicMock, patch

from services.violation_service import evaluate_event
from services import proctoring_service


class ProctoringTests(unittest.TestCase):
    @patch('services.violation_service.MULTI_FACE_TERMINATE_AT', 2)
    def test_multiple_faces_warn_then_terminate_independently(self):
        first = evaluate_event('MULTIPLE_FACES_DETECTED', 0, 4)
        self.assertEqual(first['action'], 'FINAL_WARN')
        second = evaluate_event('MULTIPLE_FACES_DETECTED', 1, 4, previous_multiple_face_events=1)
        self.assertEqual(second['action'], 'TERMINATE')
        self.assertTrue(second['paused_reason'].startswith('MALPRACTICE:'))
        self.assertEqual(second['new_violation_count'], 2)
        # A first face occurrence still receives its warning at the shared limit.
        self.assertEqual(evaluate_event('MULTIPLE_FACES_DETECTED', 3, 4)['action'], 'FINAL_WARN')

    def test_no_face_stays_informational(self):
        self.assertEqual(evaluate_event('NO_FACE_DETECTED', 1, 4)['violation_increment'], 0)

    @patch('services.violation_service.MULTI_FACE_TERMINATE_AT', 2)
    @patch('services.proctoring_service.get_connection')
    def test_multiple_face_count_is_read_under_lock_and_reason_saved(self, get_connection):
        conn = get_connection.return_value
        cursor = conn.cursor.return_value
        cursor.fetchone.side_effect = [
            {'status': 'WARNING', 'violation_count': 1, 'max_violations': 4},
            {'count': 1},
        ]
        result = proctoring_service.record_event(1, 'multiple_faces_detected')
        self.assertEqual(result['action'], 'TERMINATE')
        self.assertTrue(result['termination_reason'].startswith('MALPRACTICE:'))
        calls = cursor.execute.call_args_list
        self.assertIn('FOR UPDATE', calls[0].args[0])
        self.assertIn("severity IN ('WARNING', 'TERMINATE')", calls[1].args[0])
        self.assertEqual(calls[3].args[1][2], result['termination_reason'])
        conn.commit.assert_called_once()

    def test_third_departure_terminates(self):
        count = 0
        for event, action in zip(
            ['FULLSCREEN_EXIT', 'TAB_SWITCH', 'FULLSCREEN_EXIT'],
            ['WARN', 'FINAL_WARN', 'TERMINATE'],
        ):
            result = evaluate_event(event, count, 3)
            self.assertEqual(result['action'], action)
            count = result['new_violation_count']
        self.assertEqual(count, 3)
        self.assertEqual(result['new_status'], 'TERMINATED')

    def test_media_loss_warns_without_pausing_or_consuming_violation(self):
        result = evaluate_event('CAMERA_DISABLED', 2, 3)
        self.assertEqual(result['action'], 'WARN')
        self.assertEqual(result['new_status'], 'WARNING')
        self.assertEqual(result['new_violation_count'], 2)

    @patch('services.proctoring_service.get_connection')
    def test_third_event_locks_count_and_abandons_session(self, get_connection):
        conn = get_connection.return_value
        cursor = conn.cursor.return_value
        cursor.fetchone.return_value = {
            'status': 'WARNING', 'violation_count': 2, 'max_violations': 3,
        }
        result = proctoring_service.record_event(1, 'TAB_SWITCH')
        self.assertEqual(result['action'], 'TERMINATE')
        statements = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertIn('FOR UPDATE', statements[0])
        self.assertTrue(any("status = 'abandoned'" in sql for sql in statements))
        conn.commit.assert_called_once()

    @patch('services.proctoring_service.get_connection')
    def test_late_focus_event_cannot_revive_terminated_session(self, get_connection):
        cursor = get_connection.return_value.cursor.return_value
        cursor.fetchone.return_value = {
            'status': 'TERMINATED', 'violation_count': 3, 'max_violations': 3,
        }
        result = proctoring_service.record_event(1, 'WINDOW_FOCUS_RETURN')
        self.assertEqual(result['action'], 'TERMINATE')
        self.assertEqual(result['violation_count'], 3)
        self.assertEqual(cursor.execute.call_count, 1)


if __name__ == '__main__':
    unittest.main()
