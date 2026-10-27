import React, { useEffect, useState } from 'react';
import { getReport } from '../api.js';
import { getProctoringSummary } from '../services/proctoringApi.js';

export default function Report({ sessionId, onRestart }) {
  const [report, setReport] = useState(null);
  const [proctoringSummary, setProctoringSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const [reportResult, summaryResult] = await Promise.allSettled([
          getReport(sessionId),
          getProctoringSummary(sessionId),
        ]);

        if (reportResult.status === 'fulfilled') {
          setReport(reportResult.value);
        } else {
          setError(reportResult.reason?.message || 'Could not load the report.');
        }

        if (summaryResult.status === 'fulfilled') {
          setProctoringSummary(summaryResult.value);
        }
      } catch (err) {
        setError(err.message || 'Could not load the report.');
      } finally {
        setLoading(false);
      }
    })();
  }, [sessionId]);

  if (loading) {
    return (
      <div className="card">
        <h2>Generating your final report…</h2>
        <p className="hint">The AI is reviewing your full interview to produce a fair, detailed evaluation.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <p className="error-text">{error}</p>
        <button className="secondary-btn" onClick={onRestart}>Start Over</button>
      </div>
    );
  }

  const skillScores = report.skill_scores || {};

  return (
    <div className="card">
      <h2>Interview Report</h2>
      <p className="hint" style={{ marginTop: '-0.5rem', marginBottom: '1.25rem' }}>
        Interview Type: <strong>{report.role_key?.startsWith('fresher:') ? `Type 3 — Fresher Role-Based (${report.role_key.slice(8)})` : report.role_key ? `Type 2 — Experienced Role-Based (${report.role_key})` : 'Type 1 — Resume-Based'}</strong>
      </p>

      <div className="overall-score">
        <span className="score-number">{report.overall_score}</span>
        <span className="score-label">Overall Score / 10</span>
      </div>

      <p className="recommendation-badge">{report.recommendation}</p>

      <h3>Skill Breakdown</h3>
      <ul className="score-list">
        {Object.entries(skillScores).map(([key, value]) => (
          <li key={key}>
            <span className="skill-name">{key.replace(/_/g, ' ')}</span>
            <span className="skill-score">{value}/10</span>
          </li>
        ))}
      </ul>

      <h3>Strengths</h3>
      <ul>
        {(report.strengths || []).map((s, i) => <li key={i}>{s}</li>)}
      </ul>

      <h3>Areas to Improve</h3>
      <ul>
        {(report.weaknesses || []).map((w, i) => <li key={i}>{w}</li>)}
      </ul>

      <h3>Feedback</h3>
      <p>{report.feedback_text}</p>

      {proctoringSummary && (
        <>
          <h3>Proctoring &amp; Identity Summary</h3>
          {(proctoringSummary.status === 'TERMINATED' || proctoringSummary.proctoring_status === 'TERMINATED') && (
            <p className="malpractice-flag">
              {proctoringSummary.malpractice && <strong>Malpractice: </strong>}
              {proctoringSummary.termination_reason || 'This interview was terminated for repeated proctoring violations.'}
            </p>
          )}

          {proctoringSummary.needs_review && (
            <div className="voice-review-banner">
              <strong>⚠️ Integrity Review Flag:</strong> voice mismatch, needs review
              <p style={{ margin: '0.4rem 0 0', fontSize: '0.9rem' }}>
                A voice pattern discrepancy was detected during the interview and recorded for human evaluator review.
              </p>
            </div>
          )}

          {proctoringSummary.voice_mismatches && proctoringSummary.voice_mismatches.length > 0 && (
            <div className="voice-mismatch-audit">
              <h4 style={{ margin: '0.75rem 0 0.4rem', color: '#b45309' }}>Voice Verification Audit Trail</h4>
              <ul className="voice-audit-list">
                {proctoringSummary.voice_mismatches.map((item, i) => (
                  <li key={i} className="voice-audit-item">
                    <span className="flag-tag">voice mismatch, needs review</span>
                    <span> &bull; Question {item.question_number ?? 'N/A'}</span>
                    <span> &bull; {item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : 'Recorded'}</span>
                    {typeof item.similarity === 'number' && (
                      <span className="similarity-tag">
                        {' '}(similarity: {item.similarity}, threshold: {item.threshold ?? 0.68})
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <ul className="score-list">
            <li>
              <span className="skill-name">Proctoring status</span>
              <span className="skill-score">{proctoringSummary.status || 'COMPLETED'}</span>
            </li>
            <li>
              <span className="skill-name">Voice mismatch events</span>
              <span className="skill-score">
                {proctoringSummary.voice_mismatch_events || 0}
                {proctoringSummary.voice_mismatch_events > 0 && ' (needs review)'}
              </span>
            </li>
            <li>
              <span className="skill-name">Total violations</span>
              <span className="skill-score">{proctoringSummary.violation_count || 0} / {proctoringSummary.max_violations || 4}</span>
            </li>
            <li>
              <span className="skill-name">Tab switch events</span>
              <span className="skill-score">{proctoringSummary.tab_switch_events || 0}</span>
            </li>
            <li>
              <span className="skill-name">Window blur events</span>
              <span className="skill-score">{proctoringSummary.window_blur_events || 0}</span>
            </li>
            <li>
              <span className="skill-name">Fullscreen exits</span>
              <span className="skill-score">{proctoringSummary.fullscreen_exit_events || 0}</span>
            </li>
            <li>
              <span className="skill-name">Shortcut attempts blocked</span>
              <span className="skill-score">{proctoringSummary.shortcut_attempts || 0}</span>
            </li>
            <li>
              <span className="skill-name">Paste attempts blocked</span>
              <span className="skill-score">{proctoringSummary.paste_attempts || 0}</span>
            </li>
            <li>
              <span className="skill-name">Copy attempts blocked</span>
              <span className="skill-score">{proctoringSummary.copy_attempts || 0}</span>
            </li>
            <li>
              <span className="skill-name">No face detected events</span>
              <span className="skill-score">{proctoringSummary.no_face_events || 0}</span>
            </li>
            <li>
              <span className="skill-name">Multiple faces detected</span>
              <span className="skill-score">{proctoringSummary.multiple_face_events || 0}</span>
            </li>
          </ul>
        </>
      )}


      <button className="primary-btn" onClick={onRestart} style={{ marginTop: '1.5rem' }}>
        Start a New Interview
      </button>
    </div>
  );
}
