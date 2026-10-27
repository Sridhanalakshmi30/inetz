import io
import unittest
import numpy as np
import soundfile as sf

from services import voice_verification_service
from services.violation_service import evaluate_event


def create_mock_wav(duration_sec=1.0, freq=440.0, sample_rate=16000):
    t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
    # Sine wave with harmonics
    waveform = (
        0.6 * np.sin(2 * np.pi * freq * t)
        + 0.3 * np.sin(2 * np.pi * freq * 2 * t)
        + 0.1 * np.sin(2 * np.pi * freq * 3 * t)
    ).astype(np.float32)

    buf = io.BytesIO()
    sf.write(buf, waveform, sample_rate, format="WAV")
    return buf.getvalue()


class VoiceVerificationTests(unittest.TestCase):
    def setUp(self):
        voice_verification_service.clear_voice_embeddings("test_cand_1")
        voice_verification_service.clear_voice_embeddings("test_cand_2")

    def test_voice_embedding_extraction_and_matching(self):
        audio_voice_a1 = create_mock_wav(duration_sec=2.0, freq=220.0)
        audio_voice_a2 = create_mock_wav(duration_sec=2.0, freq=225.0)  # similar pitch/formants
        audio_voice_b = create_mock_wav(duration_sec=2.0, freq=880.0)   # very different pitch/voice

        # Register baseline for voice A
        res = voice_verification_service.register_baseline_embedding("test_cand_1", audio_voice_a1)
        self.assertTrue(res["success"])
        self.assertEqual(res["dimensions"], 192)

        # Verify same/similar speaker
        verify_same = voice_verification_service.verify_voice("test_cand_1", audio_voice_a2, threshold=0.90)
        self.assertTrue(verify_same["match"])
        self.assertEqual(verify_same["status"], "MATCH")

        # Verify different speaker
        verify_diff = voice_verification_service.verify_voice("test_cand_1", audio_voice_b, threshold=0.90)
        self.assertFalse(verify_diff["match"])
        self.assertEqual(verify_diff["status"], "MISMATCH")
        self.assertGreater(verify_same["similarity"], verify_diff["similarity"])


    def test_ephemeral_storage_and_cleanup(self):
        audio = create_mock_wav(duration_sec=1.5, freq=300.0)
        voice_verification_service.register_baseline_embedding("test_cand_2", audio)
        self.assertIsNotNone(voice_verification_service.get_baseline_embedding("test_cand_2"))

        # Clear embedding
        voice_verification_service.clear_voice_embeddings("test_cand_2")
        self.assertIsNone(voice_verification_service.get_baseline_embedding("test_cand_2"))

    def test_voice_mismatch_policy_flags_without_pausing_or_terminating(self):
        result = evaluate_event("VOICE_MISMATCH", current_violation_count=2, max_violations=4)
        self.assertEqual(result["action"], "WARN")
        self.assertEqual(result["new_status"], "WARNING")
        self.assertIsNone(result["paused_reason"])
        # Ensure no violation count was incremented (human review, not auto-reject)
        self.assertEqual(result["violation_increment"], 0)
        self.assertEqual(result["new_violation_count"], 2)


if __name__ == "__main__":
    unittest.main()
