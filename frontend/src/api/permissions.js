import http from './index'

export const permissionsApi = {
  tree: (share, path) => http.get('/permissions/tree', { params: { share, path } }),
  getAcl: (share, path) => http.get('/permissions/acl', { params: { share, path } }),
  updateAcl: (data) => http.put('/permissions/acl', data),
  applyTemplate: (data) => http.post('/permissions/apply-template', data),
}
