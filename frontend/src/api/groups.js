import http from './index'

export const groupsApi = {
  list: () => http.get('/groups'),
  get: (name) => http.get(`/groups/${name}`),
  create: (data) => http.post('/groups', data),
  delete: (name) => http.delete(`/groups/${name}`),
  updateMembers: (name, members) => http.put(`/groups/${name}/members`, { members }),
}
