'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { 
  getHost, 
  getMetrics, 
  getAlerts,
  getContainers,
  dockerAction,
  Host, 
  Metric,
  Alert,
  DockerContainer
} from '@/lib/api';
import { MetricChart } from '@/components/MetricChart';
import { ContainerLogs } from '@/components/docker/ContainerLogs';
import { ContainerInspect } from '@/components/docker/ContainerInspect';
import { DeleteContainer } from '@/components/docker/DeleteContainer';
import { ContainerConsole } from '@/components/docker/ContainerConsole';

export default function HostDetailPage() {
  const { user, token } = useAuth();
  const router = useRouter();
  const params = useParams();
  const hostId = params?.id as string;

  const [host, setHost] = useState<Host | null>(null);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [containers, setContainers] = useState<DockerContainer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [timeRange, setTimeRange] = useState<'1h' | '6h' | '24h' | '7d'>('6h');
  const [selectedContainer, setSelectedContainer] = useState<DockerContainer | null>(null);
  const [showLogs, setShowLogs] = useState(false);
  const [showInspect, setShowInspect] = useState(false);
  const [showDelete, setShowDelete] = useState(false);
  const [showConsole, setShowConsole] = useState(false);

  // Fetch data
  const fetchData = useCallback(async () => {
    if (!token || !hostId) return;
    
    try {
      setLoading(true);
      
      // Calcular rango temporal según selección
      const now = new Date();
      const limits: Record<typeof timeRange, number> = {
        '1h': 60,
        '6h': 360,
        '24h': 1440,
        '7d': 672 // 1 por hora durante 7 días
      };
      
      const [hostData, metricsData, alertsData, containersData] = await Promise.all([
        getHost(hostId),
        getMetrics(hostId, limits[timeRange]),
        getAlerts(false),
        getContainers(hostId).catch(() => [] as DockerContainer[]), // Docker puede no estar disponible
      ]);

      setHost(hostData);
      setMetrics(metricsData.reverse()); // Orden cronológico
      setAlerts(alertsData.filter(a => a.host_id === hostId)); // Filtrar por este host
      setContainers(containersData);
      setError('');
    } catch (err) {
      console.error('Error fetching host data:', err);
      setError(err instanceof Error ? err.message : 'Error al cargar datos del host');
    } finally {
      setLoading(false);
    }
  }, [token, hostId, timeRange]);

  useEffect(() => {
    fetchData();
    
    // Auto-refresh cada 15 segundos
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Docker actions
  const handleDockerAction = async (containerId: string, action: 'start' | 'stop' | 'restart') => {
    if (!hostId) return;
    
    try {
      await dockerAction(hostId, containerId, action);
      alert(`Comando ${action} enviado al contenedor ${containerId}`);
      // Actualizar después de 3 segundos para dar tiempo a la ejecución
      setTimeout(fetchData, 3000);
    } catch (err) {
      alert(`Error al ejecutar ${action}: ${err instanceof Error ? err.message : 'Error desconocido'}`);
    }
  };

  // Redirect if not logged in
  if (!user || !token) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p>Debes iniciar sesión para ver esta página</p>
      </div>
    );
  }

  if (loading && !host) {
    return (
      <div className="app-container">
        <div style={{ padding: '2rem', textAlign: 'center' }}>
          <div className="loading-spinner" />
          <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>Cargando detalles del host...</p>
        </div>
      </div>
    );
  }

  if (error && !host) {
    return (
      <div className="app-container">
        <div style={{ padding: '2rem', textAlign: 'center' }}>
          <p style={{ color: '#ef4444', marginBottom: '1rem' }}>❌ {error}</p>
          <button onClick={() => router.push('/')} className="btn btn-primary">
            Volver al Dashboard
          </button>
        </div>
      </div>
    );
  }

  if (!host) return null;

  // Última métrica para valores actuales
  const latestMetric = metrics.length > 0 ? metrics[metrics.length - 1] : null;
  const isOnline = host.status === 'online';

  return (
    <div className="app-container">
      {/* Header with breadcrumb navigation */}
      <div style={{ 
        marginBottom: '2rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div>
          <button 
            onClick={() => router.push('/')} 
            style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.1)',
              padding: '0.5rem 1rem',
              borderRadius: '8px',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              fontSize: '0.9rem',
              marginBottom: '1rem',
              transition: 'all 0.3s ease'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.1)';
              e.currentTarget.style.borderColor = 'var(--accent)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
            }}
          >
            ← Volver al Dashboard
          </button>
          <h1 style={{ 
            fontSize: '2rem', 
            marginBottom: '0.5rem',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>
            {host.hostname}
          </h1>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ 
              fontSize: '0.85rem',
              padding: '0.25rem 0.75rem',
              borderRadius: '6px',
              background: isOnline ? 'rgba(16, 185, 129, 0.2)' : 'rgba(107, 114, 128, 0.2)',
              color: isOnline ? '#10b981' : '#6b7280',
              border: `1px solid ${isOnline ? '#10b981' : '#6b7280'}`,
              fontWeight: 600
            }}>
              {isOnline ? '● Online' : '○ Offline'}
            </span>
            <span style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              IP: {host.ip}
            </span>
            {host.tags && host.tags.length > 0 && (
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {host.tags.map(tag => (
                  <span key={tag} style={{
                    fontSize: '0.75rem',
                    padding: '0.2rem 0.6rem',
                    borderRadius: '4px',
                    background: 'rgba(102, 126, 234, 0.2)',
                    color: '#667eea',
                    border: '1px solid #667eea'
                  }}>
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Time range selector */}
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {(['1h', '6h', '24h', '7d'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '8px',
                border: '1px solid',
                borderColor: timeRange === range ? 'var(--accent)' : 'rgba(255,255,255,0.1)',
                background: timeRange === range ? 'rgba(102, 126, 234, 0.3)' : 'rgba(255,255,255,0.05)',
                color: timeRange === range ? '#fff' : 'var(--text-secondary)',
                cursor: 'pointer',
                fontSize: '0.85rem',
                fontWeight: timeRange === range ? 600 : 400,
                transition: 'all 0.3s ease'
              }}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      {/* Host Information Card */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <h2 style={{ 
          fontSize: '1.2rem', 
          marginBottom: '1.5rem',
          borderBottom: '2px solid rgba(255,255,255,0.1)',
          paddingBottom: '0.75rem'
        }}>
          📊 Información del Sistema
        </h2>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1.5rem'
        }}>
          <InfoItem label="Sistema Operativo" value={host.os} icon="💻" />
          <InfoItem label="Kernel" value={host.kernel_version} icon="⚙️" />
          <InfoItem label="CPU Cores" value={`${host.cpu_cores} cores`} icon="🔲" />
          <InfoItem label="Memoria Total" value={`${(host.total_memory / 1024).toFixed(1)} GB`} icon="🧠" />
          <InfoItem label="Host ID" value={host.id.slice(0, 16) + '...'} icon="🔑" />
          <InfoItem 
            label="Última Conexión" 
            value={new Date(host.last_seen).toLocaleString('es-ES')} 
            icon="🕐" 
          />
        </div>
      </div>

      {/* Current Metrics Overview */}
      {latestMetric && (
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
          gap: '1rem',
          marginBottom: '2rem'
        }}>
          <MetricOverviewCard 
            title="CPU" 
            value={latestMetric.cpu_usage} 
            max={100}
            unit="%" 
            icon="🔲"
            color="auto"
          />
          <MetricOverviewCard 
            title="Memoria" 
            value={latestMetric.memory_used / 1024} 
            max={host.total_memory / 1024}
            unit=" GB" 
            icon="🧠"
            color="auto"
          />
          <MetricOverviewCard 
            title="Disco" 
            value={latestMetric.disk_usage_percent} 
            max={100}
            unit="%" 
            icon="💾"
            color="auto"
          />
          {latestMetric.temp_cpu && (
            <MetricOverviewCard 
              title="Temperatura CPU" 
              value={latestMetric.temp_cpu} 
              max={100}
              unit="°C" 
              icon="🌡️"
              color="auto"
              showPercentage={false}
            />
          )}
        </div>
      )}

      {/* Historical Charts */}
      <div style={{ marginBottom: '2rem' }}>
        <h2 style={{ 
          fontSize: '1.2rem', 
          marginBottom: '1rem',
          color: 'var(--text-primary)'
        }}>
          📈 Métricas Históricas ({metrics.length} puntos)
        </h2>
        
        {metrics.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
            <p style={{ color: 'var(--text-secondary)' }}>No hay datos históricos disponibles</p>
          </div>
        ) : (
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
            gap: '1.5rem'
          }}>
            <div className="card">
              <MetricChart 
                data={metrics}
                metricKey="cpu_usage"
                title="Uso de CPU"
                color="#667eea"
                unit="%"
                height="350px"
              />
            </div>
            <div className="card">
              <MetricChart 
                data={metrics}
                metricKey="memory_used"
                title="Memoria Usada (GB)"
                color="#10b981"
                unit=" GB"
                height="350px"
              />
            </div>
            <div className="card">
              <MetricChart 
                data={metrics}
                metricKey="disk_usage_percent"
                title="Uso de Disco"
                color="#f59e0b"
                unit="%"
                height="350px"
              />
            </div>
            {metrics.some(m => m.temp_cpu) && (
              <div className="card">
                <MetricChart 
                  data={metrics}
                  metricKey="temp_cpu"
                  title="Temperatura CPU"
                  color="#ef4444"
                  unit="°C"
                  height="350px"
                />
              </div>
            )}
            <div className="card">
              <MetricChart 
                data={metrics}
                metricKey="net_rx"
                title="Red Recibida (MB/s)"
                color="#06b6d4"
                unit=" MB/s"
                height="350px"
              />
            </div>
            <div className="card">
              <MetricChart 
                data={metrics}
                metricKey="net_tx"
                title="Red Enviada (MB/s)"
                color="#8b5cf6"
                unit=" MB/s"
                height="350px"
              />
            </div>
          </div>
        )}
      </div>

      {/* Docker Containers */}
      {containers.length > 0 && (
        <div style={{ marginBottom: '2rem' }}>
          <h2 style={{ 
            fontSize: '1.2rem', 
            marginBottom: '1rem',
            color: 'var(--text-primary)'
          }}>
            🐳 Contenedores Docker ({containers.length})
          </h2>
          <div className="card">
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid rgba(255,255,255,0.1)' }}>
                    <th style={tableHeaderStyle}>Nombre</th>
                    <th style={tableHeaderStyle}>Imagen</th>
                    <th style={tableHeaderStyle}>Estado</th>
                    <th style={tableHeaderStyle}>CPU</th>
                    <th style={tableHeaderStyle}>Memoria</th>
                    <th style={tableHeaderStyle}>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {containers.map(container => (
                    <tr key={container.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={tableCellStyle}>{container.name}</td>
                      <td style={{ ...tableCellStyle, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        {container.image}
                      </td>
                      <td style={tableCellStyle}>
                        <span style={{
                          padding: '0.25rem 0.75rem',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          background: container.state === 'running' 
                            ? 'rgba(16, 185, 129, 0.2)' 
                            : 'rgba(239, 68, 68, 0.2)',
                          color: container.state === 'running' ? '#10b981' : '#ef4444',
                          border: `1px solid ${container.state === 'running' ? '#10b981' : '#ef4444'}`
                        }}>
                          {container.state}
                        </span>
                      </td>
                      <td style={tableCellStyle}>{container.cpu_percent.toFixed(1)}%</td>
                      <td style={tableCellStyle}>{(container.memory_usage / 1024 / 1024).toFixed(0)} MB</td>
                      <td style={tableCellStyle}>
                        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                          {container.state !== 'running' && (
                            <ActionButton 
                              onClick={() => handleDockerAction(container.id, 'start')}
                              color="#10b981"
                              label="▶ Start"
                            />
                          )}
                          {container.state === 'running' && (
                            <>
                              <ActionButton 
                                onClick={() => handleDockerAction(container.id, 'stop')}
                                color="#ef4444"
                                label="■ Stop"
                              />
                              <ActionButton 
                                onClick={() => handleDockerAction(container.id, 'restart')}
                                color="#f59e0b"
                                label="🔄 Restart"
                              />
                            </>
                          )}
                          <ActionButton 
                            onClick={() => {
                              setSelectedContainer(container);
                              setShowLogs(true);
                            }}
                            color="#667eea"
                            label="📋 Logs"
                          />
                          <ActionButton 
                            onClick={() => {
                              setSelectedContainer(container);
                              setShowInspect(true);
                            }}
                            color="#06b6d4"
                            label="🔍 Inspect"
                          />
                          {container.state === 'running' && (
                            <ActionButton 
                              onClick={() => {
                                setSelectedContainer(container);
                                setShowConsole(true);
                              }}
                              color="#10b981"
                              label="💻 Console"
                            />
                          )}
                          <ActionButton 
                            onClick={() => {
                              setSelectedContainer(container);
                              setShowDelete(true);
                            }}
                            color="#ef4444"
                            label="🗑️ Delete"
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Alerts for this host */}
      <div>
        <h2 style={{ 
          fontSize: '1.2rem', 
          marginBottom: '1rem',
          color: 'var(--text-primary)'
        }}>
          🚨 Alertas Activas ({alerts.length})
        </h2>
        {alerts.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
            <p style={{ color: 'var(--text-secondary)' }}>✅ No hay alertas activas para este host</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {alerts.map(alert => (
              <div key={alert.id} className="card" style={{
                borderLeft: `4px solid ${alert.severity === 'critical' ? '#ef4444' : '#f59e0b'}`,
                background: alert.severity === 'critical' 
                  ? 'rgba(239, 68, 68, 0.1)' 
                  : 'rgba(245, 158, 11, 0.1)'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginBottom: '0.5rem' }}>
                      <span style={{
                        padding: '0.25rem 0.75rem',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        background: alert.severity === 'critical' ? '#ef4444' : '#f59e0b',
                        color: 'white'
                      }}>
                        {alert.severity.toUpperCase()}
                      </span>
                      <span style={{ 
                        fontSize: '0.9rem', 
                        fontWeight: 600,
                        color: 'var(--text-primary)'
                      }}>
                        {alert.metric}
                      </span>
                    </div>
                    <p style={{ 
                      margin: '0.5rem 0',
                      color: 'var(--text-primary)',
                      fontSize: '0.95rem'
                    }}>
                      {alert.message}
                    </p>
                    <p style={{ 
                      fontSize: '0.85rem', 
                      color: 'var(--text-secondary)',
                      margin: '0.5rem 0 0 0'
                    }}>
                      Valor: <strong>{alert.value}</strong> • {new Date(alert.event_time).toLocaleString('es-ES')}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Docker Container Modals */}
      {showLogs && selectedContainer && (
        <ContainerLogs
          hostId={hostId}
          containerId={selectedContainer.id}
          containerName={selectedContainer.name}
          onClose={() => {
            setShowLogs(false);
            setSelectedContainer(null);
          }}
        />
      )}

      {showInspect && selectedContainer && (
        <ContainerInspect
          hostId={hostId}
          containerId={selectedContainer.id}
          containerName={selectedContainer.name}
          onClose={() => {
            setShowInspect(false);
            setSelectedContainer(null);
          }}
        />
      )}

      {showDelete && selectedContainer && (
        <DeleteContainer
          hostId={hostId}
          containerId={selectedContainer.id}
          containerName={selectedContainer.name}
          containerStatus={selectedContainer.state}
          onClose={() => {
            setShowDelete(false);
            setSelectedContainer(null);
          }}
          onSuccess={() => {
            fetchData(); // Refresh container list
          }}
        />
      )}

      {showConsole && selectedContainer && (
        <ContainerConsole
          hostId={hostId}
          containerId={selectedContainer.id}
          containerName={selectedContainer.name}
          onClose={() => {
            setShowConsole(false);
            setSelectedContainer(null);
          }}
        />
      )}
    </div>
  );
}

/* ─── Helper Components ─────────────────────────────────────────── */

function InfoItem({ label, value, icon }: { label: string; value: string; icon: string }) {
  return (
    <div>
      <div style={{ 
        fontSize: '0.8rem', 
        color: 'var(--text-secondary)',
        marginBottom: '0.5rem',
        fontWeight: 500
      }}>
        {icon} {label}
      </div>
      <div style={{ 
        fontSize: '0.95rem', 
        color: 'var(--text-primary)',
        fontWeight: 600,
        wordBreak: 'break-word'
      }}>
        {value}
      </div>
    </div>
  );
}

function MetricOverviewCard({ 
  title, 
  value, 
  max,
  unit, 
  icon,
  color,
  showPercentage = true
}: { 
  title: string; 
  value: number; 
  max: number;
  unit: string; 
  icon: string;
  color: string;
  showPercentage?: boolean;
}) {
  const percentage = Math.min((value / max) * 100, 100);
  
  const getColor = () => {
    if (color === 'auto') {
      if (percentage < 60) return '#10b981';
      if (percentage < 80) return '#f59e0b';
      return '#ef4444';
    }
    return color;
  };

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
            {icon} {title}
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            {value.toFixed(1)}{unit}
          </div>
        </div>
        {showPercentage && (
          <div style={{ 
            fontSize: '1.5rem', 
            fontWeight: 700, 
            color: getColor()
          }}>
            {percentage.toFixed(0)}%
          </div>
        )}
      </div>
      <div style={{ 
        width: '100%', 
        height: '8px', 
        background: 'rgba(255,255,255,0.08)', 
        borderRadius: '999px',
        overflow: 'hidden'
      }}>
        <div style={{
          width: `${percentage}%`,
          height: '100%',
          background: getColor(),
          transition: 'width 0.6s ease',
          borderRadius: '999px',
          boxShadow: `0 0 10px ${getColor()}80`
        }} />
      </div>
    </div>
  );
}

function ActionButton({ 
  onClick, 
  color, 
  label 
}: { 
  onClick: () => void; 
  color: string; 
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '0.4rem 0.8rem',
        borderRadius: '4px',
        border: `1px solid ${color}`,
        background: `${color}20`,
        color: color,
        cursor: 'pointer',
        fontSize: '0.75rem',
        fontWeight: 600,
        transition: 'all 0.2s ease'
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = color;
        e.currentTarget.style.color = 'white';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = `${color}20`;
        e.currentTarget.style.color = color;
      }}
    >
      {label}
    </button>
  );
}

/* ─── Table Styles ─────────────────────────────────────────────── */

const tableHeaderStyle: React.CSSProperties = {
  padding: '0.75rem',
  textAlign: 'left',
  fontSize: '0.85rem',
  fontWeight: 600,
  color: 'var(--text-secondary)',
  textTransform: 'uppercase',
  letterSpacing: '0.5px'
};

const tableCellStyle: React.CSSProperties = {
  padding: '1rem 0.75rem',
  fontSize: '0.9rem',
  color: 'var(--text-primary)'
};
