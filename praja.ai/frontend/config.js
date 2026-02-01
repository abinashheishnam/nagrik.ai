/**
 * Runtime config (safe to change without rebuilding).
 * On Vercel, you can edit this file and redeploy.
 */
window.__PRAJA_CONFIG__ = {
  API_BASE: "http://127.0.0.1:8000/api/v1"
};
const API = window.__PRAJA_CONFIG__?.API_BASE || "http://127.0.0.1:8000/api/v1";
