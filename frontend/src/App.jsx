import React, { useState } from 'react';
import ResumeUpload from './components/ResumeUpload.jsx';
import RoleSelect from './components/RoleSelect.jsx';
import Interview from './components/Interview.jsx';
import Report from './components/Report.jsx';
import ProctoringGuard from './components/proctoring/ProctoringGuard.jsx';
import PrivacyConsent from './components/proctoring/PrivacyConsent.jsx';

export default function App() {
  const [step, setStep] = useState('type');
  const [candidateId, setCandidateId] = useState(null);
  const [candidateName, setCandidateName] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [roleKey, setRoleKey] = useState(null);

  function handleResumeReady(id, name) {
    setCandidateId(id);
    setCandidateName(name || 'Candidate');
    setStep('consent');
  }

  function handleRoleSelected(key, id) {
    setCandidateId(id);
    setCandidateName('Candidate');
    setRoleKey(key);
    setStep('consent');
  }

  function handleInterviewFinished(finishedSessionId) {
    setSessionId(finishedSessionId);
    setStep('report');
  }

  function handleRestart() {
    setCandidateId(null);
    setSessionId(null);
    setCandidateName('');
    setRoleKey(null);
    setStep('type');
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>AI Interview Module</h1>
        <p className="subtitle">Resume-based adaptive technical interview</p>
      </header>

      <main className="app-main">
        {step === 'type' && <RoleSelect
          onResumeSelected={() => setStep('upload')}
          onRoleSelected={handleRoleSelected}
        />}

        {step === 'upload' && <ResumeUpload onReady={handleResumeReady} />}

        {step === 'consent' && (
          <PrivacyConsent candidateId={candidateId} onAccepted={() => setStep('interview')}
            onDeclined={() => setStep('declined')} />
        )}

        {step === 'declined' && (
          <section className="card" aria-labelledby="consent-declined-title">
            <h2 id="consent-declined-title">Interview cannot proceed</h2>
            <p>You declined the monitoring notice. Consent is required to take this interview.</p>
            <p>No camera or microphone access was requested, and monitoring has not started.</p>
            <button className="secondary-btn" onClick={handleRestart}>Choose interview type</button>
          </section>
        )}

        {step === 'interview' && (
          <ProctoringGuard candidateId={candidateId} key={candidateId}>
            {(proctoring) => (

              <Interview
                candidateId={candidateId}
                candidateName={candidateName}
                roleKey={roleKey}
                onFinished={handleInterviewFinished}
                onQuit={() => setStep('quit')}
                proctoring={proctoring}
              />
            )}
          </ProctoringGuard>
        )}

        {step === 'report' && (
          <Report sessionId={sessionId} onRestart={handleRestart} />
        )}
        {step === 'quit' && (
          <section className="card">
            <h2>You have quit the interview</h2>
            <p>Your submitted answers have been saved. Your unfinished answer was discarded.</p>
            <button className="secondary-btn" onClick={handleRestart}>Choose interview type</button>
          </section>
        )}
      </main>
    </div>
  );
}
