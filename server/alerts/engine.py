import asyncio
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.database import async_session_maker
from database.models import AlertRule, Metric, Alert, Host
from alerts.notifications import send_alert_notification

logger = logging.getLogger("lams.engine")

async def evaluate_rules():
    logger.info("Evaluating Alert Rules...")
    async with async_session_maker() as session:
        # Get all rules
        stmt = select(AlertRule)
        result = await session.execute(stmt)
        rules = result.scalars().all()
        
        # Get active hosts
        stmt_hosts = select(Host).where(Host.status == 'online')
        res_hosts = await session.execute(stmt_hosts)
        hosts = res_hosts.scalars().all()
        
        for rule in rules:
            for host in hosts:
                # If rule is host specific and doesn't match, skip
                if rule.host_id and rule.host_id != host.id:
                    continue
                
                # Check metrics in the last duration_minutes
                time_threshold = datetime.now(timezone.utc) - timedelta(minutes=rule.duration_minutes)
                
                # Fetch recent metrics for this host
                stmt_metrics = (
                    select(Metric)
                    .where(Metric.host_id == host.id)
                    .where(Metric.timestamp >= time_threshold)
                )
                res_metrics = await session.execute(stmt_metrics)
                metrics = res_metrics.scalars().all()
                
                if not metrics:
                    continue
                
                # Evaluate condition
                breached = False
                trigger_value = 0.0
                
                # In a real engine, we'd ensure 'all' or 'avg' metrics over duration meet condition. 
                # For simplicity, if the average over the period breaches threshold, trigger alert.
                values = [getattr(m, rule.metric_name, None) for m in metrics if getattr(m, rule.metric_name, None) is not None]
                if not values:
                    continue
                    
                avg_value = sum(values) / len(values)
                
                if rule.operator == ">" and avg_value > rule.threshold:
                    breached = True
                    trigger_value = avg_value
                elif rule.operator == "<" and avg_value < rule.threshold:
                    breached = True
                    trigger_value = avg_value
                elif rule.operator == "==" and avg_value == rule.threshold:
                    breached = True
                    trigger_value = avg_value
                    
                if breached:
                    # Check if alert already exists and is not resolved
                    stmt_exist = select(Alert).where(Alert.host_id == host.id).where(Alert.metric == rule.metric_name).where(Alert.resolved == False)
                    res_exist = await session.execute(stmt_exist)
                    existing_alert = res_exist.scalar_one_or_none()
                    
                    if not existing_alert:
                        msg = f"{rule.metric_name} exceeded threshold ({avg_value:.2f} {rule.operator} {rule.threshold})"
                        new_alert = Alert(
                            host_id=host.id,
                            metric=rule.metric_name,
                            value=avg_value,
                            severity=rule.severity,
                            message=msg
                        )
                        session.add(new_alert)
                        await session.flush()  # Flush to get alert ID before sending notifications
                        await send_alert_notification(new_alert, session)
        
        await session.commit()
