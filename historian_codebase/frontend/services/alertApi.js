/**
 * Alert API Service
 * 
 * Handles all communication with the prognostics backend API.
 * Provides methods for:
 * - Fetching active alerts
 * - Acknowledging alerts
 * - Retrieving alert history
 * - Monitoring system health
 */

class AlertApiService {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
    this.timeout = 10000; // 10 second timeout
  }

  /**
   * Make API request with timeout and error handling
   * @param {string} endpoint - API endpoint path
   * @param {object} options - Fetch options
   * @returns {Promise} Response data
   */
  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error('Request timeout');
      }
      throw error;
    }
  }

  /**
   * Get all active alerts
   * @returns {Promise<Array>} Array of alert objects
   */
  async getActiveAlerts() {
    try {
      const data = await this.request('/alerts');
      return data.alerts || [];
    } catch (error) {
      console.error('Error fetching active alerts:', error);
      throw error;
    }
  }

  /**
   * Get alert history
   * @param {number} limit - Maximum number of alerts to return
   * @returns {Promise<Array>} Array of historical alert objects
   */
  async getAlertHistory(limit = 100) {
    try {
      const data = await this.request(`/alerts/history?limit=${limit}`);
      return data.alerts || [];
    } catch (error) {
      console.error('Error fetching alert history:', error);
      throw error;
    }
  }

  /**
   * Acknowledge an alert
   * @param {string} componentId - Component identifier
   * @returns {Promise<object>} Acknowledgment confirmation
   */
  async acknowledgeAlert(componentId) {
    try {
      const data = await this.request(`/alerts/${componentId}/acknowledge`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      console.log(`Alert acknowledged for ${componentId}`);
      return data;
    } catch (error) {
      console.error(`Error acknowledging alert for ${componentId}:`, error);
      throw error;
    }
  }

  /**
   * Get system health status
   * @returns {Promise<object>} Health status object
   */
  async getSystemHealth() {
    try {
      const data = await this.request('/health');
      return data;
    } catch (error) {
      console.error('Error fetching system health:', error);
      return {
        status: 'offline',
        monitor_running: false,
        historian_connected: false,
        timestamp: new Date().toISOString()
      };
    }
  }

  /**
   * Get monitoring status
   * @returns {Promise<object>} Monitor status with running state and active alerts count
   */
  async getMonitorStatus() {
    try {
      const data = await this.request('/monitor/status');
      return data;
    } catch (error) {
      console.error('Error fetching monitor status:', error);
      throw error;
    }
  }

  /**
   * Start monitoring
   * @returns {Promise<object>} Start confirmation
   */
  async startMonitor() {
    try {
      const data = await this.request('/monitor/start', { method: 'POST' });
      console.log('Monitor started');
      return data;
    } catch (error) {
      console.error('Error starting monitor:', error);
      throw error;
    }
  }

  /**
   * Stop monitoring
   * @returns {Promise<object>} Stop confirmation
   */
  async stopMonitor() {
    try {
      const data = await this.request('/monitor/stop', { method: 'POST' });
      console.log('Monitor stopped');
      return data;
    } catch (error) {
      console.error('Error stopping monitor:', error);
      throw error;
    }
  }

  /**
   * Get all monitored components
   * @returns {Promise<Array>} Array of component identifiers
   */
  async getComponents() {
    try {
      const data = await this.request('/components');
      return data.components || [];
    } catch (error) {
      console.error('Error fetching components:', error);
      throw error;
    }
  }

  /**
   * Get health status for a specific component
   * @param {string} componentId - Component identifier
   * @returns {Promise<object>} Component health object
   */
  async getComponentHealth(componentId) {
    try {
      const data = await this.request(`/component/${componentId}/health`);
      return data;
    } catch (error) {
      console.error(`Error fetching health for ${componentId}:`, error);
      throw error;
    }
  }

  /**
   * Setup WebSocket connection for real-time alerts (future enhancement)
   * @param {function} onAlert - Callback function for new alerts
   * @param {function} onError - Error callback
   * @returns {WebSocket} WebSocket connection
   */
  connectWebSocket(onAlert, onError) {
    const protocol = this.baseUrl.startsWith('https') ? 'wss' : 'ws';
    const host = this.baseUrl.replace(/^https?:\/\//, '').replace(/:\d+$/, '');
    const port = this.baseUrl.includes(':') 
      ? this.baseUrl.split(':').pop() 
      : (protocol === 'wss' ? 443 : 80);

    const wsUrl = `${protocol}://${host}:${port}/ws/alerts`;

    try {
      const ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const alert = JSON.parse(event.data);
          onAlert(alert);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        if (onError) onError(error);
      };

      return ws;
    } catch (error) {
      console.error('Error connecting WebSocket:', error);
      if (onError) onError(error);
      return null;
    }
  }

  /**
   * Setup polling for real-time alerts (fallback if WebSocket unavailable)
   * @param {function} onAlert - Callback function for new alerts
   * @param {number} interval - Polling interval in milliseconds (default 5000)
   * @returns {number} Polling interval ID
   */
  setupPolling(onAlert, interval = 5000) {
    let previousAlertCount = 0;

    const pollAlerts = async () => {
      try {
        const alerts = await this.getActiveAlerts();
        
        if (alerts.length > previousAlertCount) {
          // New alerts detected
          const newAlerts = alerts.slice(previousAlertCount);
          newAlerts.forEach(alert => onAlert(alert));
        }
        
        previousAlertCount = alerts.length;
      } catch (error) {
        console.error('Polling error:', error);
      }
    };

    // Initial poll
    pollAlerts();

    // Setup interval
    return setInterval(pollAlerts, interval);
  }

  /**
   * Format alert for display
   * @param {object} alert - Alert object from API
   * @returns {object} Formatted alert
   */
  formatAlert(alert) {
    return {
      ...alert,
      formattedTime: new Date(alert.timestamp).toLocaleString(),
      formattedLevel: alert.level.charAt(0).toUpperCase() + alert.level.slice(1),
      exceedancePercent: (((alert.value - alert.threshold) / alert.threshold) * 100).toFixed(1)
    };
  }
}

export default AlertApiService;
