export const API_BASE_URL = (() => {
  const value = process.env.REACT_APP_BACKEND_URL?.trim();
  if (!value || value === 'undefined') {
    return '';
  }
  return value.replace(/\/$/, '');
})();

export const API = `${API_BASE_URL}/api`;

export const getAuthHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem('token') || ''}`,
});