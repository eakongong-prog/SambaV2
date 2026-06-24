import http from './index'

export const dashboardApi = {
  overview: () => http.get('/dashboard/overview'),
  auditLogs: (limit = 20) => http.get('/dashboard/audit-logs', { params: { limit } }),
  sessionHistory: (hours = 24) => http.get('/dashboard/session-history', { params: { hours } }),
  topShares: () => http.get('/dashboard/top-shares'),
}
