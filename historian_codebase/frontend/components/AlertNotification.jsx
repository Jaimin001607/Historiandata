/**
 * Alert Notification Component
 * 
 * Displays real-time equipment health alerts from the prognostics backend.
 * Features: 
 * - Live alert list with severity levels
 * - Auto-dismiss and manual dismiss
 * - Acknowledgment tracking
 * - Sound/visual notifications
 */

import React, { useEffect, useState } from 'react';
import './AlertNotification.css';

const AlertLevel = {
  INFO: 'info',
  WARNING: 'warning',
  CRITICAL: 'critical'
};

const AlertNotification = ({ apiUrl = 'http://localhost:8000' }) => {
  const [alerts, setAlerts] = useState([]);
  const [dismissedAlerts, setDismissedAlerts] = useState(new Set());
  const [loading, setLoading] = useState(true);

  // Fetch active alerts from backend
  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const response = await fetch(`${apiUrl}/alerts`);
        if (!response.ok) throw new Error('Failed to fetch alerts');
        const data = await response.json();
        setAlerts(data.alerts || []);
        setLoading(false);
      } catch (error) {
        console.error('Error fetching alerts:', error);
        setLoading(false);
      }
    };

    // Initial fetch
    fetchAlerts();

    // Poll for new alerts every 5 seconds
    const interval = setInterval(fetchAlerts, 5000);
    return () => clearInterval(interval);
  }, [apiUrl]);

  // Play notification sound for critical alerts
  useEffect(() => {
    const criticalAlerts = alerts.filter(
      a => a.level === AlertLevel.CRITICAL && !dismissedAlerts.has(a.component_id)
    );
    
    if (criticalAlerts.length > 0) {
      playAlertSound();
    }
  }, [alerts, dismissedAlerts]);

  const playAlertSound = () => {
    // Beep sound (could be replaced with actual audio file)
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    oscillator.frequency.value = 800; // Hz
    oscillator.type = 'sine';

    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.5);
  };

  const dismissAlert = (componentId) => {
    setDismissedAlerts(prev => new Set(prev).add(componentId));
  };

  const acknowledgeAlert = async (componentId) => {
    try {
      const response = await fetch(
        `${apiUrl}/alerts/${componentId}/acknowledge`,
        { method: 'POST' }
      );
      if (response.ok) {
        // Refresh alerts after acknowledgment
        const alertsResponse = await fetch(`${apiUrl}/alerts`);
        const data = await alertsResponse.json();
        setAlerts(data.alerts || []);
      }
    } catch (error) {
      console.error('Error acknowledging alert:', error);
    }
  };

  const getAlertIcon = (level) => {
    switch (level) {
      case AlertLevel.CRITICAL:
        return '🚨';
      case AlertLevel.WARNING:
        return '⚠️';
      case AlertLevel.INFO:
        return 'ℹ️';
      default:
        return '•';
    }
  };

  const getAlertColor = (level) => {
    switch (level) {
      case AlertLevel.CRITICAL:
        return '#d32f2f'; // Red
      case AlertLevel.WARNING:
        return '#f57c00'; // Orange
      case AlertLevel.INFO:
        return '#0288d1'; // Blue
      default:
        return '#666';
    }
  };

  if (loading) {
    return <div className="alert-container"><p>Loading alerts...</p></div>;
  }

  const visibleAlerts = alerts.filter(a => !dismissedAlerts.has(a.component_id));

  return (
    <div className="alert-container">
      <div className="alert-header">
        <h2>Equipment Alerts ({visibleAlerts.length})</h2>
        {visibleAlerts.length > 0 && (
          <button 
            className="dismiss-all-btn"
            onClick={() => setDismissedAlerts(new Set(visibleAlerts.map(a => a.component_id)))}
          >
            Dismiss All
          </button>
        )}
      </div>

      {visibleAlerts.length === 0 ? (
        <div className="no-alerts">
          <p>✓ All systems nominal</p>
        </div>
      ) : (
        <div className="alert-list">
          {visibleAlerts.map((alert, index) => (
            <div 
              key={index}
              className={`alert-item alert-${alert.level}`}
              style={{ borderLeftColor: getAlertColor(alert.level) }}
            >
              <div className="alert-header-row">
                <span className="alert-icon">{getAlertIcon(alert.level)}</span>
                <span className="alert-level">{alert.level.toUpperCase()}</span>
                <span className="alert-component">{alert.component_id}</span>
                <span className="alert-metric">{alert.metric}</span>
              </div>

              <div className="alert-details">
                <p className="alert-message">{alert.message}</p>
                <div className="alert-metrics-row">
                  <span className="metric-badge">
                    Current: {alert.value.toFixed(2)}
                  </span>
                  <span className="metric-badge">
                    Threshold: {alert.threshold.toFixed(2)}
                  </span>
                  <span className="metric-badge">
                    Exceedance: {(((alert.value - alert.threshold) / alert.threshold * 100).toFixed(1))}%
                  </span>
                </div>
              </div>

              <div className="alert-timestamp">
                {new Date(alert.timestamp).toLocaleString()}
              </div>

              <div className="alert-actions">
                {!alert.acknowledged && (
                  <button
                    className="btn-acknowledge"
                    onClick={() => acknowledgeAlert(alert.component_id)}
                  >
                    Acknowledge
                  </button>
                )}
                <button
                  className="btn-dismiss"
                  onClick={() => dismissAlert(alert.component_id)}
                >
                  Dismiss
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AlertNotification;
