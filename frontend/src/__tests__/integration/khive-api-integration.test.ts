/**
 * KHIVE API Integration Tests
 * 
 * Tests the integration between frontend and KHIVE daemon APIs.
 */

import { KhiveApiService } from '@/lib/services/khiveApiService';
import { KHIVE_CONFIG } from '@/lib/config/khive';

// Mock fetch for HTTP API testing
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('KHIVE API Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Configuration', () => {
    it('should have valid configuration', () => {
      expect(KHIVE_CONFIG.API_BASE).toBeDefined();
      expect(KHIVE_CONFIG.WEBSOCKET_URL).toBeDefined();
      expect(KHIVE_CONFIG.API_BASE).toMatch(/^https?:\/\//);
      expect(KHIVE_CONFIG.WEBSOCKET_URL).toMatch(/^wss?:\/\//);
    });
  });

  describe('KhiveApiService', () => {
    it('should be importable', () => {
      expect(KhiveApiService).toBeDefined();
      expect(typeof KhiveApiService.getDaemonStatus).toBe('function');
      expect(typeof KhiveApiService.submitPlan).toBe('function');
    });

    it('should handle daemon status request', async () => {
      const mockStatus = {
        running: true,
        health: 'healthy' as const,
        uptime: 3600,
        active_sessions: 0,
        total_agents: 0,
        memory_usage: 50,
        cpu_usage: 25,
      };
      
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockStatus),
      });
      
      const result = await KhiveApiService.getDaemonStatus();
      expect(result).toEqual(mockStatus);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/daemon/status'),
        expect.any(Object)
      );
    });
  });
});