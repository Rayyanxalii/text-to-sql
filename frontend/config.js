/**
 * Query Sentinel — Runtime Configuration
 *
 * Configurable backend endpoint and application settings.
 * Can be overridden via window.QUERY_SENTINEL_CONFIG, environment injection,
 * or runtime settings saved in localStorage.
 */
window.QUERY_SENTINEL_CONFIG = {
  // Backend API Base URL
  API_URL: (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'))
    ? 'http://127.0.0.1:8000'
    : (typeof window !== 'undefined' && window.location.origin && window.location.origin.startsWith('http') ? window.location.origin : 'http://127.0.0.1:8000'),

  // Health check polling frequency in milliseconds
  HEALTH_CHECK_INTERVAL_MS: 10000,

  // Request timeout in milliseconds
  REQUEST_TIMEOUT_MS: 45000,

  // Application metadata
  APP_NAME: 'Query Sentinel',
  APP_VERSION: '1.0.0'
};
