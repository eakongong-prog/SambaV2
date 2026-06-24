import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('sambav2_token') || '')
  const username = ref(localStorage.getItem('sambav2_username') || '')
  const mustChangePassword = ref(false)
  const initialized = ref(false)

  const isLoggedIn = computed(() => !!token.value)

  async function init() {
    initialized.value = true
    if (!token.value) return
    try {
      const res = await authApi.me()
      username.value = res.data.username
      mustChangePassword.value = res.data.must_change_password
    } catch {
      logout()
    }
  }

  async function login(user, pass) {
    const res = await authApi.login(user, pass)
    token.value = res.data.access_token
    username.value = user
    mustChangePassword.value = res.data.must_change_password
    localStorage.setItem('sambav2_token', token.value)
    localStorage.setItem('sambav2_username', user)
  }

  async function changePassword(oldPass, newPass) {
    await authApi.changePassword(oldPass, newPass)
    mustChangePassword.value = false
  }

  function logout() {
    token.value = ''
    username.value = ''
    localStorage.removeItem('sambav2_token')
    localStorage.removeItem('sambav2_username')
  }

  return { token, username, mustChangePassword, initialized, isLoggedIn, init, login, changePassword, logout }
})
