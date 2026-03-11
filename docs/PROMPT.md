# ROLE

Actúa como un **Arquitecto Senior de Sistemas Linux, DevOps Engineer y Software Architect especializado en observabilidad, seguridad y sistemas distribuidos**.

Tu tarea es diseñar y generar la arquitectura completa de un sistema llamado:

**LAMS — Linux Autonomous Monitoring System**

El objetivo es construir un **administrador automático y plataforma de monitorización de servidores Linux**, con capacidad para monitorizar **varias máquinas mediante agentes remotos**.

El sistema debe estar optimizado para **infraestructuras pequeñas y medianas (hasta 50 servidores)**.

---

# OBJETIVO PRINCIPAL

Desarrollar una plataforma capaz de:

* monitorizar recursos del sistema Linux
* almacenar métricas históricas
* detectar anomalías
* enviar alertas
* monitorizar contenedores Docker
* permitir gestión básica de contenedores
* mostrar métricas en un dashboard web
* funcionar con arquitectura cliente-agente segura

---

# ARQUITECTURA GENERAL

El sistema se compone de **3 subsistemas principales**:

1. Central Server
2. Monitor Agent
3. Web Dashboard

---

# 1. CENTRAL SERVER

El servidor central es el núcleo del sistema.

Responsabilidades:

* recibir métricas de agentes
* almacenar métricas
* procesar reglas de alertas
* enviar notificaciones
* autenticar usuarios
* gestionar hosts monitorizados
* exponer API REST
* servir dashboard web

Debe poder ejecutarse en:

* Ubuntu Server
* Debian
* Rocky Linux

---

# 2. MONITOR AGENT

Cada servidor monitorizado ejecuta un **agente ligero**.

Responsabilidades:

* recolectar métricas del sistema
* recolectar métricas Docker
* enviar métricas al servidor central
* mantener heartbeat con el servidor
* reportar estado del host

El agente debe consumir **menos de 2% de CPU y menos de 50 MB RAM**.

Lenguajes recomendados:

Go
Rust
Python (solo si está optimizado)

---

# CICLO DE VIDA DEL AGENTE

1. Instalación mediante script bash.
2. Registro automático en el servidor central.
3. Autenticación mediante token.
4. Envío periódico de métricas.
5. Recepción de configuraciones remotas.

---

# COMUNICACIÓN AGENTE-SERVIDOR

Protocolo:

HTTPS REST API

Frecuencia de envío de métricas:

10–30 segundos configurable.

Formato de datos:

JSON.

Ejemplo de payload:

{
host_id: "server01",
timestamp: "2026-01-01T10:00:00Z",
cpu_usage: 32.5,
memory_used: 5.2,
memory_total: 16,
disk_used: 120,
disk_total: 500,
temperature_cpu: 62,
network_rx: 2048,
network_tx: 1024
}

---

# SISTEMA DE REGISTRO DE HOSTS

El servidor debe permitir gestionar múltiples máquinas.

Cada host debe tener:

* id
* hostname
* ip
* sistema operativo
* versión kernel
* cpu cores
* memoria total
* etiquetas

---

# MONITORIZACIÓN DEL SISTEMA

Cada agente debe monitorizar:

CPU

* uso total
* uso por core
* load average

Memoria

* total
* usada
* libre
* swap

Disco

* espacio total
* espacio libre
* uso %

Temperatura

* sensores CPU
* sensores GPU si existen

Red

* tráfico RX
* tráfico TX
* paquetes
* conexiones activas

Procesos

* top procesos CPU
* top procesos RAM

Sistema

* uptime
* usuarios conectados

---

# SISTEMA DE ALERTAS

El sistema debe permitir definir **reglas configurables**.

Ejemplos:

CPU > 90% durante 2 minutos
RAM > 85%
Disco libre < 10%
Temperatura CPU > 80°C

Cada alerta debe tener:

* severidad (warning, critical)
* host
* métrica
* valor
* timestamp

---

# SISTEMA DE NOTIFICACIONES

Soporte para:

Email (SMTP)
SMS (Twilio API)
Webhook (Slack / Discord)

Las notificaciones deben incluir:

host
alerta
valor detectado
hora
nivel de severidad

---

# MONITORIZACIÓN DOCKER

El agente debe detectar automáticamente si Docker está instalado.

Si está disponible:

recoger:

* lista de contenedores
* estado
* CPU
* RAM
* red
* uptime
* logs recientes

Inspirarse en funcionalidades de:

Portainer
Traefik

---

# GESTIÓN DOCKER

Desde el dashboard el administrador debe poder:

* iniciar contenedor
* parar contenedor
* reiniciar contenedor
* eliminar contenedor
* ver logs
* desplegar docker-compose

---

# BASE DE DATOS

Usar PostgreSQL.

Tablas principales:

users
hosts
metrics
alerts
docker_containers
events

Las métricas deben almacenarse como **series temporales**.

---

# SEGURIDAD

Implementar:

* TLS obligatorio
* autenticación JWT
* hash de contraseñas Argon2
* roles RBAC
* logs de auditoría

---

# SISTEMA DE USUARIOS

Roles:

Administrador
Usuario

Administrador:

gestionar hosts
gestionar alertas
gestionar Docker
gestionar usuarios

Usuario:

solo lectura de métricas y estado.

---

# WEB DASHBOARD

Dashboard accesible vía navegador.

Secciones:

Overview
Hosts
Metrics
Alerts
Docker
Users
Settings

El panel principal debe mostrar:

estado de todos los servidores
alertas activas
uso global de recursos

---

# TECNOLOGÍAS RECOMENDADAS

Backend

Python FastAPI
o Go

Frontend

React
NextJS

Gráficos

ECharts
Chart.js

---

# ESTRUCTURA DEL REPOSITORIO

project-root/

server/

api
auth
alerts
metrics
hosts
docker
database

agent/

collector
system_monitor
docker_monitor
network_monitor

frontend/

dashboard
hosts
alerts
docker

docs/

architecture
installation
api
security

tests/

unit
integration

---

# DESPLIEGUE

El servidor central debe poder instalarse con:

Docker Compose.

Servicios:

server
frontend
postgres

El agente debe instalarse con:

install-agent.sh

---

# DOCUMENTACIÓN

Generar documentación completa que incluya:

arquitectura
instalación
configuración
uso
API
seguridad

---

# RESULTADO ESPERADO

El resultado debe incluir:

arquitectura completa
diagramas del sistema
modelo de base de datos
estructura de repositorio
código inicial del servidor
código inicial del agente
código inicial del dashboard
documentación técnica completa
