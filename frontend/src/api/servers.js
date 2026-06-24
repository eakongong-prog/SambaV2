import http from './index'

export const serversApi = {
  list: () => http.get('/servers'),
  get: (id) => http.get(`/servers/${id}`),
  create: (data) => http.post('/servers', data),
  update: (id, data) => http.put(`/servers/${id}`, data),
  delete: (id) => http.delete(`/servers/${id}`),
  testConnection: (id) => http.post(`/servers/${id}/test-connection`),
}
