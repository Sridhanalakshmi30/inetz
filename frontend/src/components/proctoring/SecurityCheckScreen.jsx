import React, { useState } from 'react';


function isSupportedBrowser() {
  const ua = navigator.userAgent;
  const isChrome = /Chrome\//.test(ua) && !/Edg\//.test(ua) && !/OPR\//.test(ua);
  const isEdge = /Edg\//.test(ua);
  return isChrome || isEdge;
}

function CheckRow({ label, state, detail }) {
  const icon =
    state === 'ok' ? '✓' : state === 'fail' ? '✕' : state === 'recording' ? '⏺' : '…';

  const cls =
    state === 'ok'
      ? 'proctor-check ok'
      : state === 'fail'
      ? 'proctor-check fail'
      : state === 'recording'
      ? 'proctor-check recording'
      : 'proctor-check pending';

  return (
    <div className={cls}>
      <span className="proctor-check-icon">{icon}</span>
      <div className="proctor-check-content">
        <span className="proctor-check-label">{label}</span>
        {detail && <span className="proctor-check-detail">{detail}</span>}
      </div>
    </div>
  );
}

export default function SecurityCheckScreen({ onStart, mediaError, browserSupported }) {
  const [starting, setStarting] = useState(false);
  const [localError, setLocalError] = useState('');
  const supported = browserSupported ?? isSupportedBrowser();

  async function handleStart() {
    setStarting(true);
    setLocalError('');

    const ok = await onStart();
    if (!ok) {
      setStarting(false);
      setLocalError('Allow camera, microphone, and fullscreen access to start the interview.');
    }
  }

  return (
    <div className="card proctor-security-check">
      <h2>Interview Security Check</h2>

      <p className="hint">
        This interview checks camera and microphone access and requires fullscreen mode.
      </p>

      <div className="proctor-check-list">
        <CheckRow label="Google Chrome or Microsoft Edge" state={supported ? 'ok' : 'fail'} />
        <CheckRow label="Camera &amp; Face Visibility" state="pending" detail="Keep your face visible on screen" />
        <CheckRow label="Microphone Access" state="pending" detail="Ensure clear audio input" />
        <CheckRow label="Fullscreen Mode" state="pending" />
      </div>

      {!supported && <p className="error-text">Please use the latest Chrome or Edge browser.</p>}
      {mediaError && <p className="error-text">{mediaError}</p>}
      {localError && <p className="error-text">{localError}</p>}

      <div style={{ marginTop: '1.5rem' }}>
        <button
          className="primary-btn"
          onClick={handleStart}
          disabled={!supported || starting}
          style={{ width: '100%' }}
        >
          {starting ? 'Starting interview…' : 'Enter Fullscreen & Start Interview'}
        </button>
      </div>


    </div>
  );
}
