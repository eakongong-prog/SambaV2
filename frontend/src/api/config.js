import http from './index'

export const configApi = {
  get: () => http.get('/config'),
  update: (data) => http.put('/config', data),
  validate: (data) => http.post('/config/validate', data),
  listBackups: () => http.get('/config/backups'),
  createBackup: () => http.post('/config/backups'),
  restoreBackup: (id) => http.post(`/config/backups/${id}/restore`),
}
