// Default to empty string for relative paths in local development where proxy handles it.
// In production (Vercel), this will be populated from VITE_API_BASE_URL.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
