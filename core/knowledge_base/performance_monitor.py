#!/usr/bin/env python3
"""
Performance Monitor for Knowledge Base RAG System

This module provides performance monitoring and optimization features:
- Response time tracking
- Memory usage monitoring
- Query performance analysis
- Bottleneck detection
- Performance metrics collection
"""

import time
import threading
import psutil
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from collections import deque, defaultdict
from contextlib import contextmanager
import statistics

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Represents a performance metric."""
    name: str
    value: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationStats:
    """Statistics for a specific operation."""
    operation_name: str
    total_calls: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    recent_times: deque = field(default_factory=lambda: deque(maxlen=100))
    error_count: int = 0
    
    def add_measurement(self, duration: float, success: bool = True):
        """Add a new measurement."""
        self.total_calls += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        self.recent_times.append(duration)
        
        if not success:
            self.error_count += 1
    
    @property
    def average_time(self) -> float:
        """Get average execution time."""
        return self.total_time / self.total_calls if self.total_calls > 0 else 0.0
    
    @property
    def recent_average_time(self) -> float:
        """Get recent average execution time."""
        return statistics.mean(self.recent_times) if self.recent_times else 0.0
    
    @property
    def success_rate(self) -> float:
        """Get success rate percentage."""
        return ((self.total_calls - self.error_count) / self.total_calls * 100) if self.total_calls > 0 else 100.0
    
    def get_percentiles(self) -> Dict[str, float]:
        """Get performance percentiles."""
        if not self.recent_times:
            return {}
        
        sorted_times = sorted(self.recent_times)
        length = len(sorted_times)
        
        return {
            'p50': sorted_times[int(length * 0.5)] if length > 0 else 0,
            'p90': sorted_times[int(length * 0.9)] if length > 0 else 0,
            'p95': sorted_times[int(length * 0.95)] if length > 0 else 0,
            'p99': sorted_times[int(length * 0.99)] if length > 0 else 0
        }


class PerformanceMonitor:
    """Main performance monitoring class."""
    
    def __init__(self, max_metrics: int = 10000):
        self.max_metrics = max_metrics
        self._metrics: deque = deque(maxlen=max_metrics)
        self._operation_stats: Dict[str, OperationStats] = defaultdict(OperationStats)
        self._lock = threading.RLock()
        self._start_time = time.time()
        
        # System monitoring
        self._process = psutil.Process()
        self._system_metrics_interval = 60  # seconds
        self._last_system_check = 0
        
        logger.info("Performance monitor initialized")
    
    @contextmanager
    def measure_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """Context manager to measure operation performance."""
        start_time = time.time()
        success = True
        error = None
        
        try:
            yield
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            end_time = time.time()
            duration = end_time - start_time
            
            # Record the measurement
            self.record_operation(operation_name, duration, success, metadata or {})
            
            if error:
                logger.warning(f"Operation {operation_name} failed: {error}")
    
    def record_operation(self, operation_name: str, duration: float, success: bool = True, metadata: Optional[Dict[str, Any]] = None):
        """Record an operation measurement."""
        with self._lock:
            # Update operation stats
            if operation_name not in self._operation_stats:
                self._operation_stats[operation_name] = OperationStats(operation_name)
            
            self._operation_stats[operation_name].add_measurement(duration, success)
            
            # Add to metrics history
            metric = PerformanceMetric(
                name=operation_name,
                value=duration,
                timestamp=time.time(),
                metadata=metadata or {}
            )
            self._metrics.append(metric)
            
            logger.debug(f"Recorded {operation_name}: {duration:.3f}s (success: {success})")
    
    def record_metric(self, name: str, value: float, metadata: Optional[Dict[str, Any]] = None):
        """Record a custom metric."""
        with self._lock:
            metric = PerformanceMetric(
                name=name,
                value=value,
                timestamp=time.time(),
                metadata=metadata or {}
            )
            self._metrics.append(metric)
    
    def get_operation_stats(self, operation_name: str) -> Optional[OperationStats]:
        """Get statistics for a specific operation."""
        with self._lock:
            return self._operation_stats.get(operation_name)
    
    def get_all_operation_stats(self) -> Dict[str, OperationStats]:
        """Get statistics for all operations."""
        with self._lock:
            return dict(self._operation_stats)
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system performance metrics."""
        try:
            # CPU usage
            cpu_percent = self._process.cpu_percent()
            
            # Memory usage
            memory_info = self._process.memory_info()
            memory_percent = self._process.memory_percent()
            
            # System-wide metrics
            system_cpu = psutil.cpu_percent()
            system_memory = psutil.virtual_memory()
            
            return {
                'process': {
                    'cpu_percent': cpu_percent,
                    'memory_rss_mb': memory_info.rss / 1024 / 1024,
                    'memory_vms_mb': memory_info.vms / 1024 / 1024,
                    'memory_percent': memory_percent
                },
                'system': {
                    'cpu_percent': system_cpu,
                    'memory_percent': system_memory.percent,
                    'memory_available_mb': system_memory.available / 1024 / 1024,
                    'memory_total_mb': system_memory.total / 1024 / 1024
                },
                'timestamp': time.time()
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        with self._lock:
            current_time = time.time()
            uptime = current_time - self._start_time
            
            # Operation summaries
            operation_summaries = {}
            for name, stats in self._operation_stats.items():
                operation_summaries[name] = {
                    'total_calls': stats.total_calls,
                    'average_time': stats.average_time,
                    'recent_average_time': stats.recent_average_time,
                    'min_time': stats.min_time if stats.min_time != float('inf') else 0,
                    'max_time': stats.max_time,
                    'success_rate': stats.success_rate,
                    'error_count': stats.error_count,
                    'percentiles': stats.get_percentiles()
                }
            
            # Recent metrics
            recent_metrics = list(self._metrics)[-100:]  # Last 100 metrics
            
            # System metrics
            system_metrics = self.get_system_metrics()
            
            return {
                'uptime_seconds': uptime,
                'total_metrics': len(self._metrics),
                'operations': operation_summaries,
                'recent_metrics_count': len(recent_metrics),
                'system_metrics': system_metrics,
                'timestamp': current_time
            }
    
    def detect_performance_issues(self) -> List[Dict[str, Any]]:
        """Detect potential performance issues."""
        issues = []
        
        with self._lock:
            # Check for slow operations
            for name, stats in self._operation_stats.items():
                if stats.recent_average_time > 5.0:  # More than 5 seconds
                    issues.append({
                        'type': 'slow_operation',
                        'operation': name,
                        'average_time': stats.recent_average_time,
                        'severity': 'high' if stats.recent_average_time > 10.0 else 'medium'
                    })
                
                # Check for high error rates
                if stats.success_rate < 90.0 and stats.total_calls > 10:
                    issues.append({
                        'type': 'high_error_rate',
                        'operation': name,
                        'success_rate': stats.success_rate,
                        'error_count': stats.error_count,
                        'severity': 'high' if stats.success_rate < 50.0 else 'medium'
                    })
        
        # Check system metrics
        system_metrics = self.get_system_metrics()
        if system_metrics:
            process_metrics = system_metrics.get('process', {})
            
            # High memory usage
            if process_metrics.get('memory_percent', 0) > 80:
                issues.append({
                    'type': 'high_memory_usage',
                    'memory_percent': process_metrics['memory_percent'],
                    'memory_mb': process_metrics.get('memory_rss_mb', 0),
                    'severity': 'high' if process_metrics['memory_percent'] > 90 else 'medium'
                })
            
            # High CPU usage
            if process_metrics.get('cpu_percent', 0) > 80:
                issues.append({
                    'type': 'high_cpu_usage',
                    'cpu_percent': process_metrics['cpu_percent'],
                    'severity': 'high' if process_metrics['cpu_percent'] > 95 else 'medium'
                })
        
        return issues
    
    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """Get optimization suggestions based on performance data."""
        suggestions = []
        
        with self._lock:
            # Analyze operation patterns
            for name, stats in self._operation_stats.items():
                # Suggest caching for frequently called operations
                if stats.total_calls > 100 and stats.average_time > 1.0:
                    suggestions.append({
                        'type': 'caching',
                        'operation': name,
                        'reason': f'Operation called {stats.total_calls} times with average time {stats.average_time:.2f}s',
                        'priority': 'high' if stats.total_calls > 1000 else 'medium'
                    })
                
                # Suggest optimization for slow operations
                if stats.recent_average_time > 3.0:
                    suggestions.append({
                        'type': 'optimization',
                        'operation': name,
                        'reason': f'Recent average time is {stats.recent_average_time:.2f}s',
                        'priority': 'high' if stats.recent_average_time > 10.0 else 'medium'
                    })
        
        # System-level suggestions
        system_metrics = self.get_system_metrics()
        if system_metrics:
            process_metrics = system_metrics.get('process', {})
            
            if process_metrics.get('memory_percent', 0) > 70:
                suggestions.append({
                    'type': 'memory_optimization',
                    'reason': f'Memory usage is {process_metrics["memory_percent"]:.1f}%',
                    'priority': 'medium'
                })
        
        return suggestions
    
    def reset_stats(self):
        """Reset all performance statistics."""
        with self._lock:
            self._metrics.clear()
            self._operation_stats.clear()
            self._start_time = time.time()
            logger.info("Performance statistics reset")
    
    def export_metrics(self, format: str = 'json') -> str:
        """Export metrics in specified format."""
        summary = self.get_performance_summary()
        
        if format.lower() == 'json':
            import json
            return json.dumps(summary, indent=2, default=str)
        elif format.lower() == 'csv':
            # Simple CSV export for operations
            lines = ['operation,total_calls,average_time,success_rate,error_count']
            for name, stats in summary['operations'].items():
                lines.append(f"{name},{stats['total_calls']},{stats['average_time']:.3f},{stats['success_rate']:.1f},{stats['error_count']}")
            return '\n'.join(lines)
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None
_monitor_lock = threading.Lock()


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _performance_monitor
    
    with _monitor_lock:
        if _performance_monitor is None:
            _performance_monitor = PerformanceMonitor()
        return _performance_monitor


def measure_operation(operation_name: str, metadata: Optional[Dict[str, Any]] = None):
    """Decorator to measure operation performance."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            with monitor.measure_operation(operation_name, metadata):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def record_metric(name: str, value: float, metadata: Optional[Dict[str, Any]] = None):
    """Record a custom metric."""
    monitor = get_performance_monitor()
    monitor.record_metric(name, value, metadata)