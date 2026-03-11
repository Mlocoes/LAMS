# Arquitectura de LAMS (Linux Autonomous Monitoring System)

LAMS es una plataforma robusta y minimalista para el monitoreo de múltiples servidores Linux simultáneos, centralizando los datos, evaluación de salud y alarmas desde una ubicación maestra. Se compone de 3 áreas primordiales:

## 1. Monitor Agent (Cliente Local en Go)
Instalado directamente sobre los servidores (hasta 50 nodos).
- **Responsabilidad:** Extracción del uso de `CPU`, `RAM`, `Rendimiento de Disco` y `Tráfico de red`. Extracción opcional del uso de contenedores alojados localmente accediendo directamente al `/var/run/docker.sock` del host. 
- **Telemetría:** Todo dato es envuelto en un `Payload JSON` y distribuido mediante REST/HTTPS hacia el Servidor Central usando PUSH Periódico (cada 15 segundos).
- **Rendimiento:** Programado 100% nativamente en **Go** empleando la librería `gopsutil`. Promete operar en segundo plano utilizando consistentemente un rango menor al **2% de CPU** y **50MB de RAM**.

## 2. Central Server (API y Core DevOps)
Instalado únicamente en la Infraestructura Central o Datacenter de monitoreo.
- **Back-end API:** Expuesta utilizando **Python (FastAPI)**. Sirve como embudo (Ingress) para recibir la métrica en masa generada por los Agentes, así como enrutar instrucciones de administración remota de Docker u operaciones CRUD de Hosts.
- **Motor de Alertas:** Funciona mediante `APScheduler` como Side-Car al evento de vida del Servidor. Procesa cada minuto una matriz de evaluación comparando las métricas en crudo con Umbrales Dinámicos (`AlertRules`). En caso de rebase o falla técnica, despacha *Events* al servicio interno de Notificación.
- **Almacenamiento (PostgreSQL 15):** Diseñada para ingesta ultra-rápida temporal y referencial. 

## 3. Web Dashboard (Interfaz de Mando)
Montado usualmente sobre el mismo clúster del Central Server.
- **Front-end UI:** Renderizado mediante **Next.js** en App Router. Proveé vistas dinámicas como un `Overview`, lista de `Alertas Ocurridas (Resolve/Ack)`, Gestión central de `Docker`, etc.
- **Styling UI:** Para asegurar la personalización máxima de un estilo sofisticado "Modo Oscuro Glassmorphic" Premium (bordes neon, animaciones suaves, layouts fluidos espaciales), el sistema ha sido implementado utilizando estrictamente **Vanilla CSS** con el módulo de soporte base Global desactivando *Tailwind* por exigencias de la propia arquitectura de UI de usuario.
- **Graficado:** Expansible a usar *ECharts* (Apache) permitiendo la iteración histórica de recursos consumidos a lo largo del tiempo de múltiples hosts encimados directamente por cliente-navegador sin asfixiar la red.
