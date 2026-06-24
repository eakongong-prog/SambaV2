import http from './index'

export const sharesApi = {
  list: () => http.get('/shares'),
  get: (name) => http.get(`/shares/${name}`),
  create: (data) => http.post('/shares', data),
  update: (name, data) => http.put(`/shares/${name}`, data),
  delete: (name) => http.delete(`/shares/${name}`),
}
