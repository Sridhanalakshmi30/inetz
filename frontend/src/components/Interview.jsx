import React, { useEffect, useRef, useState } from 'react';
import { startInterview, submitAnswer, quitInterview } from '../api.js';
import RepeatVoiceCheckModal from './proctoring/RepeatVoiceCheckModal.jsx';


function speak(text) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel(); // stop any previous utterance
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1;
  utterance.pitch = 1;
  window.speechSynthesis.speak(utterance);
}

function formatTime(totalSeconds) {
  const m = Math.floor(totalSeconds / 60).toString().padStart(2, '0');
  const s = Math.floor(totalSeconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

export default function Interview({
  candidateId,
  candidateName,
  onFinished,
  onQuit,
  proctoring,
  roleKey,
}) {
  const [loading, setLoading] = useState(true);
  const [confirmQuit, setConfirmQuit] = useState(false);
  const [quitting, setQuitting] = useState(false);
  const quittingRef = useRef(false);
  const [error, setError] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [turnId, setTurnId] = useState(null);
  const [turnNumber, setTurnNumber] = useState(1);
  const [topic, setTopic] = useState('');
  const [questionText, setQuestionText] = useState('');
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const [typedAnswer, setTypedAnswer] = useState('');
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);
  const [lastTranscript, setLastTranscript] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [clipboardNotice, setClipboardNotice] = useState('');

  // Voice Verification State
  const [showRepeatVoiceCheck, setShowRepeatVoiceCheck] = useState(false);
  const [pendingNextResult, setPendingNextResult] = useState(null);

  const recognitionRef = useRef(null);
  const usedSpeechRef = useRef(false);
  const isSpeakingRef = useRef(false);
  const baseTextRef = useRef('');
  const timerRef = useRef(null);

  // Start the interview once when component mounts
  useEffect(() => {
    (async () => {
      try {
        const result = await startInterview(candidateId, undefined, roleKey);
        setSessionId(result.sessionId);
        setTurnId(result.turnId);
        setTurnNumber(result.turnNumber);
        setTopic(result.topic);
        setQuestionText(result.questionText);
        setRemainingSeconds(result.durationSeconds || result.remainingSeconds);

        if (proctoring && proctoring.registerSession) {
          proctoring.registerSession(result.sessionId);
        }
      } catch (err) {
        setError(err.message || 'Could not start the interview.');
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update proctoring with question turn number
  useEffect(() => {
    if (proctoring && proctoring.setQuestionNumber) {
      proctoring.setQuestionNumber(turnNumber);
    }
  }, [turnNumber, proctoring]);

  // Speak each new question aloud
  useEffect(() => {
    if (questionText) speak(questionText);
  }, [questionText]);

  // Countdown display
  useEffect(() => {
    if (loading || remainingSeconds <= 0) return;
    timerRef.current = setInterval(() => {
      setRemainingSeconds((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timerRef.current);
  }, [loading, sessionId]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      window.speechSynthesis?.cancel();
      isSpeakingRef.current = false;
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          // ignore
        }
        recognitionRef.current = null;
      }

    };
  }, []);

  async function startSpeaking() {
    setError('');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSpeechSupported(false);
      setError('Speech recognition is not supported in this browser. You can type your answer instead.');
      return;
    }

    setSpeechSupported(true);
    baseTextRef.current = typedAnswer ? typedAnswer.trim() + ' ' : '';

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (transcript.trim()) usedSpeechRef.current = true;
        if (event.results[i].isFinal) {
          baseTextRef.current += transcript + ' ';
        } else {
          interim += transcript;
        }
      }
      setTypedAnswer(baseTextRef.current + interim);
    };

    recognition.onerror = (event) => {
      if (event.error === 'not-allowed') {
        setError('Microphone access was denied. Please allow microphone permissions or type your answer.');
        stopSpeaking();
      } else {
        console.warn('Speech recognition error:', event.error);
      }
    };

    recognition.onend = () => {
      if (isSpeakingRef.current) {
        try {
          recognition.start();
        } catch (e) {
          // ignore
        }
      }
    };

    try {
      recognition.start();
      recognitionRef.current = recognition;
      isSpeakingRef.current = true;
      setIsSpeaking(true);
    } catch (err) {
      console.warn('Could not start speech recognition:', err);
      setError('Could not access speech recognition. You can type your answer instead.');
    }
  }

  function stopSpeaking() {
    isSpeakingRef.current = false;
    if (recognitionRef.current) {
      const rec = recognitionRef.current;
      recognitionRef.current = null;
      try {
        rec.stop();
      } catch (e) {
        // ignore
      }
    }



    setIsSpeaking(false);
    setTypedAnswer((prev) => prev.trim());
  }

  // Auto-clear clipboard notice
  useEffect(() => {
    if (!clipboardNotice) return undefined;
    const t = setTimeout(() => setClipboardNotice(''), 4000);
    return () => clearTimeout(t);
  }, [clipboardNotice]);

  function reportGuardEvent(eventType) {
    if (proctoring && proctoring.reportViolation) {
      proctoring.reportViolation(eventType);
    }
  }

  function handleAnswerPaste(e) {
    e.preventDefault();
    reportGuardEvent('PASTE_BLOCKED');
    setClipboardNotice('Pasting is disabled during the interview — please type your answer.');
  }

  function handleQuestionCopy(e) {
    e.preventDefault();
    reportGuardEvent('COPY_BLOCKED');
    setClipboardNotice('Copying the question is disabled during the interview.');
  }

  function proceedWithNextTurn(result) {
    setLastTranscript(result.transcript || typedAnswer);
    setTypedAnswer('');
    baseTextRef.current = '';
    usedSpeechRef.current = false;

    if (result.finished) {
      onFinished(sessionId);
      return;
    }

    setTurnId(result.nextTurn.turnId);
    setTurnNumber(result.nextTurn.turnNumber);
    setTopic(result.nextTurn.topic);
    setQuestionText(result.nextTurn.questionText);
    setRemainingSeconds(result.remainingSeconds);
  }

  async function handleSubmitAnswer() {
    if (quittingRef.current || confirmQuit) return;
    if (isSpeakingRef.current) {
      stopSpeaking();
    }

    const answer = typedAnswer.trim();
    if (!answer) {
      setError('Please type an answer or speak before submitting.');
      return;
    }

    setSubmitting(true);
    setError('');
    try {
      const result = await submitAnswer(sessionId, turnId, {
        answerText: answer,
        answerSource: usedSpeechRef.current ? 'voice' : 'typed',
      });

      // If voice comparison flagged a mismatch on spoken audio:
      if (result.voiceMismatch) {
        setPendingNextResult(result);
        setShowRepeatVoiceCheck(true);
        return;
      }

      proceedWithNextTurn(result);
    } catch (err) {
      setError(err.message || 'Failed to submit your answer. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleQuit() {
    if (quittingRef.current || submitting) return;
    quittingRef.current = true;
    setQuitting(true);
    setError('');
    stopSpeaking();
    window.speechSynthesis?.cancel();
    try {
      await quitInterview(sessionId);
      onQuit();
      if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    } catch (err) {
      setError(err.message || 'Could not end the interview. Please try again.');
      quittingRef.current = false;
      setQuitting(false);
    }
  }

  function handleRepeatCheckVerified() {
    setShowRepeatVoiceCheck(false);
    if (pendingNextResult) {
      proceedWithNextTurn(pendingNextResult);
      setPendingNextResult(null);
    }
  }

  function handleRepeatCheckMismatch() {
    setShowRepeatVoiceCheck(false);
    if (pendingNextResult) proceedWithNextTurn(pendingNextResult);
    setPendingNextResult(null);
  }

  if (loading) {
    return (
      <div className="card">
        <h2>Preparing your interview…</h2>
        <p className="hint">
          The AI is reading your resume and planning questions about your skills, internships, and projects.
        </p>
      </div>
    );
  }

  if (error && !sessionId) {
    return (
      <div className="card">
        <p className="error-text">{error}</p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="interview-top">
        <span className="badge">
          {roleKey?.startsWith('fresher:') ? 'Type 3: Fresher Role-Based' : roleKey ? 'Type 2: Experienced Role-Based' : 'Type 1: Resume-Based'}
        </span>
        <span className="badge">Question {turnNumber} of 15</span>
        <span className="badge topic-badge">{topic}</span>
        <span className="timer">⏱ {formatTime(remainingSeconds)}</span>
      </div>

      <h2
        className="question-text no-select"
        onCopy={handleQuestionCopy}
        onCut={handleQuestionCopy}
        onContextMenu={handleQuestionCopy}
      >
        {questionText}
      </h2>
      <button className="secondary-btn small" onClick={() => speak(questionText)}>
        🔊 Replay question
      </button>

      {clipboardNotice && <p className="clipboard-notice">{clipboardNotice}</p>}

      {lastTranscript && (
        <div
          className="transcript-preview no-select"
          onCopy={handleQuestionCopy}
          onCut={handleQuestionCopy}
          onContextMenu={handleQuestionCopy}
        >
          <strong>Your last answer:</strong> {lastTranscript}
        </div>
      )}

      <div className="answer-section">
        <label htmlFor="answer">Type or speak your answer</label>
        <textarea
          id="answer"
          rows={4}
          className={isSpeaking ? 'listening' : ''}
          value={typedAnswer}
          onChange={(e) => {
            setTypedAnswer(e.target.value);
            baseTextRef.current = e.target.value;
          }}
          placeholder="Type here, or click Speak answer below…"
          disabled={submitting}
          onPaste={handleAnswerPaste}
        />

        <div className="voice-controls">
          {!isSpeaking ? (
            <button
              type="button"
              className="secondary-btn"
              onClick={startSpeaking}
              disabled={submitting}
            >
              🎤 Speak answer
            </button>
          ) : (
            <button type="button" className="secondary-btn recording" onClick={stopSpeaking}>
              ⏹ Stop speaking
            </button>
          )}
        </div>

        {error && <p className="error-text">{error}</p>}

        <button
          className="primary-btn"
          onClick={handleSubmitAnswer}
          disabled={submitting}
        >
          {submitting ? 'Submitting…' : 'Submit Answer'}
        </button>
        <button type="button" className="secondary-btn quit-interview-btn" disabled={submitting || quitting}
          onClick={() => { stopSpeaking(); setConfirmQuit(true); }}>
          Quit interview
        </button>
      </div>

      {showRepeatVoiceCheck && (
        <RepeatVoiceCheckModal
          sessionId={sessionId}
          questionNumber={turnNumber}
          mediaStream={proctoring?.mediaStream}
          onVerified={handleRepeatCheckVerified}
          onMismatchPersists={handleRepeatCheckMismatch}
        />
      )}
      {confirmQuit && (
        <div className="proctor-modal-overlay quit-confirmation" role="dialog" aria-modal="true" aria-labelledby="quit-title">
          <div className="proctor-modal">
            <h3 id="quit-title">Quit this interview?</h3>
            <p>Your submitted answers will be kept. Your current unfinished answer will be discarded, and ending the interview cannot be undone.</p>
            {error && <p className="error-text" role="alert">{error}</p>}
            <button type="button" className="secondary-btn" disabled={quitting} onClick={() => setConfirmQuit(false)} autoFocus>Continue interview</button>
            <button type="button" className="primary-btn" disabled={quitting} onClick={handleQuit}>
              {quitting ? 'Ending interview...' : 'Quit interview'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
