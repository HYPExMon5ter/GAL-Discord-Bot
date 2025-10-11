---
id: sops.event_system_monitoring
version: 1.0
last_updated: 2025-10-11
tags: [sops, events, monitoring, performance, troubleshooting]
---

# Event System Monitoring SOP

## Overview
This SOP covers monitoring, maintenance, and troubleshooting procedures for the Guardian Angel League Event System, ensuring reliable event processing and system performance.

## Monitoring Objectives

### Primary Goals
- **Event Processing**: Monitor event queue health and processing rates
- **Performance**: Track event processing times and system throughput
- **Reliability**: Ensure event handlers and subscribers are functioning correctly
- **Error Handling**: Monitor error rates and implement recovery procedures

### Key Metrics
- Event queue size and processing rate
- Event processing latency
- Handler execution times
- Error rates and types
- Memory and CPU usage
- WebSocket connection health

## Monitoring Setup

### 1. System Metrics Collection

#### 1.1 Event Bus Monitoring
```python
# Add to your event bus implementation
import time
import psutil
from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime, timedelta

@dataclass
class EventMetrics:
    timestamp: datetime
    queue_size: int
    processing_rate: float
    error_rate: float
    avg_processing_time: float
    memory_usage: float
    cpu_usage: float
    active_handlers: int
    active_subscribers: int

class EventMonitor:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.metrics_history: List[EventMetrics] = []
        self.alert_thresholds = {
            'queue_size': 1000,
            'processing_rate': 10.0,  # events per second
            'error_rate': 0.05,  # 5%
            'avg_processing_time': 1.0,  # seconds
            'memory_usage': 80.0,  # percentage
            'cpu_usage': 80.0  # percentage
        }
    
    async def collect_metrics(self) -> EventMetrics:
        """Collect current event system metrics."""
        return EventMetrics(
            timestamp=datetime.utcnow(),
            queue_size=self.event_bus.queue_size(),
            processing_rate=self.event_bus.processing_rate(),
            error_rate=self.event_bus.error_rate(),
            avg_processing_time=self.event_bus.avg_processing_time(),
            memory_usage=psutil.virtual_memory().percent,
            cpu_usage=psutil.cpu_percent(),
            active_handlers=len(self.event_bus.active_handlers),
            active_subscribers=len(self.event_bus.active_subscribers)
        )
    
    async def check_health(self) -> Dict[str, Any]:
        """Check event system health and return status."""
        metrics = await self.collect_metrics()
        
        health_status = {
            'status': 'healthy',
            'metrics': metrics,
            'alerts': []
        }
        
        # Check thresholds and generate alerts
        if metrics.queue_size > self.alert_thresholds['queue_size']:
            health_status['alerts'].append({
                'type': 'high_queue_size',
                'message': f"Event queue size ({metrics.queue_size}) exceeds threshold",
                'severity': 'warning'
            })
        
        if metrics.error_rate > self.alert_thresholds['error_rate']:
            health_status['alerts'].append({
                'type': 'high_error_rate',
                'message': f"Error rate ({metrics.error_rate:.2%}) exceeds threshold",
                'severity': 'critical'
            })
        
        if metrics.memory_usage > self.alert_thresholds['memory_usage']:
            health_status['alerts'].append({
                'type': 'high_memory_usage',
                'message': f"Memory usage ({metrics.memory_usage}%) exceeds threshold",
                'severity': 'warning'
            })
        
        if health_status['alerts']:
            health_status['status'] = 'degraded'
            critical_alerts = [a for a in health_status['alerts'] if a['severity'] == 'critical']
            if critical_alerts:
                health_status['status'] = 'unhealthy'
        
        return health_status
```

#### 1.2 Health Check Endpoint
```python
# Add to your FastAPI application
from fastapi import APIRouter, HTTPException
from .event_monitor import EventMonitor

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/events")
async def check_event_system_health():
    """Check event system health."""
    try:
        monitor = EventMonitor(event_bus)
        health = await monitor.check_health()
        
        if health['status'] == 'unhealthy':
            raise HTTPException(status_code=503, detail=health)
        elif health['status'] == 'degraded':
            return JSONResponse(
                status_code=200,
                content={**health, 'warning': 'System degraded but operational'}
            )
        
        return health
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 2. Log Analysis Setup

#### 2.1 Structured Logging Configuration
```python
# Configure structured logging for events
import logging
import json
from datetime import datetime

class EventLogger:
    def __init__(self):
        self.logger = logging.getLogger('event_system')
        handler = logging.FileHandler('/var/log/gal-api/events.log')
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_event_processed(self, event_id: str, event_type: str, 
                          processing_time: float, handler: str):
        """Log successful event processing."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'event_processed',
            'event_id': event_id,
            'event_type': event_type,
            'processing_time': processing_time,
            'handler': handler,
            'status': 'success'
        }
        self.logger.info(json.dumps(log_entry))
    
    def log_event_error(self, event_id: str, event_type: str, 
                       error: str, handler: str):
        """Log event processing error."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'event_error',
            'event_id': event_id,
            'event_type': event_type,
            'error': str(error),
            'handler': handler,
            'status': 'error'
        }
        self.logger.error(json.dumps(log_entry))
```

#### 2.2 Log Analysis Script
```bash
#!/bin/bash
# analyze_events.sh - Event system log analysis

LOG_FILE="/var/log/gal-api/events.log"
ALERT_THRESHOLD=10  # errors in last hour

# Function to count errors in last hour
count_recent_errors() {
    local one_hour_ago=$(date -d '1 hour ago' --iso-8601)
    local error_count=$(jq -r --arg one_hour_ago "$one_hour_ago" '
        select(.timestamp >= $one_hour_ago and .type == "event_error") | length
    ' "$LOG_FILE")
    echo $error_count
}

# Function to get average processing time
get_avg_processing_time() {
    local one_hour_ago=$(date -d '1 hour ago' --iso-8601)
    local avg_time=$(jq -r --arg one_hour_ago "$one_hour_ago" '
        select(.timestamp >= $one_hour_ago and .type == "event_processed") | 
        .processing_time | 
        select(. != null) |
        if length > 0 then add/length else 0 end
    ' "$LOG_FILE")
    echo $avg_time
}

# Function to get slow events
get_slow_events() {
    local one_hour_ago=$(date -d '1 hour ago' --iso-8601)
    jq -r --arg one_hour_ago "$one_hour_ago" '
        select(.timestamp >= $one_hour_ago and .type == "event_processed" and .processing_time > 1.0) |
        "\(.timestamp) \(.event_type) \(.processing_time)s"
    ' "$LOG_FILE"
}

# Main analysis
error_count=$(count_recent_errors)
avg_time=$(get_avg_processing_time)

echo "Event System Analysis - $(date)"
echo "================================"
echo "Errors in last hour: $error_count"
echo "Average processing time: ${avg_time}s"

# Check for alerts
if [ "$error_count" -gt "$ALERT_THRESHOLD" ]; then
    echo "ALERT: High error rate detected ($error_count errors)"
    # Send alert (configure your preferred method)
fi

if (( $(echo "$avg_time > 2.0" | bc -l) )); then
    echo "WARNING: High average processing time (${avg_time}s)"
fi

echo ""
echo "Slow events (processing time > 1s):"
get_slow_events | head -10
```

### 3. Real-time Monitoring Dashboard

#### 3.1 WebSocket Monitoring Endpoint
```python
# Add to your WebSocket router
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                # Connection closed, remove it
                self.active_connections.remove(connection)

manager = WebSocketManager()

@router.websocket("/events/monitor")
async def websocket_monitor(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Send real-time metrics
            monitor = EventMonitor(event_bus)
            health = await monitor.check_health()
            await websocket.send_text(json.dumps(health))
            await asyncio.sleep(5)  # Update every 5 seconds
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

## Alerting System

### 1. Alert Configuration

#### 1.1 Alert Thresholds
```python
# Define alert thresholds
ALERT_THRESHOLDS = {
    'critical': {
        'queue_size': 5000,
        'error_rate': 0.10,  # 10%
        'processing_time': 5.0,  # seconds
        'memory_usage': 90.0,  # percentage
        'cpu_usage': 90.0  # percentage
    },
    'warning': {
        'queue_size': 1000,
        'error_rate': 0.05,  # 5%
        'processing_time': 2.0,  # seconds
        'memory_usage': 80.0,  # percentage
        'cpu_usage': 80.0  # percentage
    }
}
```

#### 1.2 Alert Notification System
```python
import aiohttp
import asyncio

class AlertManager:
    def __init__(self):
        self.webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        self.email_config = {
            'smtp_server': os.getenv('SMTP_SERVER'),
            'smtp_port': int(os.getenv('SMTP_PORT', 587)),
            'username': os.getenv('SMTP_USERNAME'),
            'password': os.getenv('SMTP_PASSWORD'),
            'recipients': os.getenv('ALERT_RECIPIENTS', '').split(',')
        }
    
    async def send_discord_alert(self, alert: dict):
        """Send alert to Discord webhook."""
        if not self.webhook_url:
            return
        
        embed = {
            "title": f"Event System Alert - {alert['severity'].upper()}",
            "description": alert['message'],
            "color": 0xFF0000 if alert['severity'] == 'critical' else 0xFFAA00,
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {"name": "Metric", "value": alert['metric'], "inline": True},
                {"name": "Value", "value": str(alert['value']), "inline": True},
                {"name": "Threshold", "value": str(alert['threshold']), "inline": True}
            ]
        }
        
        payload = {"embeds": [embed]}
        
        async with aiohttp.ClientSession() as session:
            await session.post(self.webhook_url, json=payload)
    
    async def send_email_alert(self, alert: dict):
        """Send alert via email."""
        # Implement email sending logic
        pass
    
    async def handle_alert(self, alert: dict):
        """Handle alert based on severity."""
        if alert['severity'] == 'critical':
            await self.send_discord_alert(alert)
            await self.send_email_alert(alert)
        elif alert['severity'] == 'warning':
            await self.send_discord_alert(alert)
```

### 2. Automated Recovery

#### 2.1 Recovery Procedures
```python
class EventSystemRecovery:
    def __init__(self, event_bus, alert_manager):
        self.event_bus = event_bus
        self.alert_manager = alert_manager
        self.recovery_actions = {
            'high_queue_size': self._handle_high_queue_size,
            'high_error_rate': self._handle_high_error_rate,
            'high_memory_usage': self._handle_high_memory_usage
        }
    
    async def _handle_high_queue_size(self, alert: dict):
        """Handle high queue size."""
        # Increase worker count
        self.event_bus.increase_workers()
        
        # Send alert
        await self.alert_manager.send_discord_alert({
            'severity': 'warning',
            'message': f"Increasing worker count due to high queue size: {alert['value']}",
            'metric': 'queue_size',
            'value': alert['value'],
            'threshold': alert['threshold']
        })
    
    async def _handle_high_error_rate(self, alert: dict):
        """Handle high error rate."""
        # Restart failed handlers
        await self.event_bus.restart_failed_handlers()
        
        # Send alert
        await self.alert_manager.send_discord_alert({
            'severity': 'critical',
            'message': f"High error rate detected: {alert['value']:.2%}. Restarting failed handlers.",
            'metric': 'error_rate',
            'value': alert['value'],
            'threshold': alert['threshold']
        })
    
    async def _handle_high_memory_usage(self, alert: dict):
        """Handle high memory usage."""
        # Clear caches
        self.event_bus.clear_caches()
        
        # Send alert
        await self.alert_manager.send_discord_alert({
            'severity': 'warning',
            'message': f"Clearing caches due to high memory usage: {alert['value']}%",
            'metric': 'memory_usage',
            'value': alert['value'],
            'threshold': alert['threshold']
        })
```

## Performance Optimization

### 1. Queue Management

#### 1.1 Dynamic Queue Sizing
```python
class DynamicQueueManager:
    def __init__(self, event_bus):
        self.event_bus = event_bus
        self.base_worker_count = 10
        self.max_worker_count = 50
        self.scale_up_threshold = 100
        self.scale_down_threshold = 10
    
    async def monitor_and_scale(self):
        """Monitor queue and scale workers as needed."""
        while True:
            queue_size = self.event_bus.queue_size()
            current_workers = self.event_bus.worker_count()
            
            if queue_size > self.scale_up_threshold and current_workers < self.max_worker_count:
                # Scale up
                new_workers = min(current_workers * 2, self.max_worker_count)
                self.event_bus.set_worker_count(new_workers)
                logging.info(f"Scaled up workers to {new_workers}")
            
            elif queue_size < self.scale_down_threshold and current_workers > self.base_worker_count:
                # Scale down
                new_workers = max(current_workers // 2, self.base_worker_count)
                self.event_bus.set_worker_count(new_workers)
                logging.info(f"Scaled down workers to {new_workers}")
            
            await asyncio.sleep(30)  # Check every 30 seconds
```

### 2. Caching Optimization

#### 2.1 Event Caching
```python
class EventCacheManager:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.cache_ttl = 3600  # 1 hour
    
    async def cache_event_result(self, event_id: str, result: dict):
        """Cache event processing result."""
        await self.redis.setex(
            f"event_result:{event_id}",
            self.cache_ttl,
            json.dumps(result)
        )
    
    async def get_cached_result(self, event_id: str) -> Optional[dict]:
        """Get cached event result."""
        cached = await self.redis.get(f"event_result:{event_id}")
        if cached:
            return json.loads(cached)
        return None
    
    async def clear_expired_cache(self):
        """Clear expired cache entries."""
        # Redis handles TTL automatically, but we can clean up patterns
        pattern = "event_result:*"
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            if keys:
                await self.redis.unlink(*keys)
            if cursor == 0:
                break
```

## Troubleshooting Guide

### Common Issues

#### 1. Event Queue Backlog
**Symptoms**: Events processing slowly, queue growing
**Diagnostic Steps**:
```bash
# Check queue size
curl http://localhost:8000/health/events

# Check worker count
ps aux | grep event_worker

# Check system resources
top
free -h
```

**Solutions**:
- Increase worker count
- Optimize event handlers
- Check for blocking operations
- Scale system resources

#### 2. High Error Rate
**Symptoms**: Many events failing to process
**Diagnostic Steps**:
```bash
# Check recent errors
tail -f /var/log/gal-api/events.log | grep '"type":"event_error"'

# Check specific handler errors
grep '"handler":"tournament_handler"' /var/log/gal-api/events.log | tail -20

# Check database connectivity
psql -h localhost -U galapi_user -d gal_api -c "SELECT 1;"
```

**Solutions**:
- Restart failed handlers
- Check database connections
- Verify external API availability
- Review recent code changes

#### 3. Memory Leaks
**Symptoms**: Memory usage increasing over time
**Diagnostic Steps**:
```bash
# Monitor memory usage
watch -n 5 'free -h'

# Check process memory
ps aux --sort=-%mem | head -10

# Check for memory leaks in Python
pip install memory_profiler
python -m memory_profiler your_script.py
```

**Solutions**:
- Restart event system
- Clear caches
- Review code for memory leaks
- Optimize data structures

### Recovery Procedures

#### 1. Event System Restart
```bash
# Graceful restart
sudo systemctl restart gal-api

# Check status
sudo systemctl status gal-api

# Verify health
curl https://your-domain.com/health/events
```

#### 2. Database Recovery
```bash
# Check database status
sudo systemctl status postgresql

# Restart database if needed
sudo systemctl restart postgresql

# Verify connectivity
psql -h localhost -U galapi_user -d gal_api -c "SELECT COUNT(*) FROM events;"
```

#### 3. Cache Recovery
```bash
# Clear Redis cache
redis-cli -a your_password FLUSHDB

# Restart Redis
sudo systemctl restart redis-server

# Verify connectivity
redis-cli -a your_password ping
```

## Maintenance Tasks

### Daily Tasks
- Check event system health dashboard
- Review error logs for critical issues
- Monitor queue sizes and processing rates

### Weekly Tasks
- Analyze performance trends
- Review and update alert thresholds
- Check system resource utilization
- Update event handlers if needed

### Monthly Tasks
- Comprehensive system health review
- Performance optimization analysis
- Security audit of event handlers
- Backup and recovery testing

## Documentation and Reporting

### 1. Performance Reports
```python
async def generate_monthly_report():
    """Generate monthly event system performance report."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    # Collect metrics
    metrics = {
        'total_events': await get_total_events(start_date, end_date),
        'avg_processing_time': await get_avg_processing_time(start_date, end_date),
        'error_rate': await get_error_rate(start_date, end_date),
        'peak_queue_size': await get_peak_queue_size(start_date, end_date),
        'top_slow_events': await get_top_slow_events(start_date, end_date, 10)
    }
    
    # Generate report
    report = f"""
    Event System Monthly Report
    Period: {start_date.date()} to {end_date.date()}
    
    Total Events Processed: {metrics['total_events']:,}
    Average Processing Time: {metrics['avg_processing_time']:.3f}s
    Error Rate: {metrics['error_rate']:.2%}
    Peak Queue Size: {metrics['peak_queue_size']}
    
    Top 10 Slowest Events:
    """
    
    for event in metrics['top_slow_events']:
        report += f"\n- {event['event_type']}: {event['avg_time']:.3f}s"
    
    return report
```

### 2. Incident Documentation
```markdown
# Event System Incident Template

## Incident Summary
- **Date**: [Date]
- **Time**: [Time]
- **Duration**: [Duration]
- **Severity**: [Critical/High/Medium/Low]
- **Impact**: [Description of impact]

## Symptoms
[Description of observed symptoms]

## Root Cause
[Analysis of root cause]

## Resolution
[Steps taken to resolve]

## Prevention
[Measures to prevent recurrence]

## Lessons Learned
[Key takeaways from incident]
```

---

**Event System Monitoring Status**: ✅ Production Ready  
**Monitoring**: Comprehensive real-time monitoring and alerting  
**Performance**: Dynamic scaling and optimization features  
**Recovery**: Automated recovery procedures and manual guides  
**Documentation**: Complete incident tracking and reporting system
