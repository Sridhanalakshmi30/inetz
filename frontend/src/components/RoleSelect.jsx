import React, { useEffect, useState } from 'react';
import { createRoleCandidate, getRoles } from '../api.js';

export default function RoleSelect({ onResumeSelected, onRoleSelected }) {
  const [interviewType, setInterviewType] = useState(null);
  const [roles, setRoles] = useState([]);
  const [selectedKey, setSelectedKey] = useState(null);
  const [loadingRoles, setLoadingRoles] = useState(true);
  const [creatingCandidate, setCreatingCandidate] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    getRoles()
      .then((data) => setRoles(data.roles || []))
      .catch((err) => setError(err.message || 'Failed to load roles.'))
      .finally(() => setLoadingRoles(false));
  }, []);

  async function handleProceed() {
    if (interviewType === 'resume') {
      onResumeSelected();
      return;
    }
    const profileKey = interviewType === 'fresher' && selectedKey ? `fresher:${selectedKey}` : selectedKey;
    if (!profileKey) return;
    setCreatingCandidate(true);
    setError('');
    try {
      const result = await createRoleCandidate();
      onRoleSelected(profileKey, result.candidateId);
    } catch (err) {
      setError(err.message || 'Could not prepare the role-based interview.');
      setCreatingCandidate(false);
    }
  }

  const selectedRole = roles.find((role) => role.key === selectedKey);

  return (
    <div className="card">
      <h2>Step 1 — Select Interview Type</h2>
      <p className="hint">Choose a resume-based, experienced role-based, or fresher interview.</p>

      <div className="type-selector-grid">
        <button type="button" className={`type-card ${interviewType === 'resume' ? 'type-card-selected' : ''}`}
          onClick={() => { setInterviewType('resume'); setSelectedKey(null); }}>
          <div className="type-header"><span className="type-badge">Type 1</span></div>
          <h3 className="type-title">Resume-Based</h3>
          <p className="type-description">Upload your resume and receive questions about its skills, projects, and experience.</p>
        </button>

        <button type="button" className={`type-card ${interviewType === 'role' ? 'type-card-selected' : ''}`}
          onClick={() => setInterviewType('role')}>
          <div className="type-header"><span className="type-badge">Type 2</span></div>
          <h3 className="type-title">Experienced Role-Based</h3>
          <p className="type-description">Choose a job role and receive questions on its core skills. No resume upload is needed.</p>
        </button>

        <button type="button" className={`type-card ${interviewType === 'fresher' ? 'type-card-selected' : ''}`}
          onClick={() => { setInterviewType('fresher'); setSelectedKey(null); }}>
          <div className="type-header"><span className="type-badge">Type 3</span></div>
          <h3 className="type-title">Fresher Role-Based</h3>
          <p className="type-description">Choose a job role and receive easy-to-moderate questions on its fundamentals. No resume upload is needed.</p>
        </button>
      </div>

      {interviewType === 'resume' && <div className="type-confirmation-box">
        <p className="hint">You will upload a PDF or Word resume on the next screen.</p>
        <button type="button" className="primary-btn" onClick={handleProceed}>Continue to Resume Upload →</button>
      </div>}

      {(interviewType === 'role' || interviewType === 'fresher') && <div className="type-confirmation-box">
        <p className="hint">Choose one of the nine roles for your {interviewType === 'fresher' ? 'fresher' : 'experienced'} interview:</p>
        {loadingRoles && <p className="hint">Loading available roles…</p>}
        {!loadingRoles && <div className="role-grid">
          {roles.map((role) => <button key={role.key} type="button"
            className={`role-card ${selectedKey === role.key ? 'role-card-selected' : ''}`}
            onClick={() => setSelectedKey(role.key)}>
            <strong>{role.label}</strong>
            <span>{role.core_topics.length} core topics</span>
          </button>)}
        </div>}
        {error && <p className="error-text">{error}</p>}
        <button type="button" className="primary-btn" disabled={!selectedKey || creatingCandidate} onClick={handleProceed}>
          {creatingCandidate ? 'Preparing interview…' : selectedRole ? `Continue with ${interviewType === 'fresher' ? 'Fresher ' : ''}${selectedRole.label} →` : 'Select a role to continue'}
        </button>
      </div>}
    </div>
  );
}
