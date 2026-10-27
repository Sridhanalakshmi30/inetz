import React, { useRef, useState } from 'react';
import { useProctoring } from '../../hooks/useProctoring.js';
import SecurityCheckScreen from './SecurityCheckScreen.jsx';
import ViolationWarning from './ViolationWarning.jsx';
import ProctoringStatusBadge from './ProctoringStatusBadge.jsx';
import LockdownOverlay from './LockdownOverlay.jsx';

export default function ProctoringGuard({ candidateId, children }) {
  const [checksPassed, setChecksPassed] = useState(false);
  const [sessionId, setSessionId] = useState(null);

  const videoRef = useRef(null);

  const proctoring = useProctoring({
    sessionId,
    videoRef,
  });

  async function handleStart() {
    const ok = await proctoring.runSecurityCheck();

    if (ok) {
      setChecksPassed(true);
    }

    return ok;
  }

  if (!checksPassed) {
    return (
      <>
        <SecurityCheckScreen
          candidateId={candidateId}
          onStart={handleStart}
          mediaError={proctoring.mediaError}
          mediaStream={proctoring.mediaStream}
        />

        <VideoSink
          stream={proctoring.mediaStream}
          videoRef={videoRef}
        />
      </>
    );
  }

  if (proctoring.phase === 'TERMINATED') {
    return (
      <div className="card proctor-terminated" role="alert" aria-live="assertive">
        <h2>INTERVIEW ENDED &mdash; MALPRACTICE</h2>
        <p>{proctoring.terminationReason || 'The interview ended after repeated proctoring violations.'}</p>
        <p>You cannot continue this interview. The reason has been recorded for review.</p>

        <p className="hint">
          Your interview activity and answers up to this point have been saved.
        </p>
      </div>
    );
  }

  const childProctoring = {
    phase: proctoring.phase,

    setQuestionNumber:
      proctoring.setQuestionNumber,

    registerSession:
      setSessionId,

    reportViolation:
      proctoring.reportViolation,

    mediaStream:
      proctoring.mediaStream,
  };


  return (
    <div className="proctor-wrapper">

      <div className="proctor-status-bar">

        <ProctoringStatusBadge
          phase={proctoring.phase}
          violationCount={proctoring.violationCount}
          maxViolations={proctoring.maxViolations}
        />

      </div>

      <VideoSink stream={proctoring.mediaStream} videoRef={videoRef} detection={proctoring.faceDetection} />

      {children(childProctoring)}

      {proctoring.locked && (
        <LockdownOverlay
          reason={proctoring.lockedReason}
          onContinue={() => proctoring.enterFullscreen && proctoring.enterFullscreen()}
          violationCount={proctoring.violationCount}
          maxViolations={proctoring.maxViolations}
        />
      )}

      <ViolationWarning
        violation={proctoring.lastViolation}
        violationCount={proctoring.violationCount}
        maxViolations={proctoring.maxViolations}
        onContinue={proctoring.dismissWarning}
      />


    </div>
  );
}

function VideoSink({ stream, videoRef, detection }) {
  const [playing, setPlaying] = useState(false);

  React.useEffect(() => {

    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
    }

  }, [stream, videoRef]);

  return (
    <section className="camera-preview" aria-label="Your live camera preview">
      <div className="camera-preview-heading">
        <strong>Your camera</strong>
        <span role="status">{playing ? 'Live' : 'Connecting...'}</span>
      </div>
      <div style={{ position: 'relative' }}>
      <video
        ref={videoRef}
        autoPlay
        muted
        playsInline
        onPlaying={() => setPlaying(true)}
        onWaiting={() => setPlaying(false)}
        onEmptied={() => setPlaying(false)}
        aria-label="Live view of your camera"
        style={{ display: 'block', width: '100%', height: 'auto', objectFit: 'contain' }}
      />
      {detection?.boxes.map((box, index) => (
        <div key={index} aria-hidden="true" style={{
          position: 'absolute', pointerEvents: 'none', boxSizing: 'border-box',
          left: `${(1 - box.x - box.width) * 100}%`, top: `${box.y * 100}%`,
          width: `${box.width * 100}%`, height: `${box.height * 100}%`,
          border: `2px solid ${detection.count > 1 ? '#ff4848' : '#00e69b'}`,
        }} />
      ))}
      </div>
      {detection && <p role="status">
        {detection.status === 'active' ? `Faces detected: ${detection.count}` :
          detection.status === 'error' ? 'Face detection unavailable. Check your connection and restart.' :
          'Waiting for face detection...'}
      </p>}
      <p>Keep your face visible and well lit.</p>
    </section>
  );
}
