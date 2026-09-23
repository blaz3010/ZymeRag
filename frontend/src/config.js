// Centralized API Configuration for ZymeRag / Axiom Gateway
// Defaults to local development backend if in Vite dev server (port 5173),
// otherwise uses VITE_API_URL environment variable or relative root.
export const API = import.meta.env.VITE_API_URL || (typeof window !== 'undefined' && window.location.port === '5173' ? 'http://localhost:8000' : '');
