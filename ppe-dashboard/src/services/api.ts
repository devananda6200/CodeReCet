import type { StreamData, SystemMetrics } from '../types';
import { initialStreams, mockMetrics } from '../mock/mockData';

// Mock REST API Service
export const api = {
  getSystemHealth: async (): Promise<{ status: string; uptime: number }> => {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({ status: 'ok', uptime: Math.floor(Date.now() / 1000) });
      }, 200);
    });
  },

  getInitialStreams: async (): Promise<StreamData[]> => {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve(initialStreams);
      }, 500);
    });
  },

  getInitialMetrics: async (): Promise<SystemMetrics> => {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve(mockMetrics);
      }, 300);
    });
  }
};
