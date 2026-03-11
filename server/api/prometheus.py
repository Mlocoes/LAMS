"""
Prometheus metrics endpoint.

Exposes LAMS metrics in Prometheus text format for scraping.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_client import CONTENT_TYPE_LATEST
import logging

from database.database import get_db
from prometheus.exporter import (
    update_prometheus_metrics,
    generate_prometheus_metrics
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["prometheus"])


@router.get("", response_class=Response)
async def prometheus_metrics(db: AsyncSession = Depends(get_db)):
    """
    Endpoint compatible con Prometheus para scraping de métricas.
    
    Este endpoint:
    - NO requiere autenticación (Prometheus scraper no soporta JWT)
    - Actualiza métricas desde la BD en cada request
    - Retorna formato texto plano compatible con Prometheus
    
    Ejemplo de configuración en Prometheus:
    ```yaml
    scrape_configs:
      - job_name: 'lams'
        static_configs:
          - targets: ['lams-server:8080']
        metrics_path: '/api/v1/metrics'
        scrape_interval: 30s
    ```
    
    Returns:
        Response: Métricas en formato texto Prometheus
    """
    try:
        logger.info("Prometheus scrape request received")
        
        # Actualizar métricas en tiempo real desde BD
        await update_prometheus_metrics(db)
        
        # Generar salida en formato Prometheus
        metrics_output = generate_prometheus_metrics()
        
        logger.info(
            f"Prometheus metrics generated successfully "
            f"({len(metrics_output)} bytes)"
        )
        
        return Response(
            content=metrics_output,
            media_type=CONTENT_TYPE_LATEST
        )
        
    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {e}", exc_info=True)
        # Retornar respuesta vacía en caso de error
        # Prometheus manejará esto como un scrape fallido
        return Response(
            content=b"",
            media_type=CONTENT_TYPE_LATEST,
            status_code=500
        )
