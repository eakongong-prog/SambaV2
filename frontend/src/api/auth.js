import http from './index'

export const authApi = {
  login: (username, password) => http.post('/auth/login', { username, password }),
  me: () => http.get('/auth/me'),
  changePassword: (old_password, new_password) =>
    http.post('/auth/change-password', { old_password, new_password }),
}
