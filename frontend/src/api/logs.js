import http from './index'

export const logsApi = {
  get: (params) => http.get('/logs', { params }),
}
