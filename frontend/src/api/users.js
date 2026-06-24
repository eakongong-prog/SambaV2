import http from './index'

export const usersApi = {
  list: () => http.get('/users'),
  get: (username) => http.get(`/users/${username}`),
  create: (data) => http.post('/users', data),
  update: (username, data) => http.put(`/users/${username}`, data),
  delete: (username) => http.delete(`/users/${username}`),
  resetPassword: (username, password) =>
    http.post(`/users/${username}/reset-password`, { password }),
  batchImport: (data) => http.post('/users/batch-import', data),
}
