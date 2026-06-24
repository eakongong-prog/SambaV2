import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useServerStore = defineStore('server', () => {
  const selectedId = ref(parseInt(localStorage.getItem('sambav2_server_id') || '0') || null)
  const selectedName = ref(localStorage.getItem('sambav2_server_name') || '')

  function selectServer(id, name) {
    selectedId.value = id
    selectedName.value = name
    localStorage.setItem('sambav2_server_id', String(id))
    localStorage.setItem('sambav2_server_name', name)
  }

  function clear() {
    selectedId.value = null
    selectedName.value = ''
    localStorage.removeItem('sambav2_server_id')
    localStorage.removeItem('sambav2_server_name')
  }

  return { selectedId, selectedName, selectServer, clear }
})
