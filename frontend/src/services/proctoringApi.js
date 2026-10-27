import { authFetch } from './authFetch.js';
async function handleResponse(res) {
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const err = new Error(
      data.detail ||
      data.error ||
      `Request failed with status ${res.status}`
    );
    err.status = res.status;
    throw err;
  }

  return data;
}

export async function startProctoring(sessionId) {
  const res = await authFetch(
    '/api/interview/proctoring/start',
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
      }),
    }
  );

  return handleResponse(res);
}

export async function sendProctoringEvent(
  sessionId,
  eventType,
  {
    questionNumber,
    durationSeconds,
    metadata,
  } = {}
) {
  const res = await authFetch(
    '/api/interview/proctoring/event',
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        event_type: eventType,
        question_number: questionNumber ?? null,
        client_timestamp: new Date().toISOString(),
        duration_seconds: durationSeconds ?? null,
        metadata: metadata ?? null,
      }),
    }
  );

  return handleResponse(res);
}

export async function getProctoringStatus(sessionId) {
  const res = await authFetch(
    `/api/interview/proctoring/status/${sessionId}`
  );

  return handleResponse(res);
}

export async function terminateProctoring(sessionId) {
  const res = await authFetch(
    `/api/interview/proctoring/terminate/${sessionId}`,
    {
      method: 'POST',
    }
  );

  return handleResponse(res);
}

export async function getProctoringSummary(sessionId) {
  const res = await authFetch(
    `/api/interview/proctoring/summary/${sessionId}`
  );

  return handleResponse(res);
}
