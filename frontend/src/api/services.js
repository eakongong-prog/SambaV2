import http from './index'

export const servicesApi = {
  status: () => http.get('/services/status'),
  action: (name, action) => http.post(`/services/${name}/${action}`),
  reloadConfig: () => http.post('/services/reload-config'),
  sessions: () => http.get('/services/sessions'),
  disconnectSession: (pid) => http.post(`/services/sessions/${pid}/disconnect`),
}
