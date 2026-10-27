import React, { useState } from 'react';
import { uploadResume } from '../api.js';

export default function ResumeUpload({ onReady }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function handleFileChange(e) {
    setError('');
    const selected = e.target.files[0];
    if (!selected) return;
    const ext = selected.name.split('.').pop().toLowerCase();
    if (!['pdf', 'docx'].includes(ext)) {
      setError('Please choose a .pdf or .docx file.');
      return;
    }
    setFile(selected);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) {
      setError('Please choose your resume file first.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const result = await uploadResume(file);
      onReady(result.candidateId, result.parsedResume?.name);
    } catch (err) {
      setError(err.message || 'Something went wrong while processing your resume.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <h2>Step 2 — Upload your resume</h2>
      <p className="hint">
        Upload your resume as a PDF or Word document. The AI will read it and build interview
        questions about your technical skills, internships, and projects.
      </p>

      <form onSubmit={handleSubmit} className="upload-form">
        <input
          type="file"
          accept=".pdf,.docx"
          onChange={handleFileChange}
          disabled={loading}
        />

        {file && <p className="file-chip">Selected: {file.name}</p>}
        {error && <p className="error-text">{error}</p>}

        <button type="submit" className="primary-btn" disabled={loading || !file}>
          {loading ? 'Reading your resume…' : 'Continue to Interview'}
        </button>
      </form>

      {loading && (
        <p className="hint" style={{ marginTop: '1rem' }}>
          This can take a few seconds while the AI extracts your skills and experience.
        </p>
      )}
    </div>
  );
}
