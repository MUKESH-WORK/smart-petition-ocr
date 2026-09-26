/**
 * Privacy-First Telemetry & Performance Monitoring Utility
 * Compliant with DPDP Act & OWASP Privacy Guidelines.
 * Collects anonymized operational metrics (OCR speed, dispatch latency) locally.
 */

class TelemetryTracker {
  constructor() {
    this.enabled = true;
    this.sessionId = Math.random().toString(36).substring(2, 10);
    this.metrics = [];
  }

  trackEvent(eventName, properties = {}) {
    if (!this.enabled) return;
    
    // Sanitize properties: strip any PII (names, phone numbers, aadhaar)
    const sanitizedProps = { ...properties };
    delete sanitizedProps.name;
    delete sanitizedProps.phone;
    delete sanitizedProps.aadhaar;
    delete sanitizedProps.password;
    delete sanitizedProps.email;

    const eventData = {
      event: eventName,
      timestamp: new Date().toISOString(),
      sessionId: this.sessionId,
      properties: sanitizedProps
    };

    this.metrics.push(eventData);
    if (this.metrics.length > 50) {
      this.metrics.shift();
    }

    if (process.env.NODE_ENV === 'development') {
      console.debug(`[Telemetry] ${eventName}`, sanitizedProps);
    }
  }

  trackPageView(pageName) {
    this.trackEvent('page_view', { path: pageName });
  }

  trackPerformance(metricName, durationMs) {
    this.trackEvent('performance_timing', {
      metric: metricName,
      durationMs: Math.round(durationMs)
    });
  }
}

export const analytics = new TelemetryTracker();
export default analytics;
