import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { AuthAPI, User, AuthResponse } from '@/services/api'

interface AuthState {
  isAuthenticated: boolean
  user: User | null
  token: string | null
  refreshToken: string | null
  isLoading: boolean
  error: string | null
}

interface AuthActions {
  login: (email: string, password: string) => Promise<void>
  loginWithMagicLink: (token: string) => Promise<void>
  logout: () => void
  refreshAuth: () => Promise<void>
  clearError: () => void
  setLoading: (loading: boolean) => void
}

type AuthStore = AuthState & AuthActions

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // State
      isAuthenticated: false,
      user: null,
      token: null,
      refreshToken: null,
      isLoading: false,
      error: null,

      // Actions
      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response: AuthResponse = await AuthAPI.login(email, password)
          set({
            isAuthenticated: true,
            user: response.user,
            token: response.token,
            refreshToken: response.refreshToken,
            isLoading: false,
            error: null,
          })
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Login failed',
          })
          throw error
        }
      },

      loginWithMagicLink: async (token: string) => {
        set({ isLoading: true, error: null })
        try {
          const response: AuthResponse = await AuthAPI.verifyMagicLink(token)
          set({
            isAuthenticated: true,
            user: response.user,
            token: response.token,
            refreshToken: response.refreshToken,
            isLoading: false,
            error: null,
          })
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Magic link verification failed',
          })
          throw error
        }
      },

      logout: () => {
        // Call logout API if token exists
        const { token } = get()
        if (token) {
          AuthAPI.logout().catch(console.error)
        }
        
        set({
          isAuthenticated: false,
          user: null,
          token: null,
          refreshToken: null,
          isLoading: false,
          error: null,
        })
      },

      refreshAuth: async () => {
        const { refreshToken } = get()
        if (!refreshToken) {
          get().logout()
          return
        }

        try {
          const response: AuthResponse = await AuthAPI.refreshToken()
          set({
            isAuthenticated: true,
            user: response.user,
            token: response.token,
            refreshToken: response.refreshToken,
            error: null,
          })
        } catch (error) {
          console.error('Token refresh failed:', error)
          get().logout()
        }
      },

      clearError: () => {
        set({ error: null })
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading })
      },
    }),
    {
      name: 'lucid-auth-storage',
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
      }),
    }
  )
)
