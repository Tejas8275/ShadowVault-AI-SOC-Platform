import { api } from './api'

export interface LoginInput { email: string; password: string }

// Foundation endpoint returns 501; a session contract will be added with authentication.
export const authService = {
  login: (input: LoginInput) => api<void>('/auth/login', {
    method: 'POST', body: JSON.stringify(input),
  }),
}
