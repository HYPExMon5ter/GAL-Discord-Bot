---
id: sops.performance-monitoring-sop
version: 1.0
last_updated: 2025-10-14
tags: [performance, monitoring, metrics, optimization, alerting]
---

# Performance Monitoring SOP

## Overview

This Standard Operating Procedure (SOP) outlines the performance monitoring processes for the Guardian Angel League Live Graphics Dashboard project. The process ensures optimal system performance, proactive issue identification, and systematic performance optimization.

## Scope

This SOP applies to:
- Application performance monitoring (APM)
- Database performance monitoring
- Frontend performance monitoring
- Infrastructure performance monitoring
- User experience monitoring
- Performance baseline establishment

## Monitoring Architecture

### System Components Monitored
```yaml
monitored_components:
  frontend:
    - "Page load times"
    - "Component render times"
    - "User interaction responses"
    - "Bundle size and loading"
    - "Browser performance metrics"
    
  backend:
    - "API response times"
    - "Database query performance"
    - "Memory usage patterns"
    - "CPU utilization"
    - "Error rates and types"
    
  database:
    - "Query execution times"
    - "Connection pool usage"
    - "Database size growth"
    - "Index performance"
    - "Lock contention"
    
  infrastructure:
    - "Server resource utilization"
    - "Network latency and throughput"
    - "Disk I/O performance"
    - "Application memory usage"
    - "System health metrics"
```

### Monitoring Stack
```yaml
monitoring_tools:
  application_monitoring:
    - "Application logs"
    - "Performance metrics"
    - "Error tracking"
    - "Custom metrics"
    
  frontend_monitoring:
    - "Core Web Vitals"
    - "User interaction timing"
    - "JavaScript errors"
    - "Resource loading metrics"
    
  infrastructure_monitoring:
    - "System metrics collection"
    - "Resource utilization"
    - "Network monitoring"
    - "Service health checks"
    
  alerting:
    - "Threshold-based alerts"
    - "Anomaly detection"
    - "Multi-channel notifications"
    - "Escalation procedures"
```

## Performance Metrics and KPIs

### Frontend Performance Metrics

#### Core Web Vitals
```typescript
// Core Web Vitals monitoring
interface CoreWebVitals {
  LCP: LargestContentfulPaint;  // < 2.5s
  FID: FirstInputDelay;         // < 100ms
  CLS: CumulativeLayoutShift;  // < 0.1
  FCP: FirstContentfulPaint;   // < 1.8s
  TTFB: TimeToFirstByte;        // < 600ms
}

// Performance monitoring implementation
class PerformanceMonitor {
  measureWebVitals(): void {
    // Measure LCP
    new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const lastEntry = entries[entries.length - 1];
      this.reportMetric('LCP', lastEntry.startTime);
    }).observe({ entryTypes: ['largest-contentful-paint'] });
    
    // Measure FID
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        this.reportMetric('FID', entry.processingStart - entry.startTime);
      }
    }).observe({ entryTypes: ['first-input'] });
  }
}
```

#### Custom Frontend Metrics
```typescript
// Custom frontend performance metrics
interface FrontendMetrics {
  componentRenderTime: number;      // Component render performance
  apiResponseTime: number;          // API call performance
  stateUpdateTime: number;          // State management performance
  bundleLoadTime: number;           // Bundle loading performance
  userInteractionTime: number;      // User interaction responsiveness
}

// Component performance monitoring
export const withPerformanceMonitoring = <P extends object>(
  Component: React.ComponentType<P>,
  componentName: string
) => {
  return React.memo((props: P) => {
    const renderStart = performance.now();
    
    useEffect(() => {
      const renderTime = performance.now() - renderStart;
      reportMetric('component_render_time', renderTime, {
        component: componentName
      });
    });
    
    return <Component {...props} />;
  });
};
```

### Backend Performance Metrics

#### API Performance
```python
# API performance monitoring
import time
from functools import wraps
from prometheus_client import Counter, Histogram, Gauge

# Metrics definitions
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('api_request_duration_seconds', 'API request duration')
ACTIVE_CONNECTIONS = Gauge('api_active_connections', 'Active API connections')

def monitor_performance(func):
    """Decorator to monitor API performance"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            REQUEST_COUNT.labels(method='POST', endpoint=func.__name__, status='200').inc()
            return result
        except Exception as e:
            REQUEST_COUNT.labels(method='POST', endpoint=func.__name__, status='500').inc()
            raise
        finally:
            REQUEST_DURATION.observe(time.time() - start_time)
    
    return wrapper
```

#### Database Performance
```python
# Database performance monitoring
class DatabasePerformanceMonitor:
    def __init__(self, db_session):
        self.db = db_session
        self.query_times = []
    
    def monitor_query(self, query_func):
        """Monitor database query performance"""
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = query_func(*args, **kwargs)
                query_time = time.time() - start_time
                self.query_times.append(query_time)
                
                # Alert on slow queries
                if query_time > 1.0:  # 1 second threshold
                    self.alert_slow_query(query_func.__name__, query_time)
                
                return result
            except Exception as e:
                self.log_query_error(query_func.__name__, e)
                raise
        
        return wrapper
    
    def get_performance_stats(self):
        """Get database performance statistics"""
        if not self.query_times:
            return {}
        
        return {
            'avg_query_time': sum(self.query_times) / len(self.query_times),
            'max_query_time': max(self.query_times),
            'min_query_time': min(self.query_times),
            'total_queries': len(self.query_times)
        }
```

## Monitoring Implementation

### Frontend Monitoring Setup

#### Performance Observer Implementation
```typescript
// Performance monitoring setup
class PerformanceMonitoringService {
  private metrics: Map<string, number[]> = new Map();
  
  constructor() {
    this.initializeMonitoring();
  }
  
  private initializeMonitoring(): void {
    // Monitor page load performance
    window.addEventListener('load', () => {
      this.measurePageLoad();
    });
    
    // Monitor navigation performance
    this.measureNavigationTiming();
    
    // Monitor resource loading
    this.measureResourceTiming();
    
    // Monitor long tasks
    this.measureLongTasks();
  }
  
  private measurePageLoad(): void {
    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    const metrics = {
      domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
      loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
      firstPaint: performance.getEntriesByType('paint')[0]?.startTime || 0,
      firstContentfulPaint: performance.getEntriesByType('paint')[1]?.startTime || 0
    };
    
    this.reportMetrics('page_load', metrics);
  }
  
  private measureLongTasks(): void {
    if ('PerformanceObserver' in window) {
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          this.reportMetric('long_task', entry.duration, {
            name: entry.name,
            startTime: entry.startTime
          });
        }
      });
      
      observer.observe({ entryTypes: ['longtask'] });
    }
  }
}
```

### Backend Monitoring Setup

#### FastAPI Middleware
```python
# FastAPI performance monitoring middleware
from fastapi import Request, Response
import time
import logging

class PerformanceMonitoringMiddleware:
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(__name__)
    
    async def __call__(self, request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Add performance headers
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log performance metrics
        self.logger.info(
            f"Request: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.4f}s"
        )
        
        # Alert on slow requests
        if process_time > 2.0:  # 2 second threshold
            self.alert_slow_request(request, process_time)
        
        return response
    
    def alert_slow_request(self, request: Request, process_time: float):
        """Alert on slow requests"""
        self.logger.warning(
            f"Slow request detected: {request.method} {request.url.path} "
            f"took {process_time:.4f}s"
        )
        # Additional alerting logic here
```

## Alerting and Notification

### Alert Configuration

#### Performance Thresholds
```yaml
performance_thresholds:
  frontend:
    page_load_time:
      warning: 3.0  # seconds
      critical: 5.0  # seconds
    first_input_delay:
      warning: 200   # milliseconds
      critical: 500  # milliseconds
    cumulative_layout_shift:
      warning: 0.15
      critical: 0.25
      
  backend:
    api_response_time:
      warning: 1.0   # seconds
      critical: 3.0  # seconds
    error_rate:
      warning: 5%    # percentage
      critical: 10%  # percentage
      
  database:
    query_time:
      warning: 500   # milliseconds
      critical: 2000 # milliseconds
    connection_pool:
      warning: 80%   # utilization
      critical: 95%  # utilization
```

#### Alert Escalation
```python
# Alert escalation system
class AlertManager:
    def __init__(self):
        self.alert_levels = {
            'info': self.log_info,
            'warning': self.send_warning_notification,
            'critical': self.send_critical_alert
        }
    
    def handle_performance_alert(self, metric_name: str, value: float, threshold: dict):
        """Handle performance alert"""
        severity = self.determine_severity(value, threshold)
        
        alert_data = {
            'metric': metric_name,
            'value': value,
            'threshold': threshold,
            'timestamp': datetime.utcnow(),
            'severity': severity
        }
        
        # Trigger appropriate alert handler
        self.alert_levels[severity](alert_data)
    
    def send_critical_alert(self, alert_data: dict):
        """Send critical alert"""
        # Multiple notification channels
        self.send_email_alert(alert_data)
        self.send_slack_alert(alert_data)
        self.create_incident(alert_data)
        self.notify_on_call_engineer(alert_data)
```

### Notification Channels

#### Multi-Channel Notifications
```yaml
notification_channels:
  email:
    recipients:
      - "devops@guardianangelleague.com"
      - "backend-team@guardianangelleague.com"
    template: "performance_alert_email"
    
  slack:
    channel: "#performance-alerts"
    webhook_url: "${SLACK_WEBHOOK_URL}"
    template: "performance_alert_slack"
    
  pagerduty:
    service_key: "${PAGERDUTY_SERVICE_KEY}"
    severity: "critical"
    
  dashboard:
    url: "https://dashboard.guardianangelleague.com/alerts"
    real_time_updates: true
```

## Performance Optimization

### Proactive Performance Management

#### Performance Budgets
```typescript
// Performance budget configuration
const performanceBudgets = {
  // Bundle size budgets
  bundleSize: {
    total: 250 * 1024,      // 250KB total
    vendor: 100 * 1024,     // 100KB vendor
    main: 150 * 1024        // 150KB main
  },
  
  // Loading performance budgets
  loading: {
    firstContentfulPaint: 1500,  // 1.5s
    largestContentfulPaint: 2500, // 2.5s
    firstInputDelay: 100         // 100ms
  },
  
  // Runtime performance budgets
  runtime: {
    scriptingTime: 50,      // 50ms per frame
    renderingTime: 50,      // 50ms per frame
    paintingTime: 20        // 20ms per frame
  }
};

// Performance budget enforcement
function enforcePerformanceBudgets(metrics: any): void {
  const violations = [];
  
  // Check bundle size
  if (metrics.bundleSize.total > performanceBudgets.bundleSize.total) {
    violations.push({
      type: 'bundle_size',
      budget: performanceBudgets.bundleSize.total,
      actual: metrics.bundleSize.total,
      severity: 'warning'
    });
  }
  
  // Check loading performance
  if (metrics.loading.largestContentfulPaint > performanceBudgets.loading.largestContentfulPaint) {
    violations.push({
      type: 'lcp',
      budget: performanceBudgets.loading.largestContentfulPaint,
      actual: metrics.loading.largestContentfulPaint,
      severity: 'critical'
    });
  }
  
  // Report violations
  if (violations.length > 0) {
    reportPerformanceViolations(violations);
  }
}
```

#### Performance Optimization Checklist
```markdown
## Performance Optimization Checklist

### Frontend Optimization
- [ ] Code splitting implemented
- [ ] Lazy loading for routes and components
- [ ] Image optimization and lazy loading
- [ ] Bundle size analysis and optimization
- [ ] Service worker for caching
- [ ] CSS optimization and critical path CSS
- [ ] Font loading optimization

### Backend Optimization
- [ ] Database query optimization
- [ ] Caching strategies implemented
- [ ] API response compression
- [ ] Connection pooling optimized
- [ ] Async operations for I/O bound tasks
- [ ] Memory usage optimization
- [ ] Background job processing

### Database Optimization
- [ ] Index optimization
- [ ] Query plan analysis
- [ ] Connection pool tuning
- [ ] Database maintenance procedures
- [ ] Data archiving strategies
```

## Reporting and Analysis

### Performance Reports

#### Daily Performance Summary
```markdown
# Daily Performance Report - 2025-10-14

## Executive Summary
- **Overall Health**: Good
- **Critical Issues**: 0
- **Warnings**: 2
- **Performance Score**: 92/100

## Frontend Performance
- **Average Page Load Time**: 1.8s (Target: < 2.5s) ✅
- **First Contentful Paint**: 1.2s (Target: < 1.8s) ✅
- **Largest Contentful Paint**: 2.1s (Target: < 2.5s) ✅
- **Cumulative Layout Shift**: 0.08 (Target: < 0.1) ✅

## Backend Performance
- **Average API Response Time**: 245ms (Target: < 500ms) ✅
- **P95 Response Time**: 1.2s (Target: < 2s) ✅
- **Error Rate**: 0.8% (Target: < 1%) ✅
- **Throughput**: 1,250 req/min (Target: > 1,000 req/min) ✅

## Database Performance
- **Average Query Time**: 45ms (Target: < 100ms) ✅
- **Slow Queries**: 3 (Threshold: > 1s) ⚠️
- **Connection Pool Usage**: 65% (Target: < 80%) ✅
- **Database Size**: 2.3GB (Growth: +150MB this week)

## Alerts and Issues
1. **Slow Query Warning**: Graphics table query taking 1.2s
   - Status: Investigating
   - Impact: Minor
   
2. **Memory Usage Warning**: Frontend bundle approaching size limit
   - Status: Optimization planned
   - Impact: Minor

## Recommendations
1. Optimize slow graphics table query with better indexing
2. Review frontend bundle dependencies for optimization opportunities
3. Monitor database growth trend for capacity planning
```

#### Performance Trend Analysis
```python
# Performance trend analysis
class PerformanceAnalyzer:
    def analyze_performance_trends(self, time_period: str = '7d'):
        """Analyze performance trends over time period"""
        trends = {
            'response_time': self.calculate_trend('api_response_time', time_period),
            'error_rate': self.calculate_trend('error_rate', time_period),
            'throughput': self.calculate_trend('throughput', time_period),
            'user_experience': self.calculate_ux_trend(time_period)
        }
        
        return {
            'trends': trends,
            'anomalies': self.detect_anomalies(trends),
            'recommendations': self.generate_recommendations(trends)
        }
    
    def detect_performance_anomalies(self, metrics: dict):
        """Detect performance anomalies using statistical analysis"""
        anomalies = []
        
        for metric_name, values in metrics.items():
            # Use statistical methods to detect anomalies
            mean = np.mean(values)
            std_dev = np.std(values)
            threshold = mean + (2 * std_dev)  # 2 sigma threshold
            
            anomaly_indices = np.where(values > threshold)[0]
            
            if len(anomaly_indices) > 0:
                anomalies.append({
                    'metric': metric_name,
                    'anomalies': anomaly_indices.tolist(),
                    'severity': self.calculate_anomaly_severity(values, anomaly_indices)
                })
        
        return anomalies
```

## Capacity Planning

### Performance Scaling Analysis

#### Load Testing and Capacity Planning
```yaml
capacity_planning:
  current_capacity:
    concurrent_users: 100
    requests_per_minute: 1500
    database_connections: 50
    memory_usage: 60%
    cpu_usage: 45%
    
  projected_growth:
    monthly_growth_rate: 15%
    quarterly_growth_rate: 50%
    annual_growth_rate: 200%
    
  scaling_triggers:
    cpu_usage: > 70%
    memory_usage: > 80%
    response_time: > 2s
    error_rate: > 5%
    
  scaling_recommendations:
    database:
      - "Add read replicas for read-heavy operations"
      - "Implement database connection pooling optimization"
      - "Plan for database sharding at 500% growth"
      
    application:
      - "Implement horizontal scaling for API servers"
      - "Add Redis for session and caching"
      - "Optimize bundle size and implement CDN"
      
    infrastructure:
      - "Upgrade server specifications at 300% growth"
      - "Implement auto-scaling for traffic spikes"
      - "Add monitoring and alerting infrastructure"
```

## Incident Response

### Performance Incident Procedures

#### Performance Incident Response
```markdown
## Performance Incident Response Process

### Incident Classification
- **Severity 1 (Critical)**: System-wide performance degradation
- **Severity 2 (High)**: Significant performance impact
- **Severity 3 (Medium)**: Moderate performance issues
- **Severity 4 (Low)**: Minor performance concerns

### Response Timeline

#### Immediate Response (0-15 minutes)
1. **Incident Identification**
   - Automated alert detection
   - Manual verification
   - Impact assessment
   
2. **Initial Response**
   - Assemble response team
   - Establish communication channels
   - Begin initial diagnosis

#### Investigation (15-60 minutes)
1. **Performance Analysis**
   - Review performance metrics
   - Identify bottlenecks
   - Analyze system state
   
2. **Root Cause Analysis**
   - Identify root cause
   - Assess impact scope
   - Develop mitigation strategy

#### Resolution (60+ minutes)
1. **Implementation**
   - Apply fixes
   - Monitor improvements
   - Validate resolution
   
2. **Post-Incident**
   - Document incident
   - Update procedures
   - Implement preventive measures
```

## Continuous Improvement

### Performance Optimization Roadmap

#### Performance Improvement Initiatives
```markdown
## Performance Improvement Roadmap

### Short-term (1-3 months)
1. **Database Optimization**
   - Implement query optimization
   - Add strategic indexes
   - Optimize connection pooling

2. **Frontend Optimization**
   - Implement code splitting
   - Optimize bundle size
   - Add service worker caching

3. **Monitoring Enhancement**
   - Add custom metrics
   - Improve alerting
   - Implement dashboard

### Medium-term (3-6 months)
1. **Infrastructure Scaling**
   - Implement horizontal scaling
   - Add caching layer
   - Optimize CDN usage

2. **Performance Testing**
   - Implement load testing
   - Stress testing procedures
   - Capacity planning

### Long-term (6+ months)
1. **Architecture Optimization**
   - Microservices evaluation
   - Database optimization
   - Performance budgeting

2. **Advanced Monitoring**
   - AI-powered anomaly detection
   - Predictive performance analytics
   - Automated optimization
```

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-14  
**Related SOPs**: 
- [Integration Testing Procedures](./integration-testing-procedures.md)
- [Component Lifecycle Management](./component-lifecycle-management.md)
- [System Auditor](../droids/system_auditor.md)
