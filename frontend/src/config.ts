// Single source of truth for the backend URL.
// Set VITE_API_URL in Vercel (production) — falls back to localhost for dev.
export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const WS_BASE = API_BASE.replace(/^http/, 'ws');

// crypto.randomUUID requires a secure context (HTTPS/localhost) — fall back
// for plain-HTTP LAN testing from a phone.
export function generateId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
