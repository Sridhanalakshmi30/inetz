import test from 'node:test';
import assert from 'node:assert/strict';
import { authFetch } from './authFetch.js';

const tokens = new Map();
globalThis.window = { location: { origin: 'https://interview.example.com' } };
globalThis.sessionStorage = {
  getItem: (key) => tokens.get(key) ?? null,
  setItem: (key, value) => tokens.set(key, value),
};

test('upload and start store separate credentials and use the right scope', async () => {
  tokens.clear();
  globalThis.fetch = async (url, options) => {
    if (url === '/api/resume/upload') {
      assert.equal(options.headers.get('Authorization'), null);
      return Response.json({ candidateId: 7, accessToken: 'candidate-secret' });
    }
    assert.equal(options.headers.get('Authorization'), 'Bearer candidate-secret');
    return Response.json({ sessionId: 11, accessToken: 'session-secret' });
  };
  await authFetch('/api/resume/upload', { method: 'POST', body: new FormData() });
  await authFetch('/api/interview/start', { method: 'POST', body: JSON.stringify({ candidateId: 7 }) });
  assert.equal(tokens.get('interview:session:11'), 'session-secret');
  assert.equal(tokens.get('interview:candidate:7'), 'candidate-secret');
});

test('session requests use only their matching token', async () => {
  tokens.set('interview:session:11', 'session-secret');
  globalThis.fetch = async (url, options) => {
    assert.equal(options.headers.get('Authorization'), 'Bearer session-secret');
    return Response.json({});
  };
  await authFetch('/api/interview/11/report');
  await authFetch('/api/interview/11/answer', { method: 'POST', body: new FormData() });
  await authFetch('/api/interview/proctoring/event', { method: 'POST', body: JSON.stringify({ session_id: 11 }) });
  globalThis.fetch = async (url, options) => {
    assert.equal(options.headers.get('Authorization'), null);
    return Response.json({}, { status: 401 });
  };
  await authFetch('/api/interview/12/report');
});

test('role-only candidate stores its credential without a resume', async () => {
  tokens.clear();
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/resume/role-candidate');
    assert.equal(options.headers.get('Authorization'), null);
    return Response.json({ candidateId: 23, accessToken: 'role-candidate-secret' });
  };
  await authFetch('/api/resume/role-candidate', { method: 'POST' });
  assert.equal(tokens.get('interview:candidate:23'), 'role-candidate-secret');
});
