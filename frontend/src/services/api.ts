import axios from 'axios';
import type { Transaction, NewTransaction, User, AuthResponse, TransactionSummary, PreviewResponse, Budget } from '../types';

// When using Vite's proxy, we use relative URLs
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  }
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const language = localStorage.getItem('language') || 'en';
  config.headers['Accept-Language'] = language;
  const currency = localStorage.getItem('currency') || 'USD';
  config.headers['X-Currency'] = currency;
  return config;
});

export const authApi = {
  login: async (data: any): Promise<AuthResponse> => {
    const params = new URLSearchParams();
    params.append('username', data.email);
    params.append('password', data.password);

    const response = await api.post('/auth/token', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  },
  register: async (data: any): Promise<User> => {
    const response = await api.post('/auth/register', data);
    return response.data;
  },
  me: async (): Promise<User> => {
    const response = await api.get('/auth/me');
    return response.data;
  },
};

export const transactionApi = {
  getTransactions: async (): Promise<Transaction[]> => {
    const response = await api.get('/transactions');
    return response.data;
  },

  addTransaction: async (transaction: NewTransaction): Promise<Transaction> => {
    const response = await api.post('/transactions', transaction);
    return response.data;
  },

  updateTransaction: async (id: number, transaction: Partial<NewTransaction>): Promise<Transaction> => {
    const response = await api.put(`/transactions/${id}`, transaction);
    return response.data;
  },

  deleteTransaction: async (id: number): Promise<void> => {
    await api.delete(`/transactions/${id}`);
  },

  bulkDeleteTransactions: async (ids: number[]): Promise<{ message: string; deleted_count: number }> => {
    const response = await api.post('/transactions/bulk/delete', { ids });
    return response.data;
  },

  uploadTransactions: async (file: File, columnMapping?: Record<string, string>): Promise<TransactionSummary> => {
    const formData = new FormData();
    formData.append('file', file);
    if (columnMapping) {
      formData.append('column_mapping', JSON.stringify(columnMapping));
    }
    const response = await api.post('/transactions/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  previewTransactions: async (file: File, columnMapping?: Record<string, string>): Promise<PreviewResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    if (columnMapping) {
      formData.append('column_mapping', JSON.stringify(columnMapping));
    }
    const response = await api.post('/transactions/preview', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  batchCreateTransactions: async (transactions: NewTransaction[]): Promise<TransactionSummary> => {
    const response = await api.post('/transactions/batch/', transactions);
    return response.data;
  },

  getReportSummary: async (startDate?: string, endDate?: string): Promise<any> => {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    
    const response = await api.get(`/transactions/report/summary?${params.toString()}`);
    return response.data;
  },
};

export const budgetApi = {
  getBudgets: async (): Promise<Budget[]> => {
    const response = await api.get('/budgets');
    return response.data;
  },
  createBudget: async (budget: { category: string; amount: number }): Promise<Budget> => {
    const response = await api.post('/budgets', budget);
    return response.data;
  },
  updateBudget: async (id: number, budget: { amount: number }): Promise<Budget> => {
    const response = await api.put(`/budgets/${id}`, budget);
    return response.data;
  },
  deleteBudget: async (id: number): Promise<void> => {
    await api.delete(`/budgets/${id}`);
  },
};
