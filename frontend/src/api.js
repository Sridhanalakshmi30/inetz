import { authFetch } from './services/authFetch.js';
// Small fetch wrapper for all backend calls. The Vite dev server proxies /api to the backend.

async function handleResponse(res) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || (typeof data.detail === 'string' && data.detail) || `Request failed with status ${res.status}`);
  }
  return data;
}

export async function uploadResume(file) {
  const formData = new FormData();
  formData.append('resume', file);
  const res = await authFetch('/api/resume/upload', { method: 'POST', body: formData });
  return handleResponse(res);
}

export async function createRoleCandidate() {
  return handleResponse(await authFetch('/api/resume/role-candidate', { method: 'POST' }));
}

export async function giveConsent(candidateId) {
  const res = await authFetch('/api/interview/consent', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ candidateId }),
  });
  return handleResponse(res);
}

export async function startInterview(candidateId, durationMinutes, roleKey = null) {
  const res = await authFetch('/api/interview/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ candidateId, durationMinutes, roleKey }),
  });
  return handleResponse(res);
}

export async function getRoles() {
  const res = await authFetch('/api/interview/roles');
  return handleResponse(res);
}

export async function registerVoiceBaseline(candidateId, audioBlob, sessionId = null) {
  const formData = new FormData();
  if (candidateId) formData.append('candidateId', candidateId);
  if (sessionId) formData.append('sessionId', sessionId);
  const filename = (audioBlob.type && audioBlob.type.includes('wav')) ? 'baseline.wav' : 'baseline.webm';
  formData.append('audio', audioBlob, filename);

  const res = await authFetch('/api/interview/voice/baseline', {
    method: 'POST',
    body: formData,
  });
  return handleResponse(res);
}

export async function verifyVoice(sessionId, audioBlob, questionNumber = null) {
  const formData = new FormData();
  if (sessionId) formData.append('sessionId', sessionId);
  if (questionNumber) formData.append('questionNumber', questionNumber);
  const filename = (audioBlob.type && audioBlob.type.includes('wav')) ? 'voice_check.wav' : 'voice_check.webm';
  formData.append('audio', audioBlob, filename);

  const res = await authFetch('/api/interview/voice/verify', {
    method: 'POST',
    body: formData,
  });
  return handleResponse(res);
}

export async function submitRepeatVoiceCheck(sessionId, audioBlob, questionNumber = null) {
  const formData = new FormData();
  if (sessionId) formData.append('sessionId', sessionId);
  if (questionNumber) formData.append('questionNumber', questionNumber);
  const filename = (audioBlob.type && audioBlob.type.includes('wav')) ? 'repeat_check.wav' : 'repeat_check.webm';
  formData.append('audio', audioBlob, filename);

  const res = await authFetch('/api/interview/voice/repeat-check', {
    method: 'POST',
    body: formData,
  });
  return handleResponse(res);
}

export async function clearVoiceEmbedding(sessionId = null, candidateId = null) {
  const res = await authFetch('/api/interview/voice/clear', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sessionId, candidateId }),
  });
  return handleResponse(res);
}

export async function submitAnswer(sessionId, turnId, { answerText, answerSource = 'typed' }) {
  const formData = new FormData();
  formData.append('turnId', turnId);
  if (answerText) formData.append('answerText', answerText);
  formData.append('answerSource', answerSource);

  const res = await authFetch(`/api/interview/${sessionId}/answer`, { method: 'POST', body: formData });
  return handleResponse(res);
}


export async function getReport(sessionId) {
  const res = await authFetch(`/api/interview/${sessionId}/report`);
  return handleResponse(res);
}

export async function quitInterview(sessionId) {
  const res = await authFetch(`/api/interview/${sessionId}/quit`, { method: 'POST' });
  return handleResponse(res);
}
