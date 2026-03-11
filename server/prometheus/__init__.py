"""
Prometheus metrics exporter for LAMS.

This module exposes LAMS metrics in Prometheus format for integration
with Prometheus monitoring and Grafana visualization.
"""

from .exporter import (
    update_prometheus_metrics,
    generate_prometheus_metrics,
    registry
)

__all__ = [
    'update_prometheus_metrics',
    'generate_prometheus_metrics',
    'registry'
]
