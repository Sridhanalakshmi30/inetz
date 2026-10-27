import React from 'react';

/**
 * Rendered by ProctoringGuard whenever proctoring.locked is true — i.e. the
 * instant the browser window loses OS focus or drops out of fullscreen
 * (Start Menu, Alt+Tab to another app, a second monitor, etc).
 *
 * This is a purely client-side, instant reaction (no server round-trip),
 * so the question/answer are hidden immediately rather than staying
 * visible in the background for however long the network call to log the
 * violation takes. It is NOT what stops the candidate from opening the
 * Start Menu or another app — nothing running inside a browser tab can do
 * that. It only makes sure the interview content isn't visible/usable
 * while they do, and requires them to explicitly come back and re-enter
 * fullscreen to continue.
 */
export default function LockdownOverlay({ reason, onContinue, violationCount, maxViolations }) {
  const message =
    reason === 'BLUR'
      ? 'This window lost focus — you switched to another app, window, or the Start Menu.'
      : 'You are no longer in fullscreen mode.';

  return (
    <div className="proctor-lockdown-overlay">
      <div className="proctor-lockdown-box">
        <h3>🔒 Interview Locked</h3>
        <p>{message}</p>
        <p className="hint">
          The question and your answer are hidden while this window isn't focused and in
          fullscreen. This has been logged as a proctoring violation.
        </p>
        {typeof violationCount === 'number' && typeof maxViolations === 'number' && (
          <p className="proctor-violation-count">
            Violation: {violationCount} / {maxViolations}
          </p>
        )}
        <button className="primary-btn" onClick={onContinue}>
          Return to fullscreen and continue
        </button>
      </div>
    </div>
  );
}
