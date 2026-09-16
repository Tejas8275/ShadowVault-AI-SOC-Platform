import { api } from './api'

export interface Readiness { status: 'ok'; database: 'ok' }
export const healthService = { check: () => api<Readiness>('/health') }
