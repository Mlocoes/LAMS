"""
Data retention and cleanup jobs for LAMS

This module provides functions to:
1. Delete old metrics beyond retention period
2. Aggregate metrics for long-term storage
3. Maintain database size and performance
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from database.database import async_session_maker
from database.models import Metric, MetricAggregated

logger = logging.getLogger(__name__)


async def cleanup_old_metrics() -> Dict[str, Any]:
    """
    Delete metrics older than METRICS_RETENTION_DAYS.
    
    Returns:
        Dict with cleanup statistics
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=settings.METRICS_RETENTION_DAYS)
        
        async with async_session_maker() as session:
            # Count metrics to be deleted
            count_stmt = select(func.count(Metric.id)).where(Metric.timestamp < cutoff_date)
            result = await session.execute(count_stmt)
            count_before = result.scalar()
            
            # Delete old metrics
            delete_stmt = delete(Metric).where(Metric.timestamp < cutoff_date)
            await session.execute(delete_stmt)
            await session.commit()
            
            logger.info(f"✅ Cleanup: Deleted {count_before} metrics older than {settings.METRICS_RETENTION_DAYS} days")
            
            return {
                "status": "success",
                "deleted_count": count_before,
                "cutoff_date": cutoff_date.isoformat(),
                "retention_days": settings.METRICS_RETENTION_DAYS
            }
    
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


async def aggregate_metrics() -> Dict[str, Any]:
    """
    Aggregate metrics older than METRICS_AGGREGATION_DAYS into hourly summaries.
    
    This reduces storage by replacing individual metric samples with aggregated data
    (avg, min, max) grouped by hour.
    
    Returns:
        Dict with aggregation statistics
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=settings.METRICS_AGGREGATION_DAYS)
        
        async with async_session_maker() as session:
            # Get distinct hosts with old metrics
            hosts_stmt = select(Metric.host_id).where(
                Metric.timestamp < cutoff_date
            ).distinct()
            hosts_result = await session.execute(hosts_stmt)
            host_ids = [row[0] for row in hosts_result.fetchall()]
            
            total_aggregated = 0
            total_deleted = 0
            
            for host_id in host_ids:
                # Aggregate metrics for this host
                stats = await _aggregate_host_metrics(session, host_id, cutoff_date)
                total_aggregated += stats["aggregated"]
                total_deleted += stats["deleted"]
            
            logger.info(
                f"✅ Aggregation: Created {total_aggregated} aggregated records, "
                f"deleted {total_deleted} raw metrics for {len(host_ids)} hosts"
            )
            
            return {
                "status": "success",
                "hosts_processed": len(host_ids),
                "aggregated_records": total_aggregated,
                "deleted_raw_metrics": total_deleted,
                "cutoff_date": cutoff_date.isoformat(),
                "aggregation_days": settings.METRICS_AGGREGATION_DAYS
            }
    
    except Exception as e:
        logger.error(f"❌ Error during aggregation: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }


async def _aggregate_host_metrics(
    session: AsyncSession,
    host_id: str,
    cutoff_date: datetime
) -> Dict[str, int]:
    """
    Aggregate metrics for a specific host.
    
    Groups metrics by hour and creates aggregated records with avg/min/max values.
    
    Args:
        session: Database session
        host_id: Host identifier
        cutoff_date: Only aggregate metrics before this date
    
    Returns:
        Dict with counts of aggregated and deleted records
    """
    # Get all metrics for this host before cutoff date
    metrics_stmt = select(Metric).where(
        Metric.host_id == host_id,
        Metric.timestamp < cutoff_date
    ).order_by(Metric.timestamp)
    
    result = await session.execute(metrics_stmt)
    metrics = result.scalars().all()
    
    if not metrics:
        return {"aggregated": 0, "deleted": 0}
    
    # Group metrics by hour
    hourly_groups = {}
    for metric in metrics:
        # Truncate to hour
        hour_key = metric.timestamp.replace(minute=0, second=0, microsecond=0)
        if hour_key not in hourly_groups:
            hourly_groups[hour_key] = []
        hourly_groups[hour_key].append(metric)
    
    # Create aggregated records
    aggregated_count = 0
    for hour_timestamp, hour_metrics in hourly_groups.items():
        # Check if aggregation already exists
        existing_stmt = select(MetricAggregated).where(
            MetricAggregated.host_id == host_id,
            MetricAggregated.timestamp == hour_timestamp,
            MetricAggregated.period == "hourly"
        )
        existing_result = await session.execute(existing_stmt)
        if existing_result.scalar_one_or_none():
            continue  # Skip if already aggregated
        
        # Calculate aggregated values
        cpu_values = [m.cpu_usage for m in hour_metrics if m.cpu_usage is not None]
        memory_values = [m.memory_used for m in hour_metrics if m.memory_used is not None]
        disk_values = [m.disk_usage_percent for m in hour_metrics if m.disk_usage_percent is not None]
        temp_values = [m.temp_cpu for m in hour_metrics if m.temp_cpu is not None]
        net_rx_values = [m.net_rx for m in hour_metrics if m.net_rx is not None]
        net_tx_values = [m.net_tx for m in hour_metrics if m.net_tx is not None]
        
        # Create aggregated record
        aggregated = MetricAggregated(
            host_id=host_id,
            timestamp=hour_timestamp,
            period="hourly",
            cpu_usage_avg=sum(cpu_values) / len(cpu_values) if cpu_values else None,
            cpu_usage_min=min(cpu_values) if cpu_values else None,
            cpu_usage_max=max(cpu_values) if cpu_values else None,
            memory_used_avg=sum(memory_values) / len(memory_values) if memory_values else None,
            memory_used_min=min(memory_values) if memory_values else None,
            memory_used_max=max(memory_values) if memory_values else None,
            disk_usage_percent_avg=sum(disk_values) / len(disk_values) if disk_values else None,
            disk_usage_percent_min=min(disk_values) if disk_values else None,
            disk_usage_percent_max=max(disk_values) if disk_values else None,
            temp_cpu_avg=sum(temp_values) / len(temp_values) if temp_values else None,
            temp_cpu_min=min(temp_values) if temp_values else None,
            temp_cpu_max=max(temp_values) if temp_values else None,
            net_rx_total=sum(net_rx_values) if net_rx_values else None,
            net_tx_total=sum(net_tx_values) if net_tx_values else None,
            sample_count=len(hour_metrics)
        )
        
        session.add(aggregated)
        aggregated_count += 1
    
    # Commit aggregated records
    await session.commit()
    
    # Delete raw metrics that were aggregated
    deleted_count = len(metrics)
    if aggregated_count > 0:
        delete_stmt = delete(Metric).where(
            Metric.host_id == host_id,
            Metric.timestamp < cutoff_date
        )
        await session.execute(delete_stmt)
        await session.commit()
    
    return {
        "aggregated": aggregated_count,
        "deleted": deleted_count
    }


async def run_maintenance_job() -> Dict[str, Any]:
    """
    Run complete maintenance job: aggregate old metrics, then cleanup very old ones.
    
    This is the main entry point for scheduled maintenance tasks.
    
    Returns:
        Dict with combined statistics from all maintenance operations
    """
    logger.info("🔧 Starting maintenance job...")
    
    start_time = datetime.now(timezone.utc)
    
    # Step 1: Aggregate old metrics (7-30 days) into hourly summaries
    aggregation_result = await aggregate_metrics()
    
    # Step 2: Delete very old metrics (>30 days)
    cleanup_result = await cleanup_old_metrics()
    
    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()
    
    logger.info(f"✅ Maintenance job completed in {duration:.2f} seconds")
    
    return {
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": duration,
        "aggregation": aggregation_result,
        "cleanup": cleanup_result
    }
