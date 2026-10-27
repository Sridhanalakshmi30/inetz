import React, { useRef, useState } from 'react';
import { giveConsent } from '../../api.js';

export default function PrivacyConsent({ candidateId, onAccepted, onDeclined }) {
  const [agreed, setAgreed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const submitting = useRef(false);

  async function handleContinue(event) {
    event.preventDefault();
    if (!agreed || submitting.current) return;
    submitting.current = true;
    setSaving(true);
    setError('');
    try {
      await giveConsent(candidateId);
      onAccepted();
    } catch (err) {
      setError(err.message || 'Could not save consent. Please try again.');
    } finally {
      submitting.current = false;
      setSaving(false);
    }
  }

  return (
    <section className="card privacy-consent" aria-labelledby="privacy-title">
      <h2 id="privacy-title">Privacy &amp; Monitoring Notice</h2>

      <h3>This interview uses</h3>
      <ul>
        <li><strong>Camera &amp; Face Tracking:</strong> Local in-browser face verification ensures you remain on camera.</li>
        <li><strong>Microphone:</strong> Browser speech recognition converts spoken answers into text. Depending on your browser, its speech provider may process audio remotely. This app sends only the transcript to the interview server.</li>
        <li><strong>Fullscreen Enforcement:</strong> Fullscreen mode is required to maintain focus.</li>
        <li><strong>Browser Activity Monitoring:</strong> Tab switches and window focus loss are detected.</li>
      </ul>

      <h3>What is analysed &amp; stored</h3>
      <ul>
        <li><strong>Speech Privacy:</strong> This interview does not record or upload audio clips or create a voice profile. Spoken answers, including any edits, are saved as text and marked as voice answers.</li>
        <li><strong>Interview Content:</strong> Your typed answers, speech transcripts, and proctoring event logs are saved for evaluation.</li>
      </ul>

      <h3>Integrity Policy</h3>
      <p>
        Camera, fullscreen, and browser activity monitoring remain active during the interview. Proctoring events are recorded for review.
      </p>

      <form onSubmit={handleContinue}>
        <label className="consent-checkbox">
          <input
            type="checkbox"
            checked={agreed}
            disabled={saving}
            onChange={(event) => setAgreed(event.target.checked)}
          />
          <span>
            I have read and agree to the camera, microphone, and browser activity monitoring described above.
          </span>
        </label>
        {error && <p className="error-text" role="alert">{error}</p>}
        <div className="consent-actions">
          <button type="submit" className="primary-btn" disabled={!agreed || saving}>
            {saving ? 'Saving consent…' : 'I Agree — Continue'}
          </button>
          <button type="button" className="secondary-btn" disabled={saving} onClick={onDeclined}>
            Decline
          </button>
        </div>
      </form>
    </section>
  );
}
