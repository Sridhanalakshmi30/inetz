// Tokens stay in this browser tab and are never put in URLs.
export async function authFetch(url, options = {}) {
  const headers = new Headers(options.headers);
  const path = new URL(url, window.location.origin).pathname;
  let scope = 'session';
  let id = path.match(/\/(\d+)(?:\/|$)/)?.[1];
  if (!id && typeof options.body === 'string') {
    const body = JSON.parse(options.body);
    if (body.candidateId && !path.includes('/proctoring/')) {
      scope = 'candidate';
      id = body.candidateId;
    } else id = body.session_id;
  }
  const token = id && sessionStorage.getItem(`interview:${scope}:${id}`);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(url, { ...options, headers });
  if (response.ok && (path === '/api/resume/upload' || path === '/api/resume/role-candidate' || path === '/api/interview/start')) {
    const data = await response.clone().json();
    const issuedScope = path.startsWith('/api/resume/') ? 'candidate' : 'session';
    const issuedId = issuedScope === 'candidate' ? data.candidateId : data.sessionId;
    if (data.accessToken) sessionStorage.setItem(`interview:${issuedScope}:${issuedId}`, data.accessToken);
  }
  return response;
}
