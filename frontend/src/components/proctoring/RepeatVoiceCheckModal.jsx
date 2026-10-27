import React, { useState, useRef, useEffect } from 'react';
import { submitRepeatVoiceCheck } from '../../api.js';
import { convertToMono16kWavBlob } from '../../utils/audioUtils.js';


function getSupportedAudioMimeType() {
  const types = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/ogg',
    'audio/mp4',
    'audio/aac',
  ];
  if (typeof MediaRecorder === 'undefined' || !MediaRecorder.isTypeSupported) {
    return '';
  }
  for (const t of types) {
    if (MediaRecorder.isTypeSupported(t)) {
      return t;
    }
  }
  return '';
}

const REPEAT_PHRASES = [
  '“Technical verification: I confirm that I am speaking my answers clearly into the microphone.”',
  '“Security check: I am completing this technical interview in a quiet and private space.”',
  '“Voice authentication: My camera is active and this is my authentic spoken voice.”',
];

export default function RepeatVoiceCheckModal({
  sessionId,
  questionNumber,
  mediaStream,
  onVerified,
  onMismatchPersists,
}) {
  const [phraseIndex] = useState(() => Math.floor(Math.random() * REPEAT_PHRASES.length));
  const [recording, setRecording] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [countdown, setCountdown] = useState(5);
  const [error, setError] = useState('');

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const countdownIntervalRef = useRef(null);
  const localStreamRef = useRef(null);

  const selectedPhrase = REPEAT_PHRASES[phraseIndex];

  useEffect(() => {
    return () => {
      if (countdownIntervalRef.current) clearInterval(countdownIntervalRef.current);
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
        try {
          mediaRecorderRef.current.stop();
        } catch (e) {
          // ignore
        }
      }
      if (localStreamRef.current) {
        try {
          localStreamRef.current.getTracks().forEach((t) => t.stop());
        } catch (e) {
          // ignore
        }
      }
    };
  }, []);

  async function handleStartRecord() {
    setError('');
    audioChunksRef.current = [];

    let activeStream = mediaStream;
    let audioTracks = activeStream ? activeStream.getAudioTracks() : [];

    if (!audioTracks.length) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        localStreamRef.current = stream;
        activeStream = stream;
        audioTracks = stream.getAudioTracks();
      } catch (err) {
        setError('Microphone access unavailable. Please enable microphone permissions in your browser.');
        return;
      }
    }

    if (!audioTracks.length) {
      setError('No active microphone found.');
      return;
    }

    try {
      const audioOnlyStream = new MediaStream(audioTracks);
      const mimeType = getSupportedAudioMimeType();
      const recorderOptions = mimeType ? { mimeType } : undefined;

      const recorder = new MediaRecorder(audioOnlyStream, recorderOptions);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        const rawBlob = new Blob(audioChunksRef.current, {
          type: recorder.mimeType || 'audio/webm',
        });

        if (rawBlob.size < 100) {
          setError('Audio was too short. Please speak clearly and try again.');
          setSubmitting(false);
          setRecording(false);
          return;
        }

        setSubmitting(true);
        try {
          const wavBlob = await convertToMono16kWavBlob(rawBlob);
          const result = await submitRepeatVoiceCheck(sessionId, wavBlob, questionNumber);
          if (result.match) {
            onVerified();
          } else {
            // Mismatch persists: pause and flag for human review
            onMismatchPersists(result);
          }
        } catch (err) {
          setError(err.message || 'Verification request failed. Please try again.');
        } finally {
          setSubmitting(false);
          setRecording(false);
        }
      };


      recorder.start(250);
      setRecording(true);
      setCountdown(5);

      let timeLeft = 5;
      countdownIntervalRef.current = setInterval(() => {
        timeLeft -= 1;
        setCountdown(timeLeft);
        if (timeLeft <= 0) {
          clearInterval(countdownIntervalRef.current);
          if (recorder.state === 'recording') {
            recorder.stop();
          }
        }
      }, 1000);
    } catch (err) {
      console.warn('Repeat voice check start error:', err);
      setError(`Microphone error: ${err.message || 'Could not start recording.'}`);
    }
  }

  return (
    <div className="proctor-modal-overlay" role="dialog" aria-modal="true" aria-labelledby="repeat-voice-title">
      <div className="proctor-modal" style={{ maxWidth: '520px' }}>
        <h3 id="repeat-voice-title" style={{ color: '#d97706' }}>
          🎙️ Repeat Voice Check Required
        </h3>

        <p className="hint">
          A voice similarity mismatch was detected. To verify that you are the same candidate who completed
          the security check, please read this short phrase aloud:
        </p>

        <blockquote className="baseline-quote" style={{ margin: '1rem 0', fontSize: '1.05rem' }}>
          {selectedPhrase}
        </blockquote>

        {recording && (
          <div className="voice-progress-container" style={{ margin: '1rem 0' }}>
            <span className="voice-progress-timer" style={{ color: '#d97706', fontWeight: 700 }}>
              🔴 Recording repeat check: {countdown}s remaining...
            </span>
          </div>
        )}

        {submitting && (
          <p className="hint" style={{ fontWeight: 600, color: '#3454d1' }}>
            Comparing voice embedding against baseline…
          </p>
        )}

        {error && <p className="error-text">{error}</p>}

        <div style={{ marginTop: '1.25rem', display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
          {!recording && !submitting ? (
            <button type="button" className="primary-btn" onClick={handleStartRecord}>
              🎤 Read Phrase &amp; Verify (5s)
            </button>
          ) : recording ? (
            <button
              type="button"
              className="secondary-btn recording"
              onClick={() => {
                if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
                  mediaRecorderRef.current.stop();
                }
              }}
            >
              ⏹ Finish Recording
            </button>
          ) : (
            <button type="button" className="primary-btn" disabled>
              Verifying…
            </button>
          )}
        </div>

        <p className="hint" style={{ fontSize: '0.8rem', marginTop: '1rem' }}>
          If the mismatch persists, it will be flagged for human review and the interview will continue.
          No automatic rejection or penalty will be applied.
        </p>
      </div>
    </div>
  );
}
