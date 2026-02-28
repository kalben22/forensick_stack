import { apiClient } from './client'

export interface LoginCredentials {
  username: string
  password: string
}

export interface RegisterData {
  username: string
  password: string
  email?: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  username: string
  role: string
}

export interface UserResponse {
  id: number
  username: string
  email: string | null
  role: string
  is_active: boolean
  created_at: string
}

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<TokenResponse> => {
    const { data } = await apiClient.post<TokenResponse>('/auth/login', credentials)
    return data
  },

  register: async (userData: RegisterData): Promise<UserResponse> => {
    const { data } = await apiClient.post<UserResponse>('/auth/register', userData)
    return data
  },

  getMe: async (): Promise<UserResponse> => {
    const { data } = await apiClient.get<UserResponse>('/auth/me')
    return data
  },
}
