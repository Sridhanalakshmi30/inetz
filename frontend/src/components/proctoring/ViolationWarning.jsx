import React from 'react';

const EVENT_LABELS = {
  TAB_SWITCH: 'You switched away from the interview tab.',
  WINDOW_BLUR: 'You left the interview window.',
  FULLSCREEN_EXIT: 'You exited fullscreen mode.',
  NO_FACE_DETECTED: 'You were not visible in the camera.',
  MULTIPLE_FACES_DETECTED: 'More than one face was detected.',
  SHORTCUT_BLOCKED: 'A blocked keyboard shortcut was used (e.g. switching or opening a tab, reloading, or devtools).',
  PASTE_BLOCKED: 'A paste attempt into the answer box was blocked.',
  COPY_BLOCKED: 'An attempt to copy the question was blocked.',
};

export default function ViolationWarning({
  violation,
  violationCount,
  maxViolations,
  onContinue,
}) {

  if (!violation) {
    return null;
  }

  const isFinal =
    violation.action === 'FINAL_WARN';
  const isMultipleFaces = violation.eventType === 'MULTIPLE_FACES_DETECTED';

  const message =
    EVENT_LABELS[violation.eventType] ||
    'A proctoring violation was detected.';

  return (
    <div className="proctor-modal-overlay">

      <div
        role="alertdialog"
        aria-modal="true"
        aria-label={`Interview warning ${violationCount} of ${maxViolations}`}
        className={
          `proctor-modal ${
            isFinal
              ? 'proctor-modal-final'
              : ''
          }`
        }
      >

        <h3>
          {isFinal
            ? '⚠ FINAL WARNING'
            : '⚠ Interview Warning'}
        </h3>

        <p>{message}</p>

        <p>
          {isMultipleFaces ? violation.message : isFinal
            ? 'The next violation reaches the violation limit. Your interview will end with a suspected malpractice notification.'
            : 'Return to fullscreen and stay on the interview tab. Reaching the violation limit will end the interview.'}
        </p>

        <p className="proctor-violation-count">
          {isMultipleFaces ? 'Ask the other person to leave the camera view now.' : `Warning: ${violationCount} / ${maxViolations}`}
        </p>

        <button
          className="primary-btn"
          onClick={onContinue}
        >
          Return to Fullscreen and Continue
        </button>

      </div>

    </div>
  );
}
