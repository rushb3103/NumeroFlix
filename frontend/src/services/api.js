import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 15000,
  withCredentials: true,
  paramsSerializer: { indexes: null },
})

api.interceptors.response.use(
  response => response,
  error => {
    const requestPath = error.config?.url || ''
    if (error.response?.status === 401 && !requestPath.startsWith('/auth/')) {
      window.dispatchEvent(new Event('numeroflix:unauthorized'))
    }
    return Promise.reject(error)
  },
)
export default api

