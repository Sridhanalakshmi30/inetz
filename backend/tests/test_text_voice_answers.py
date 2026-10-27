import io
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi import HTTPException, UploadFile
from routers import interview


class TextVoiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_expired_timer_still_generates_question_fifteen(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(interview, 'get_session', return_value={
                'status': 'in_progress', 'candidate_id': 1,
                'started_at': datetime.now() - timedelta(hours=1),
                'duration_minutes': 15, 'question_count': 14,
                'interview_plan': {'topics': [{'name': 'OOP', 'type': 'technical_skill'}]},
                'current_topic_index': 0,
            }))
            stack.enter_context(patch.object(interview, 'get_candidate_resume', return_value={}))
            connection = stack.enter_context(patch.object(interview, 'get_connection')).return_value
            cursor = connection.cursor.return_value
            cursor.fetchone.return_value = {'question_text': 'What is inheritance?'}
            cursor.fetchall.return_value = []
            cursor.lastrowid = 15
            stack.enter_context(patch.object(interview, 'evaluate_answer_and_decide', return_value={
                'technical_score': 8, 'depth_score': 8, 'relevance_score': 8,
                'rationale': 'Correct.', 'adaptive_decision': 'new_topic',
            }))
            stack.enter_context(patch.object(interview.proctoring_service, 'is_active', return_value=True))
            stack.enter_context(patch.object(interview, 'pick_next_topic', return_value={'name': 'OOP', 'index': 0}))
            stack.enter_context(patch.object(interview, 'generate_next_question', return_value={
                'question_text': 'Name the four pillars of OOP.',
            }))
            result = await interview.submit_answer(1, 14, 'It allows reuse.', 'typed', None)
        self.assertFalse(result['finished'])
        self.assertEqual(result['nextTurn']['turnNumber'], 15)
        self.assertEqual(result['remainingSeconds'], 0)

    async def test_disabled_audio_is_rejected_before_processing(self):
        audio = UploadFile(filename='answer.wav', file=io.BytesIO(b'audio'))
        with patch.object(interview, 'VOICE_CHECK_ENABLED', False), patch.object(interview, 'get_session') as session:
            with self.assertRaises(HTTPException) as error:
                await interview.submit_answer(1, 2, 'Transcript', 'voice', audio)
            self.assertEqual(error.exception.status_code, 400)
            session.assert_not_called()
            self.assertTrue(audio.file.closed)

    async def test_transcript_saved_once_with_selected_source(self):
        for source in ('voice', 'typed'):
            with ExitStack() as stack:
                stack.enter_context(patch.object(interview, 'get_session', return_value={
                    'status': 'in_progress', 'candidate_id': 1, 'started_at': datetime.now(),
                    'duration_minutes': 15, 'question_count': interview.MAX_QUESTIONS,
                }))
                stack.enter_context(patch.object(interview, 'get_candidate_resume', return_value={}))
                connection = stack.enter_context(patch.object(interview, 'get_connection')).return_value
                cursor = connection.cursor.return_value
                cursor.fetchone.return_value = {'question_text': 'Explain indexing.'}
                cursor.rowcount = 1
                stack.enter_context(patch.object(interview, 'evaluate_answer_and_decide', return_value={
                    'technical_score': 8, 'depth_score': 8, 'relevance_score': 8,
                    'rationale': 'Correct.', 'adaptive_decision': 'new_topic',
                }))
                stack.enter_context(patch.object(interview.proctoring_service, 'mark_completed'))
                transcribe = stack.enter_context(patch.object(interview, 'transcribe_audio'))
                result = await interview.submit_answer(1, 2, 'An index speeds lookup.', source, None)
                self.assertTrue(result['finished'])
                saved = cursor.execute.call_args_list[1].args[1]
                self.assertEqual(saved[:2], ('An index speeds lookup.', source))
                transcribe.assert_not_called()


if __name__ == '__main__':
    unittest.main()
