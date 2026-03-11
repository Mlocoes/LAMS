'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { 
  getHosts, 
  getAlerts, 
  getMetrics, 
  getNotificationConfigs,
  createNotificationConfig,
  updateNotificationConfig,
  deleteNotificationConfig,
  testNotificationConfig,
  getUsers,
  createUser,
  updateUser,
  deleteUser,
  updateHostTags,
  Host, 
  Alert, 
  Metric,
  NotificationConfig,
  NotificationConfigCreate,
  User,
  UserCreate,
  UserUpdate
} from '@/lib/api';
import { MetricChart } from '@/components/MetricChart';
import { ThemeToggle } from '@/components/ThemeToggle';
import { exportMetricsToCSV, exportHostsToCSV, exportAlertsToCSV } from '@/lib/export';

/* ─── Login screen ─────────────────────────────────────────────── */
function LoginScreen() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      console.log('🔐 Iniciando login...', { email });
      await login(email, password);
      console.log('✅ Login exitoso');
    } catch (err) {
      console.error('❌ Error en login:', err);
      const errorMessage = err instanceof Error ? err.message : 'Credenciales incorrectas';
      setError(`${errorMessage}. Verifica que el email y contraseña sean correctos.`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="login-logo">
          <span className="text-gradient">LAMS</span>
        </div>
        <h1>Linux Autonomous Monitoring</h1>
        <p className="login-subtitle">Inicia sesión para acceder al dashboard</p>
        
        {/* Panel de diagnóstico con credenciales por defecto */}
        <div style={{ 
          background: '#16213e', 
          padding: '15px', 
          borderRadius: '8px', 
          marginBottom: '20px',
          border: '1px solid #0f3460'
        }}>
          <div style={{ marginBottom: '10px', color: '#4ade80', fontWeight: 'bold' }}>
            🔑 Credenciales por defecto:
          </div>
          <div style={{ fontSize: '14px', fontFamily: 'monospace', lineHeight: '1.8' }}>
            <div><strong>Email:</strong> admin@lams.io</div>
            <div><strong>Password:</strong> lams2024</div>
          </div>
          <div style={{ 
            marginTop: '10px', 
            padding: '8px', 
            background: '#0f3460',
            borderRadius: '4px',
            fontSize: '12px'
          }}>
            <div>🔧 API: {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}</div>
          </div>
          <button 
            type="button"
            onClick={() => {
              setEmail('admin@lams.io');
              setPassword('lams2024');
            }}
            style={{
              marginTop: '10px',
              width: '100%',
              padding: '8px',
              background: '#4ade80',
              color: '#000',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '13px'
            }}
          >
            ✨ Autocompletar credenciales
          </button>
        </div>
        
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="admin@lams.io"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>
          {error && <p className="login-error">{error}</p>}
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Autenticando…' : 'Iniciar sesión'}
          </button>
          
          <div style={{ 
            marginTop: '15px', 
            textAlign: 'center',
            fontSize: '13px'
          }}>
            <a 
              href="/diagnostic" 
              style={{ 
                color: '#4ade80', 
                textDecoration: 'none',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px'
              }}
            >
              🔧 Diagnóstico de conectividad
            </a>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ─── Sidebar nav ───────────────────────────────────────────────── */
type Page = 'dashboard' | 'hosts' | 'alerts' | 'docker' | 'rules' | 'notifications' | 'users' | 'settings';

function Sidebar({ 
  current, 
  setCurrent, 
  onLogout,
  isOpen,
  onClose,
  userRole
}: { 
  current: Page; 
  setCurrent: (p: Page) => void; 
  onLogout: () => void;
  isOpen?: boolean;
  onClose?: () => void;
  userRole?: boolean | string;
}) {
  const allLinks: { id: Page; label: string; icon: string; adminOnly?: boolean }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: '◈' },
    { id: 'hosts',     label: 'Hosts',     icon: '⬡' },
    { id: 'alerts',    label: 'Alertas',   icon: '⚡' },
    { id: 'docker',    label: 'Docker',    icon: '⊡' },
    { id: 'rules',     label: 'Reglas',    icon: '⚙' },
    { id: 'notifications', label: 'Notificaciones', icon: '🔔' },
    { id: 'users',     label: 'Usuarios',  icon: '👤' },
    { id: 'settings',  label: 'Configuración', icon: '⚙️', adminOnly: true },
  ];
  
  // Filtrar enlaces basados en el rol (mostrar settings solo a admins)
  const isAdmin = userRole === true || userRole === 'true';
  const links = allLinks.filter(link => !link.adminOnly || isAdmin);
  
  const handleNavClick = (pageId: Page) => {
    setCurrent(pageId);
    if (onClose) onClose(); // Cerrar sidebar en móvil después de navegar
  };
  
  return (
    <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
      <div className="sidebar-logo">
        <span className="text-gradient">LAMS</span>
      </div>
      <div style={{ padding: '0 1rem 1rem', display: 'flex', justifyContent: 'center' }}>
        <ThemeToggle />
      </div>
      <nav className="sidebar-nav">
        {links.map(l => (
          <button
            key={l.id}
            className={`nav-item ${current === l.id ? 'active' : ''}`}
            onClick={() => handleNavClick(l.id)}
          >
            <span className="nav-icon">{l.icon}</span>
            {l.label}
          </button>
        ))}
      </nav>
      <button className="nav-item logout-btn" onClick={onLogout}>
        <span className="nav-icon">⏻</span>
        Salir
      </button>
    </aside>
  );
}

/* ─── Stat card for overview ─────────────────────────────────────── */
function StatCard({ title, value, sub, accent }: { title: string; value: string; sub?: string; accent: string }) {
  return (
    <div className={`card stat-card highlight-${accent}`}>
      <h3>
        {title}
      </h3>
      <p className="card-value">{value}</p>
      {sub && <p className="stat-sub">{sub}</p>}
    </div>
  );
}

/* ─── Status badge (ULTRA COMPACTO) ──────────────────────────────────────────────── */
function StatusBadge({ status }: { status: string }) {
  const isOnline = status === 'online';
  return (
    <span style={{ 
      fontSize: '0.6rem', 
      padding: '0.15rem 0.4rem', 
      borderRadius: '3px',
      background: isOnline ? '#10b981' : '#6b7280',
      color: 'white',
      fontWeight: 600,
      display: 'inline-block'
    }}>
      {isOnline ? 'ON' : 'OFF'}
    </span>
  );
}

/* ─── Progress bar ──────────────────────────────────────────────── */
function ProgressBar({ value, max, color, showLabel = true }: { value: number; max: number; color: string; showLabel?: boolean }) {
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
    <div style={{ width: '100%' }}>
      {showLabel && (
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem', fontSize: '0.9rem', fontWeight: 600 }}>
          <span style={{ color: 'var(--text-secondary)' }}>
            {value.toFixed(1)} <span style={{ fontSize: '0.85rem' }}>/ {max.toFixed(0)}</span>
          </span>
          <span style={{ color: getColor(), fontWeight: 700 }}>{percentage.toFixed(1)}%</span>
        </div>
      )}
      <div style={{ 
        width: '100%', 
        height: '10px', 
        background: 'rgba(255,255,255,0.08)', 
        borderRadius: '999px',
        overflow: 'hidden',
        boxShadow: 'inset 0 1px 3px rgba(0,0,0,0.3)'
      }}>
        <div style={{
          width: `${percentage}%`,
          height: '100%',
          background: `linear-gradient(90deg, ${getColor()}, ${getColor()}dd)`,
          transition: 'width 0.6s cubic-bezier(0.4, 0, 0.2, 1)',
          boxShadow: `0 0 15px ${getColor()}80`,
          borderRadius: '999px'
        }} />
      </div>
    </div>
  );
}

/* ─── Metric card with progress ─────────────────────── */
function MetricCard({ 
  title, 
  value, 
  max, 
  unit, 
  icon, 
  color = 'auto',
  subtitle 
}: { 
  title: string; 
  value: number; 
  max?: number; 
  unit: string; 
  icon: string;
  color?: string;
  subtitle?: string;
}) {
  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
        <div style={{ flex: 1 }}>
          <h3 style={{ 
            fontSize: '0.75rem', 
            fontWeight: 700,
            color: 'var(--text-secondary)', 
            marginBottom: '0.75rem',
            textTransform: 'uppercase',
            letterSpacing: '0.08em'
          }}>
            {title}
          </h3>
          <p style={{ fontSize: '1.2rem', fontWeight: 700, margin: 0, letterSpacing: '-0.01em' }}>
            {value.toFixed(1)}
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 600 }}>{unit}</span>
          </p>
          {subtitle && (
            <p style={{ 
              fontSize: '0.85rem', 
              color: 'var(--text-secondary)', 
              marginTop: '0.5rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem'
            }}>
              {subtitle}
            </p>
          )}
        </div>
        <span className="card-icon" style={{ fontSize: '1.5rem' }}>{icon}</span>
      </div>
      {max && <ProgressBar value={value} max={max} color={color} showLabel={false} />}
    </div>
  );
}

/* ─── Dashboard overview ────────────────────────────────────────── */
function DashboardPage() {
  const [hosts, setHosts] = useState<Host[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [metrics, setMetrics] = useState<Record<string, Metric[]>>({});
  const [loading, setLoading] = useState(true);
  const [selectedHostId, setSelectedHostId] = useState<string>('');
  const [metricsLimit, setMetricsLimit] = useState(60); // Últimos 15 minutos (60 * 15s)

  const loadData = useCallback(async () => {
    try {
      const [h, a] = await Promise.all([getHosts(), getAlerts(false)]);
      setHosts(h);
      setAlerts(a);
      
      // Cargar métricas del host seleccionado o del primero disponible
      const targetHost = selectedHostId || (h.length > 0 ? h[0].id : null);
      if (targetHost) {
        const m = await getMetrics(targetHost, metricsLimit);
        setMetrics(prev => ({ ...prev, [targetHost]: m }));
        if (!selectedHostId && targetHost) setSelectedHostId(targetHost);
      }
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedHostId, metricsLimit]);

  useEffect(() => {
    loadData();
    // Auto-refresh cada 15 segundos
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, [loadData]);

  if (loading) return <div className="loading-msg">Cargando datos…</div>;

  const online = hosts.filter(h => h.status === 'online').length;
  const offline = hosts.length - online;
  const critical = alerts.filter(a => a.severity === 'critical').length;
  const warning = alerts.filter(a => a.severity === 'warning').length;

  const hostMetrics = selectedHostId ? metrics[selectedHostId] || [] : [];
  const currentMetric = hostMetrics.length > 0 ? hostMetrics[0] : null;
  const selectedHost = hosts.find(h => h.id === selectedHostId);

  return (
    <div className="page-content" style={{ height: 'calc(100vh - 2rem)', overflow: 'hidden' }}>
      {/* Header compacto */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.75rem' }}>📊</span>
            Dashboard <span className="text-gradient">Global</span>
          </h1>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0' }}>
            Auto-refresh 15s · {selectedHost?.hostname || 'Selecciona un host'}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          {hosts.length > 0 && (
            <>
              <select
                value={selectedHostId}
                onChange={e => setSelectedHostId(e.target.value)}
                className="lams-select"
                style={{ minWidth: '150px', padding: '0.5rem 0.75rem', fontSize: '0.85rem' }}
              >
                {hosts.map(h => (
                  <option key={h.id} value={h.id}>🖥️ {h.hostname}</option>
                ))}
              </select>
              
              <select
                value={metricsLimit}
                onChange={e => setMetricsLimit(Number(e.target.value))}
                className="lams-select"
                style={{ padding: '0.5rem 0.75rem', fontSize: '0.85rem' }}
                title="Rango temporal"
              >
                <option value={60}>⏱️ 15m</option>
                <option value={240}>⏱️ 1h</option>
                <option value={1440}>⏱️ 6h</option>
                <option value={5760}>⏱️ 24h</option>
              </select>
              
              <button
                onClick={() => exportMetricsToCSV(hostMetrics, selectedHost?.hostname || 'metrics')}
                style={{
                  padding: '0.5rem 0.75rem',
                  background: '#8b5cf6',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  transition: 'all 0.2s ease'
                }}
                onMouseEnter={e => e.currentTarget.style.background = '#7c3aed'}
                onMouseLeave={e => e.currentTarget.style.background = '#8b5cf6'}
                title="Exportar métricas a CSV"
                disabled={hostMetrics.length === 0}
              >
                📊 CSV
              </button>
            </>
          )}
        </div>
      </div>

      {/* Layout optimizado en 2 columnas */}
      <div className="dashboard-layout">
        
        {/* Columna izquierda: Gráficos */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', overflow: 'hidden' }}>
          
          {/* Resumen ultra-compacto inline */}
          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.7rem', padding: '0.35rem 0.5rem', background: 'rgba(255,255,255,0.03)', borderRadius: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ color: 'var(--text-secondary)' }}>🟢 <b>{online}</b> online</span>
            <span style={{ color: 'var(--text-secondary)' }}>⚠️ <b>{critical}</b> críticas</span>
            <span style={{ color: 'var(--text-secondary)' }}>🖥️ <b>{hosts.length}</b> hosts</span>
            <span style={{ color: 'var(--text-secondary)' }}>🔔 <b>{alerts.length}</b> alertas</span>
          </div>

          {/* Métricas en tiempo real - barra compacta */}
          {currentMetric && selectedHost ? (
            <>
              {/* Mini métricas inline */}
              <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.7rem', padding: '0.4rem 0.6rem', background: 'rgba(255,255,255,0.03)', borderRadius: '0.5rem', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: '120px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>⚡ CPU:</span> <b>{currentMetric.cpu_usage.toFixed(1)}%</b>
                  <span style={{ color: 'var(--text-muted)', marginLeft: '0.5rem', fontSize: '0.65rem' }}>Load: {currentMetric.load_average}</span>
                </div>
                <div style={{ flex: 1, minWidth: '120px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>💾 RAM:</span> <b>{currentMetric.memory_used.toFixed(0)} MB</b>
                  <span style={{ color: 'var(--text-muted)', marginLeft: '0.5rem', fontSize: '0.65rem' }}>Libre: {currentMetric.memory_free.toFixed(0)} MB</span>
                </div>
                <div style={{ flex: 1, minWidth: '120px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>💿 Disco:</span> <b>{currentMetric.disk_usage_percent.toFixed(1)}%</b>
                  <span style={{ color: 'var(--text-muted)', marginLeft: '0.5rem', fontSize: '0.65rem' }}>{currentMetric.disk_used.toFixed(0)}/{currentMetric.disk_total.toFixed(0)} GB</span>
                </div>
              </div>

              {/* Gráficos históricos - dominan la pantalla */}
              {hostMetrics.length > 1 && (
                <div className="charts-grid">
                  <div className="card" style={{ padding: '0.5rem' }}>
                    <MetricChart
                      data={hostMetrics.slice().reverse()}
                      metricKey="cpu_usage"
                      title="CPU Usage"
                      color="#8b5cf6"
                      unit="%"
                      height="calc((100vh - 12rem) / 2)"
                    />
                  </div>
                  <div className="card" style={{ padding: '0.5rem' }}>
                    <MetricChart
                      data={hostMetrics.slice().reverse()}
                      metricKey="memory_used"
                      title="RAM"
                      color="#3b82f6"
                      unit=" MB"
                      height="calc((100vh - 12rem) / 2)"
                    />
                  </div>
                  <div className="card" style={{ padding: '0.5rem' }}>
                    <MetricChart
                      data={hostMetrics.slice().reverse()}
                      metricKey="disk_usage_percent"
                      title="Disco"
                      color="#f59e0b"
                      unit="%"
                      height="calc((100vh - 12rem) / 2)"
                    />
                  </div>
                  <div className="card" style={{ padding: '0.5rem' }}>
                    <MetricChart
                      data={hostMetrics.slice().reverse()}
                      metricKey="temp_cpu"
                      title="Temp CPU"
                      color="#ef4444"
                      unit="°C"
                      height="calc((100vh - 12rem) / 2)"
                    />
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="card" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              No hay métricas disponibles aún.
            </div>
          )}
        </div>

        {/* Columna derecha: Hosts y Alertas */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', overflow: 'hidden' }}>

          {/* Hosts compactos */}
          <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            <h3 style={{ fontSize: '0.75rem', margin: '0 0 0.4rem 0', color: 'var(--text-secondary)', fontWeight: 600 }}>
              🖥️ Hosts ({hosts.length})
            </h3>
            <div className="card" style={{ padding: '0.4rem', flex: 1, overflow: 'auto' }}>
              <table style={{ width: '100%', fontSize: '0.65rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                    <th style={{ padding: '0.3rem', textAlign: 'left', fontSize: '0.6rem', color: 'var(--text-muted)' }}>Host</th>
                    <th style={{ padding: '0.3rem', textAlign: 'center', fontSize: '0.6rem', color: 'var(--text-muted)' }}>CPU</th>
                    <th style={{ padding: '0.3rem', textAlign: 'center', fontSize: '0.6rem', color: 'var(--text-muted)' }}>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {hosts.map(h => (
                    <tr 
                      key={h.id} 
                      onClick={() => setSelectedHostId(h.id)}
                      style={{ 
                        cursor: 'pointer', 
                        background: h.id === selectedHostId ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                        borderBottom: '1px solid rgba(255,255,255,0.05)'
                      }}
                    >
                      <td style={{ padding: '0.4rem 0.3rem', fontWeight: 600, fontSize: '0.65rem' }}>{h.hostname}</td>
                      <td style={{ padding: '0.4rem 0.3rem', textAlign: 'center', fontSize: '0.65rem' }}>{h.cpu_cores}</td>
                      <td style={{ padding: '0.4rem 0.3rem', textAlign: 'center' }}><StatusBadge status={h.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Alertas compactas */}
          {alerts.length > 0 && (
            <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
              <h3 style={{ fontSize: '0.75rem', margin: '0 0 0.4rem 0', color: 'var(--text-secondary)', fontWeight: 600 }}>
                🚨 Alertas ({alerts.length})
              </h3>
              <div className="card" style={{ padding: '0.4rem', flex: 1, overflow: 'auto' }}>
                <table style={{ width: '100%', fontSize: '0.65rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                      <th style={{ padding: '0.3rem', textAlign: 'left', fontSize: '0.6rem', color: 'var(--text-muted)' }}>Host</th>
                      <th style={{ padding: '0.3rem', textAlign: 'left', fontSize: '0.6rem', color: 'var(--text-muted)' }}>Métrica</th>
                      <th style={{ padding: '0.3rem', textAlign: 'center', fontSize: '0.6rem', color: 'var(--text-muted)' }}>Sev.</th>
                    </tr>
                  </thead>
                  <tbody>
                    {alerts.slice(0, 15).map(a => (
                      <tr key={a.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '0.4rem 0.3rem', fontWeight: 600, fontSize: '0.65rem' }}>{a.host_id}</td>
                        <td style={{ padding: '0.4rem 0.3rem', fontSize: '0.6rem', color: 'var(--text-secondary)' }}>{a.metric}</td>
                        <td style={{ padding: '0.4rem 0.3rem', textAlign: 'center' }}>
                          <span style={{ 
                            fontSize: '0.55rem', 
                            padding: '0.15rem 0.35rem', 
                            borderRadius: '3px',
                            background: a.severity === 'critical' ? '#ef4444' : '#f59e0b',
                            color: 'white',
                            fontWeight: 700
                          }}>
                            {a.severity === 'critical' ? 'CRIT' : 'WARN'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Hosts page ────────────────────────────────────────────────── */
function HostsPage() {
  const router = useRouter();
  const [hosts, setHosts] = useState<Host[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'online' | 'offline'>('all');
  const [tagFilter, setTagFilter] = useState<string>('');
  const [editingTagsFor, setEditingTagsFor] = useState<string | null>(null);
  const [tagInput, setTagInput] = useState('');

  useEffect(() => { getHosts().then(setHosts).finally(() => setLoading(false)); }, []);

  // Obtener todos los tags únicos
  const allTags = Array.from(new Set(hosts.flatMap(h => h.tags || [])));

  // Guardar tags
  const saveTags = async (hostId: string, tags: string[]) => {
    try {
      const updatedHost = await updateHostTags(hostId, tags);
      setHosts(hosts.map(h => h.id === hostId ? updatedHost : h));
      setEditingTagsFor(null);
      setTagInput('');
    } catch (error) {
      console.error('Error updating tags:', error);
      alert('Error al actualizar tags');
    }
  };

  if (loading) return <div className="loading-msg">Cargando hosts...</div>;

  // Filtrado de hosts
  const filteredHosts = hosts.filter(h => {
    // Filtro de búsqueda
    const matchesSearch = searchQuery === '' || 
      h.hostname.toLowerCase().includes(searchQuery.toLowerCase()) ||
      h.ip.includes(searchQuery) ||
      h.os.toLowerCase().includes(searchQuery.toLowerCase()) ||
      h.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (h.tags || []).some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    
    // Filtro de estado
    const matchesStatus = statusFilter === 'all' || h.status === statusFilter;
    
    // Filtro de tag
    const matchesTag = tagFilter === '' || (h.tags || []).includes(tagFilter);
    
    return matchesSearch && matchesStatus && matchesTag;
  });

  const online = hosts.filter(h => h.status === 'online').length;
  const offline = hosts.length - online;

  return (
    <div className="page-content" style={{ height: 'calc(100vh - 2rem)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      {/* Header compacto moderno */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', padding: '0.75rem 0', flexShrink: 0 }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '2rem' }}>🖥️</span>
            Hosts <span className="text-gradient">Registrados</span>
          </h1>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0', display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span><b>{hosts.length}</b> servidores monitoreados</span>
            <span style={{ 
              padding: '0.15rem 0.5rem', 
              borderRadius: '4px', 
              background: 'rgba(16, 185, 129, 0.15)',
              color: '#10b981',
              fontSize: '0.75rem',
              fontWeight: 600
            }}>● {online} activos</span>
            {offline > 0 && (
              <span style={{ 
                padding: '0.15rem 0.5rem', 
                borderRadius: '4px', 
                background: 'rgba(239, 68, 68, 0.15)',
                color: '#ef4444',
                fontSize: '0.75rem',
                fontWeight: 600
              }}>● {offline} inactivos</span>
            )}
          </p>
        </div>
        {hosts.length > 0 && (
          <button
            onClick={() => exportHostsToCSV(filteredHosts.length > 0 ? filteredHosts : hosts)}
            style={{
              padding: '0.75rem 1.25rem',
              background: '#8b5cf6',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              transition: 'all 0.2s ease'
            }}
            onMouseEnter={e => e.currentTarget.style.background = '#7c3aed'}
            onMouseLeave={e => e.currentTarget.style.background = '#8b5cf6'}
            title={filteredHosts.length > 0 && filteredHosts.length < hosts.length ? 
              `Exportar ${filteredHosts.length} hosts filtrados a CSV` : 
              'Exportar todos los hosts a CSV'}
          >
            📊 Exportar CSV
          </button>
        )}
      </div>

      {/* Barra de búsqueda y filtros */}
      <div style={{ 
        display: 'flex', 
        gap: '1rem', 
        marginBottom: '1.5rem', 
        flexWrap: 'wrap',
        alignItems: 'center',
        background: 'rgba(255,255,255,0.03)',
        padding: '1rem',
        borderRadius: '8px',
        border: '1px solid rgba(255,255,255,0.08)'
      }}>
        <div style={{ flex: 1, minWidth: '300px' }}>
          <input
            type="text"
            placeholder="🔍 Buscar por hostname, IP, OS, ID o tags..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '0.75rem 1rem',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '6px',
              color: 'white',
              fontSize: '0.9rem',
              outline: 'none',
              transition: 'all 0.2s ease'
            }}
            onFocus={e => e.target.style.borderColor = '#4ade80'}
            onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
          />
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            onClick={() => setStatusFilter('all')}
            style={{
              padding: '0.75rem 1.25rem',
              background: statusFilter === 'all' ? '#4ade80' : 'rgba(255,255,255,0.05)',
              color: statusFilter === 'all' ? '#000' : 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: '600',
              transition: 'all 0.2s ease'
            }}
          >
            Todos ({hosts.length})
          </button>
          <button
            onClick={() => setStatusFilter('online')}
            style={{
              padding: '0.75rem 1.25rem',
              background: statusFilter === 'online' ? '#10b981' : 'rgba(16, 185, 129, 0.1)',
              color: statusFilter === 'online' ? '#000' : '#10b981',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: '600',
              transition: 'all 0.2s ease'
            }}
          >
            ● Online ({online})
          </button>
          <button
            onClick={() => setStatusFilter('offline')}
            style={{
              padding: '0.75rem 1.25rem',
              background: statusFilter === 'offline' ? '#ef4444' : 'rgba(239, 68, 68, 0.1)',
              color: statusFilter === 'offline' ? '#000' : '#ef4444',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '0.85rem',
              fontWeight: '600',
              transition: 'all 0.2s ease'
            }}
          >
            ● Offline ({offline})
          </button>
        </div>
        {allTags.length > 0 && (
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>🏷️ Tags:</span>
            <button
              onClick={() => setTagFilter('')}
              style={{
                padding: '0.5rem 0.75rem',
                background: tagFilter === '' ? '#8b5cf6' : 'rgba(139, 92, 246, 0.1)',
                color: tagFilter === '' ? '#000' : '#a78bfa',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.75rem',
                fontWeight: '600'
              }}
            >
              Todos
            </button>
            {allTags.map(tag => (
              <button
                key={tag}
                onClick={() => setTagFilter(tag)}
                style={{
                  padding: '0.5rem 0.75rem',
                  background: tagFilter === tag ? '#8b5cf6' : 'rgba(139, 92, 246, 0.1)',
                  color: tagFilter === tag ? '#000' : '#a78bfa',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.75rem',
                  fontWeight: '600'
                }}
              >
                {tag}
              </button>
            ))}
          </div>
        )}
        {(searchQuery || statusFilter !== 'all' || tagFilter) && (
          <div style={{ 
            fontSize: '0.85rem', 
            color: '#4ade80',
            fontWeight: 600,
            padding: '0.5rem 1rem',
            background: 'rgba(74, 222, 128, 0.1)',
            borderRadius: '6px'
          }}>
            {filteredHosts.length} resultado{filteredHosts.length !== 1 ? 's' : ''} encontrado{filteredHosts.length !== 1 ? 's' : ''}
          </div>
        )}
      </div>

      {hosts.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🖥️</div>
          <h3 className="empty-state-title">No hay hosts registrados</h3>
          <p className="empty-state-text">Instala y ejecuta el agente LAMS en tus servidores para comenzar el monitoreo</p>
        </div>
      ) : filteredHosts.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🔍</div>
          <h3 className="empty-state-title">No se encontraron resultados</h3>
          <p className="empty-state-text">Intenta con otros términos de búsqueda o ajusta los filtros</p>
          <button
            onClick={() => {
              setSearchQuery('');
              setStatusFilter('all');
              setTagFilter('');
            }}
            style={{
              marginTop: '1rem',
              padding: '0.75rem 1.5rem',
              background: '#4ade80',
              color: '#000',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 'bold',
              fontSize: '0.9rem'
            }}
          >
            Limpiar filtros
          </button>
        </div>
      ) : (
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <div className="table-wrap" style={{ flex: 1, overflow: 'auto' }}>
            <table className="lams-table" style={{ fontSize: '0.85rem' }}>
              <thead>
                <tr>
                  <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Estado</th>
                  <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Hostname</th>
                  <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Tags</th>
                <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Identificador</th>
                <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Dirección IP</th>
                <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Sistema Operativo</th>
                <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Kernel</th>
                <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>CPU Cores</th>
                <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Memoria RAM</th>
                <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Último Contacto</th>
                <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredHosts.map(h => (
                <tr key={h.id} style={{ 
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                  transition: 'all 0.2s ease',
                  background: h.status === 'online' ? 'transparent' : 'rgba(239, 68, 68, 0.05)'
                }}>
                  <td style={{ padding: '0.75rem' }}><StatusBadge status={h.status} /></td>
                  <td style={{ padding: '0.75rem', fontWeight: 700, fontSize: '0.95rem' }}>
                    🖥️ {h.hostname}
                  </td>
                  <td style={{ padding: '0.75rem' }}>
                    {editingTagsFor === h.id ? (
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        <input
                          type="text"
                          value={tagInput}
                          onChange={e => setTagInput(e.target.value)}
                          placeholder="tag1, tag2, tag3"
                          style={{
                            padding: '0.5rem',
                            background: 'rgba(255,255,255,0.05)',
                            border: '1px solid rgba(255,255,255,0.1)',
                            borderRadius: '4px',
                            color: 'white',
                            fontSize: '0.8rem',
                            width: '200px'
                          }}
                          onKeyDown={e => {
                            if (e.key === 'Enter') {
                              const tags = tagInput.split(',').map(t => t.trim()).filter(t => t);
                              saveTags(h.id, tags);
                            } else if (e.key === 'Escape') {
                              setEditingTagsFor(null);
                              setTagInput('');
                            }
                          }}
                        />
                        <button
                          onClick={() => {
                            const tags = tagInput.split(',').map(t => t.trim()).filter(t => t);
                            saveTags(h.id, tags);
                          }}
                          style={{
                            padding: '0.5rem 0.75rem',
                            background: '#10b981',
                            color: '#000',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '0.75rem',
                            fontWeight: 'bold'
                          }}
                        >
                          ✓
                        </button>
                        <button
                          onClick={() => {
                            setEditingTagsFor(null);
                            setTagInput('');
                          }}
                          style={{
                            padding: '0.5rem 0.75rem',
                            background: '#ef4444',
                            color: '#000',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '0.75rem',
                            fontWeight: 'bold'
                          }}
                        >
                          ✕
                        </button>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                        {(h.tags || []).map(tag => (
                          <span
                            key={tag}
                            style={{
                              padding: '0.25rem 0.6rem',
                              background: 'rgba(139, 92, 246, 0.15)',
                              color: '#a78bfa',
                              borderRadius: '4px',
                              fontSize: '0.7rem',
                              fontWeight: 600
                            }}
                          >
                            🏷️ {tag}
                          </span>
                        ))}
                        <button
                          onClick={() => {
                            setEditingTagsFor(h.id);
                            setTagInput((h.tags || []).join(', '));
                          }}
                          style={{
                            padding: '0.25rem 0.5rem',
                            background: 'rgba(139, 92, 246, 0.1)',
                            color: '#a78bfa',
                            border: '1px solid rgba(139, 92, 246, 0.3)',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '0.7rem',
                            fontWeight: 600
                          }}
                          title="Editar tags"
                        >
                          ✏️
                        </button>
                      </div>
                    )}
                  </td>
                  <td style={{ padding: '0.75rem', fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {h.id}
                  </td>
                  <td style={{ padding: '0.75rem' }}>
                    <span style={{ 
                      fontFamily: 'monospace', 
                      fontSize: '0.85rem',
                      padding: '0.25rem 0.5rem',
                      background: 'rgba(99, 102, 241, 0.1)',
                      borderRadius: '4px',
                      color: '#818cf8',
                      fontWeight: 600
                    }}>
                      {h.ip}
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      {h.os.toLowerCase().includes('ubuntu') && '🟠'}
                      {h.os.toLowerCase().includes('debian') && '🔴'}
                      {h.os.toLowerCase().includes('centos') && '🟣'}
                      {h.os.toLowerCase().includes('fedora') && '🔵'}
                      {h.os.toLowerCase().includes('arch') && '🔷'}
                      {!h.os.toLowerCase().match(/ubuntu|debian|centos|fedora|arch/) && '🐧'}
                      <span style={{ fontSize: '0.85rem' }}>{h.os}</span>
                    </div>
                  </td>
                  <td style={{ padding: '0.75rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    {h.kernel_version}
                  </td>
                  <td style={{ padding: '0.75rem' }}>
                    <span style={{ 
                      fontSize: '0.75rem',
                      padding: '0.25rem 0.6rem',
                      borderRadius: '4px',
                      background: 'rgba(59, 130, 246, 0.15)',
                      color: '#60a5fa',
                      fontWeight: 700,
                      display: 'inline-block'
                    }}>
                      ⚙️ <b>{h.cpu_cores}</b> CORES
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem' }}>
                    <span style={{ 
                      fontSize: '0.75rem',
                      padding: '0.25rem 0.6rem',
                      borderRadius: '4px',
                      background: 'rgba(139, 92, 246, 0.15)',
                      color: '#a78bfa',
                      fontWeight: 700,
                      display: 'inline-block'
                    }}>
                      💾 <b>{(h.total_memory / 1024).toFixed(1)}</b> GB
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    {new Date(h.last_seen).toLocaleString('es-ES', { 
                      day: '2-digit', 
                      month: '2-digit', 
                      year: 'numeric', 
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}
                  </td>
                  <td style={{ padding: '0.75rem' }}>
                    <button
                      onClick={() => router.push(`/hosts/${h.id}`)}
                      style={{
                        padding: '0.4rem 0.8rem',
                        borderRadius: '4px',
                        border: '1px solid #667eea',
                        background: 'rgba(102, 126, 234, 0.2)',
                        color: '#667eea',
                        cursor: 'pointer',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        transition: 'all 0.2s ease'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = '#667eea';
                        e.currentTarget.style.color = 'white';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'rgba(102, 126, 234, 0.2)';
                        e.currentTarget.style.color = '#667eea';
                      }}
                      title="Ver detalles completos del host"
                    >
                      Ver Detalles
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </div>
      )}
    </div>
  );
}

/* ─── Alerts page ────────────────────────────────────────────────── */
function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [showResolved, setShowResolved] = useState(false);

  const reload = useCallback(() => {
    setLoading(true);
    getAlerts(showResolved).then(setAlerts).finally(() => setLoading(false));
  }, [showResolved]);

  useEffect(() => { reload(); }, [reload]);

  const handleResolve = async (id: number) => {
    const { resolveAlert } = await import('@/lib/api');
    await resolveAlert(id);
    reload();
  };

  const critical = alerts.filter(a => a.severity === 'critical' && !a.resolved).length;
  const warning = alerts.filter(a => a.severity === 'warning' && !a.resolved).length;
  const resolved = alerts.filter(a => a.resolved).length;

  return (
    <div className="page-content" style={{ height: 'calc(100vh - 2rem)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      {/* Header compacto moderno */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', padding: '0.75rem 0', flexShrink: 0 }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '2rem' }}>🚨</span>
            Alertas <span className="text-gradient">{showResolved ? 'Históricas' : 'Activas'}</span>
          </h1>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0', display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span><b>{alerts.length}</b> {showResolved ? 'alertas totales' : 'pendientes'}</span>
            {!showResolved && critical > 0 && (
              <span style={{ 
                padding: '0.15rem 0.5rem', 
                borderRadius: '4px', 
                background: 'rgba(239, 68, 68, 0.15)',
                color: '#ef4444',
                fontSize: '0.75rem',
                fontWeight: 600
              }}>🔴 {critical} críticas</span>
            )}
            {!showResolved && warning > 0 && (
              <span style={{ 
                padding: '0.15rem 0.5rem', 
                borderRadius: '4px', 
                background: 'rgba(245, 158, 11, 0.15)',
                color: '#f59e0b',
                fontSize: '0.75rem',
                fontWeight: 600
              }}>⚠️ {warning} advertencias</span>
            )}
            {showResolved && resolved > 0 && (
              <span style={{ 
                padding: '0.15rem 0.5rem', 
                borderRadius: '4px', 
                background: 'rgba(16, 185, 129, 0.15)',
                color: '#10b981',
                fontSize: '0.75rem',
                fontWeight: 600
              }}>✓ {resolved} resueltas</span>
            )}
          </p>
        </div>
        
        {/* Botones en la parte derecha */}
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          {alerts.length > 0 && (
            <button
              onClick={() => exportAlertsToCSV(alerts)}
              style={{
                padding: '0.75rem 1.25rem',
                background: '#8b5cf6',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.85rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={e => e.currentTarget.style.background = '#7c3aed'}
              onMouseLeave={e => e.currentTarget.style.background = '#8b5cf6'}
              title="Exportar alertas a CSV"
            >
              📊 Exportar CSV
            </button>
          )}
          
          {/* Toggle moderno */}
          <label style={{ 
            cursor: 'pointer', 
            userSelect: 'none',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.5rem 0.75rem',
            borderRadius: '6px',
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.1)',
            fontSize: '0.85rem',
          fontWeight: 600,
          transition: 'all 0.2s ease'
        }}>
          <input 
            type="checkbox" 
            checked={showResolved} 
            onChange={e => setShowResolved(e.target.checked)}
            style={{ width: '16px', height: '16px', cursor: 'pointer' }}
          />
          <span>Mostrar resueltas</span>
        </label>
        </div>
      </div>
      
      {loading ? (
        <div className="loading-msg">⏳ Cargando alertas...</div>
      ) : alerts.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🎉</div>
          <h3 className="empty-state-title">
            {showResolved ? 'No hay alertas en el historial' : '¡Todo está funcionando perfectamente!'}
          </h3>
          <p className="empty-state-text">
            {showResolved 
              ? 'Aún no se han registrado alertas en el sistema' 
              : 'No hay alertas activas en este momento'}
          </p>
        </div>
      ) : (
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <div className="table-wrap" style={{ flex: 1, overflow: 'auto' }}>
            <table className="lams-table" style={{ fontSize: '0.85rem' }}>
              <thead>
                <tr>
                  <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Severidad</th>
                  <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Host</th>
                <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Métrica</th>
                <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Valor</th>
                <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Mensaje</th>
                <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Fecha/Hora</th>
                <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Acción</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map(a => (
                <tr 
                  key={a.id} 
                  style={{ 
                    borderBottom: '1px solid rgba(255,255,255,0.05)',
                    background: a.severity === 'critical' && !a.resolved ? 'rgba(239, 68, 68, 0.05)' : 'transparent',
                    opacity: a.resolved ? 0.6 : 1
                  }}
                >
                  <td style={{ padding: '0.75rem' }}>
                    <span style={{ 
                      fontSize: '0.7rem',
                      padding: '0.25rem 0.6rem',
                      borderRadius: '4px',
                      background: a.severity === 'critical' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                      color: a.severity === 'critical' ? '#ef4444' : '#f59e0b',
                      fontWeight: 700,
                      display: 'inline-block',
                      textTransform: 'uppercase'
                    }}>
                      {a.severity === 'critical' ? '🔴 CRIT' : '⚠️ WARN'}
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem', fontWeight: 700, fontSize: '0.9rem' }}>
                    🖥️ {a.host_id}
                  </td>
                  <td style={{ padding: '0.75rem' }}>
                    <span style={{ 
                      fontSize: '0.75rem',
                      padding: '0.25rem 0.6rem',
                      borderRadius: '4px',
                      background: 'rgba(99, 102, 241, 0.15)',
                      color: '#818cf8',
                      fontWeight: 600,
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '0.3rem'
                    }}>
                      {a.metric === 'cpu_usage' && '⚡'}
                      {a.metric === 'memory_usage' && '💾'}
                      {a.metric === 'disk_usage' && '💿'}
                      {a.metric === 'temp_cpu' && '🌡️'}
                      {!['cpu_usage', 'memory_usage', 'disk_usage', 'temp_cpu'].includes(a.metric) && '📊'}
                      <span>{a.metric.replace('_', ' ')}</span>
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem' }}>
                    <span style={{ 
                      fontFamily: 'monospace', 
                      fontSize: '0.85rem', 
                      fontWeight: 700,
                      padding: '0.25rem 0.5rem',
                      background: 'rgba(255,255,255,0.05)',
                      borderRadius: '4px'
                    }}>
                      {a.value.toFixed(2)}
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem', maxWidth: '300px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    {a.message}
                  </td>
                  <td style={{ padding: '0.75rem', fontSize: '0.75rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                    {new Date(a.event_time).toLocaleString('es-ES', { 
                      day: '2-digit', 
                      month: '2-digit', 
                      year: 'numeric', 
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}
                  </td>
                  <td style={{ padding: '0.75rem' }}>
                    {!a.resolved ? (
                      <button 
                        onClick={() => handleResolve(a.id)}
                        style={{ 
                          padding: '0.4rem 0.8rem',
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          border: '1px solid #10b981',
                          background: 'rgba(16, 185, 129, 0.15)',
                          color: '#10b981',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          transition: 'all 0.2s ease',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.3rem'
                        }}
                        onMouseEnter={e => {
                          e.currentTarget.style.background = 'rgba(16, 185, 129, 0.25)';
                        }}
                        onMouseLeave={e => {
                          e.currentTarget.style.background = 'rgba(16, 185, 129, 0.15)';
                        }}
                      >
                        ✓ Resolver
                      </button>
                    ) : (
                      <span style={{ 
                        fontSize: '0.7rem',
                        padding: '0.25rem 0.6rem',
                        borderRadius: '4px',
                        background: 'rgba(16, 185, 129, 0.15)',
                        color: '#10b981',
                        fontWeight: 700,
                        display: 'inline-block'
                      }}>
                        ✓ RESUELTA
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </div>
      )}
    </div>
  );
}

/* ─── Docker page ───────────────────────────────────────────────── */
function DockerPage() {
  const [hosts, setHosts] = useState<Host[]>([]);
  const [selectedHost, setSelectedHost] = useState<string>('');
  const [containers, setContainers] = useState<import('@/lib/api').DockerContainer[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const loadContainers = useCallback(async () => {
    if (!selectedHost) return;
    setLoading(true);
    const { getContainers } = await import('@/lib/api');
    getContainers(selectedHost).then(setContainers).finally(() => setLoading(false));
  }, [selectedHost]);

  useEffect(() => { getHosts().then(h => { setHosts(h); if (h.length) setSelectedHost(h[0].id); }); }, []);
  useEffect(() => { loadContainers(); }, [loadContainers]);

  const handleAction = async (containerId: string, action: 'start' | 'stop' | 'restart') => {
    setActionLoading(containerId);
    try {
      const { dockerAction, getCommandStatus } = await import('@/lib/api');
      
      // Create the command
      const response = await dockerAction(selectedHost, containerId, action);
      const commandId = response.command_id;
      
      if (!commandId) {
        throw new Error('No se recibió command_id del servidor');
      }
      
      // Poll for command completion (max 30 seconds)
      const maxAttempts = 15;
      let attempts = 0;
      let commandCompleted = false;
      
      while (attempts < maxAttempts && !commandCompleted) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        try {
          const commandStatus = await getCommandStatus(commandId);
          
          if (commandStatus.status === 'completed') {
            commandCompleted = true;
            alert(`✅ Comando ${action} ejecutado exitosamente`);
            break;
          } else if (commandStatus.status === 'failed') {
            commandCompleted = true;
            alert(`❌ Error al ejecutar ${action}: ${commandStatus.result || 'Error desconocido'}`);
            break;
          }
          // Si está en 'executing' o 'pending', seguir esperando
        } catch (pollError) {
          console.error('Error polling command status:', pollError);
          // Continuar intentando
        }
        
        attempts++;
      }
      
      if (!commandCompleted) {
        alert(`⏳ Comando ${action} enviado, pero tomó más de lo esperado. Verifica el estado del contenedor.`);
      }
      
      // Reload containers
      await loadContainers();
    } catch (err) {
      console.error('Action failed:', err);
      alert(`Error ejecutando ${action}: ${err instanceof Error ? err.message : 'Error desconocido'}`);
    } finally {
      setActionLoading(null);
    }
  };

  const running = containers.filter(c => c.state === 'running').length;
  const stopped = containers.length - running;

  return (
    <div className="page-content" style={{ height: 'calc(100vh - 2rem)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      {/* Header compacto moderno */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', padding: '0.75rem 0', flexShrink: 0 }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '2rem' }}>🐳</span>
            Docker <span className="text-gradient">Containers</span>
          </h1>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0', display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span><b>{containers.length}</b> contenedor{containers.length !== 1 ? 'es' : ''}</span>
            {running > 0 && (
              <span style={{ 
                padding: '0.15rem 0.5rem', 
                borderRadius: '4px', 
                background: 'rgba(16, 185, 129, 0.15)',
                color: '#10b981',
                fontSize: '0.75rem',
                fontWeight: 600
              }}>● {running} activos</span>
            )}
            {stopped > 0 && (
              <span style={{ 
                padding: '0.15rem 0.5rem', 
                borderRadius: '4px', 
                background: 'rgba(107, 114, 128, 0.15)',
                color: '#9ca3af',
                fontSize: '0.75rem',
                fontWeight: 600
              }}>● {stopped} detenidos</span>
            )}
            {selectedHost && (
              <span style={{ fontSize: '0.75rem' }}>
                en <b>{hosts.find(h => h.id === selectedHost)?.hostname}</b>
              </span>
            )}
          </p>
        </div>
        
        {/* Select moderno */}
        <select
          className="lams-select"
          value={selectedHost}
          onChange={e => setSelectedHost(e.target.value)}
          style={{ 
            minWidth: '180px',
            padding: '0.5rem 0.75rem',
            fontSize: '0.85rem',
            fontWeight: 600
          }}
        >
          {hosts.map(h => <option key={h.id} value={h.id}>🖥️ {h.hostname}</option>)}
        </select>
      </div>
      
      {loading ? (
        <div className="loading-msg">⏳ Cargando contenedores...</div>
      ) : containers.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🐳</div>
          <h3 className="empty-state-title">No hay contenedores Docker</h3>
          <p className="empty-state-text">
            No se encontraron contenedores en {hosts.find(h => h.id === selectedHost)?.hostname || 'este host'}
          </p>
        </div>
      ) : (
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <div className="table-wrap" style={{ flex: 1, overflow: 'auto' }}>
            <table className="lams-table" style={{ fontSize: '0.85rem' }}>
              <thead>
                <tr>
                  <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Estado</th>
                  <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Nombre</th>
                  <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Imagen</th>
                  <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>CPU</th>
                <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Memoria</th>
                <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Creado</th>
                <th style={{ padding: '0.65rem', fontSize: '0.7rem' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {containers.map(c => (
                <tr 
                  key={c.id}
                  style={{ 
                    borderBottom: '1px solid rgba(255,255,255,0.05)',
                    background: c.state === 'running' ? 'transparent' : 'rgba(107, 114, 128, 0.05)'
                  }}
                >
                  <td style={{ padding: '0.75rem' }}>
                    <span style={{ 
                      fontSize: '0.7rem',
                      padding: '0.25rem 0.6rem',
                      borderRadius: '4px',
                      background: c.state === 'running' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(107, 114, 128, 0.2)',
                      color: c.state === 'running' ? '#10b981' : '#9ca3af',
                      fontWeight: 700,
                      display: 'inline-block',
                      textTransform: 'uppercase'
                    }}>
                      {c.state === 'running' ? '🟢 RUN' : '⚪ STOP'}
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem', fontWeight: 700, fontSize: '0.95rem' }}>
                    🐳 {c.name}
                  </td>
                  <td style={{ padding: '0.75rem' }}>
                    <span style={{ 
                      fontFamily: 'monospace', 
                      fontSize: '0.75rem',
                      color: 'var(--text-muted)',
                      padding: '0.25rem 0.5rem',
                      background: 'rgba(99, 102, 241, 0.1)',
                      borderRadius: '4px'
                    }}>
                      {c.image}
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem' }}>
                    <span style={{ 
                      fontSize: '0.75rem',
                      padding: '0.25rem 0.6rem',
                      borderRadius: '4px',
                      background: 'rgba(139, 92, 246, 0.15)',
                      color: '#a78bfa',
                      fontWeight: 700,
                      display: 'inline-block'
                    }}>
                      ⚡ <b>{c.cpu_percent.toFixed(2)}%</b>
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem' }}>
                    <span style={{ 
                      fontSize: '0.75rem',
                      padding: '0.25rem 0.6rem',
                      borderRadius: '4px',
                      background: 'rgba(59, 130, 246, 0.15)',
                      color: '#60a5fa',
                      fontWeight: 700,
                      display: 'inline-block'
                    }}>
                      💾 <b>{c.memory_usage.toFixed(1)}</b> MB
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem', fontSize: '0.75rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                    {new Date(c.created_at).toLocaleString('es-ES', { 
                      day: '2-digit', 
                      month: '2-digit', 
                      year: 'numeric', 
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}
                  </td>
                  <td style={{ padding: '0.75rem' }}>
                    <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                      {c.state !== 'running' && (
                        <button
                          onClick={() => handleAction(c.id, 'start')}
                          disabled={actionLoading === c.id}
                          style={{ 
                            padding: '0.35rem 0.65rem',
                            fontSize: '0.7rem',
                            fontWeight: 700,
                            border: '1px solid #10b981',
                            background: actionLoading === c.id ? 'rgba(107, 114, 128, 0.2)' : 'rgba(16, 185, 129, 0.15)',
                            color: actionLoading === c.id ? '#9ca3af' : '#10b981',
                            borderRadius: '4px',
                            cursor: actionLoading === c.id ? 'not-allowed' : 'pointer',
                            transition: 'all 0.2s ease',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.3rem',
                            whiteSpace: 'nowrap'
                          }}
                          onMouseEnter={e => {
                            if (actionLoading !== c.id) {
                              e.currentTarget.style.background = 'rgba(16, 185, 129, 0.25)';
                            }
                          }}
                          onMouseLeave={e => {
                            if (actionLoading !== c.id) {
                              e.currentTarget.style.background = 'rgba(16, 185, 129, 0.15)';
                            }
                          }}
                        >
                          {actionLoading === c.id ? '⏳' : '▶️'} START
                        </button>
                      )}
                      {c.state === 'running' && (
                        <>
                          <button
                            onClick={() => handleAction(c.id, 'stop')}
                            disabled={actionLoading === c.id}
                            style={{ 
                              padding: '0.35rem 0.65rem',
                              fontSize: '0.7rem',
                              fontWeight: 700,
                              border: '1px solid #f59e0b',
                              background: actionLoading === c.id ? 'rgba(107, 114, 128, 0.2)' : 'rgba(245, 158, 11, 0.15)',
                              color: actionLoading === c.id ? '#9ca3af' : '#f59e0b',
                              borderRadius: '4px',
                              cursor: actionLoading === c.id ? 'not-allowed' : 'pointer',
                              transition: 'all 0.2s ease',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.3rem',
                              whiteSpace: 'nowrap'
                            }}
                            onMouseEnter={e => {
                              if (actionLoading !== c.id) {
                                e.currentTarget.style.background = 'rgba(245, 158, 11, 0.25)';
                              }
                            }}
                            onMouseLeave={e => {
                              if (actionLoading !== c.id) {
                                e.currentTarget.style.background = 'rgba(245, 158, 11, 0.15)';
                              }
                            }}
                          >
                            {actionLoading === c.id ? '⏳' : '⏸️'} STOP
                          </button>
                          <button
                            onClick={() => handleAction(c.id, 'restart')}
                            disabled={actionLoading === c.id}
                            style={{ 
                              padding: '0.35rem 0.65rem',
                              fontSize: '0.7rem',
                              fontWeight: 700,
                              border: '1px solid #3b82f6',
                              background: actionLoading === c.id ? 'rgba(107, 114, 128, 0.2)' : 'rgba(59, 130, 246, 0.15)',
                              color: actionLoading === c.id ? '#9ca3af' : '#60a5fa',
                              borderRadius: '4px',
                              cursor: actionLoading === c.id ? 'not-allowed' : 'pointer',
                              transition: 'all 0.2s ease',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.3rem',
                              whiteSpace: 'nowrap'
                            }}
                            onMouseEnter={e => {
                              if (actionLoading !== c.id) {
                                e.currentTarget.style.background = 'rgba(59, 130, 246, 0.25)';
                              }
                            }}
                            onMouseLeave={e => {
                              if (actionLoading !== c.id) {
                                e.currentTarget.style.background = 'rgba(59, 130, 246, 0.15)';
                              }
                            }}
                          >
                            {actionLoading === c.id ? '⏳' : '🔄'} RESTART
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </div>
      )}
    </div>
  );
}

/* ─── Alert Rules page ──────────────────────────────────────────── */
function RulesPage() {
  const [rules, setRules] = useState<import('@/lib/api').AlertRule[]>([]);
  const [hosts, setHosts] = useState<Host[]>([]);
  const [form, setForm] = useState({ metric_name: 'cpu_usage', operator: '>', threshold: 80, severity: 'warning', duration_minutes: 1, host_id: '' });
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    const { getAlertRules } = await import('@/lib/api');
    getAlertRules().then(setRules).finally(() => setLoading(false));
  }, []);

  useEffect(() => { reload(); getHosts().then(setHosts); }, [reload]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const { createAlertRule } = await import('@/lib/api');
    await createAlertRule({ ...form, host_id: form.host_id || null });
    reload();
  };

  const handleDelete = async (id: number) => {
    const { deleteAlertRule } = await import('@/lib/api');
    await deleteAlertRule(id);
    reload();
  };

  return (
    <div className="page-content" style={{ height: 'calc(100vh - 2rem)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ flexShrink: 0, marginBottom: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: '1.75rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '2rem' }}>⚙️</span>
              Reglas de <span className="text-gradient">Alertas</span>
            </h1>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0' }}>
              {rules.length} regla{rules.length !== 1 ? 's' : ''} de alertas configurada{rules.length !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
      </div>

      {/* Form */}
      <div className="card" style={{ marginBottom: '0.75rem', flexShrink: 0, padding: '0.75rem' }}>
        <h3 style={{ fontSize: '0.8rem', marginBottom: '0.5rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          ➕ Nueva Regla
        </h3>
        <form className="rule-form" onSubmit={handleCreate} style={{ alignItems: 'end' }}>
          <div className="field">
            <label style={{ fontWeight: 600, fontSize: '0.7rem', marginBottom: '0.25rem', display: 'block', color: 'var(--text-primary)' }}>Métrica</label>
            <select value={form.metric_name} onChange={e => setForm(f => ({ ...f, metric_name: e.target.value }))}>
              <option value="cpu_usage">⚡ CPU Usage</option>
              <option value="memory_used">💾 Memory Used</option>
              <option value="disk_usage_percent">💿 Disk Usage %</option>
              <option value="swap_used">🔄 Swap Used</option>
              <option value="temp_cpu">🌡️ CPU Temp</option>
            </select>
          </div>
          <div className="field">
            <label style={{ fontWeight: 600, fontSize: '0.7rem', marginBottom: '0.25rem', display: 'block', color: 'var(--text-primary)' }}>Operador</label>
            <select value={form.operator} onChange={e => setForm(f => ({ ...f, operator: e.target.value }))}>
              <option value=">">Mayor que ({'>'})</option>
              <option value="<">Menor que ({'<'})</option>
              <option value="==">Igual a (==)</option>
            </select>
          </div>
          <div className="field">
            <label style={{ fontWeight: 600, fontSize: '0.7rem', marginBottom: '0.25rem', display: 'block', color: 'var(--text-primary)' }}>Umbral</label>
            <input type="number" value={form.threshold} onChange={e => setForm(f => ({ ...f, threshold: Number(e.target.value) }))} />
          </div>
          <div className="field">
            <label style={{ fontWeight: 600, fontSize: '0.7rem', marginBottom: '0.25rem', display: 'block', color: 'var(--text-primary)' }}>Severidad</label>
            <select value={form.severity} onChange={e => setForm(f => ({ ...f, severity: e.target.value }))}>
              <option value="warning">⚠️ Warning</option>
              <option value="critical">🔴 Critical</option>
            </select>
          </div>
          <div className="field">
            <label style={{ fontWeight: 600, fontSize: '0.7rem', marginBottom: '0.25rem', display: 'block', color: 'var(--text-primary)' }}>Duración (min)</label>
            <input type="number" min={1} value={form.duration_minutes} onChange={e => setForm(f => ({ ...f, duration_minutes: Number(e.target.value) }))} />
          </div>
          <div className="field">
            <label style={{ fontWeight: 600, fontSize: '0.7rem', marginBottom: '0.25rem', display: 'block', color: 'var(--text-primary)' }}>Host</label>
            <select value={form.host_id} onChange={e => setForm(f => ({ ...f, host_id: e.target.value }))}>
              <option value="">🌐 Todos los hosts</option>
              {hosts.map(h => <option key={h.id} value={h.id}>🖥️ {h.hostname}</option>)}
            </select>
          </div>
          <button type="submit" className="btn-primary" style={{ padding: '0.5rem 1rem', fontWeight: 700, fontSize: '0.8rem' }}>
            ✓ Crear
          </button>
        </form>
      </div>

      {loading ? (
        <div className="loading-msg">⏳ Cargando reglas...</div>
      ) : rules.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">⚙️</div>
          <h3 className="empty-state-title">No hay reglas configuradas</h3>
          <p className="empty-state-text">Crea tu primera regla de alerta usando el formulario superior</p>
        </div>
      ) : (
        <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <div className="table-wrap" style={{ flex: 1, overflow: 'auto' }}>
            <table className="lams-table">
              <thead>
                <tr>
                  <th>Métrica</th>
                  <th>Condición</th>
                  <th>Severidad</th>
                  <th>Duración</th>
                  <th>Host</th>
                  <th>Acción</th>
                </tr>
              </thead>
              <tbody>
                {rules.map(r => (
                  <tr key={r.id}>
                    <td>
                      <span className="badge badge-info">
                        {r.metric_name === 'cpu_usage' && '⚡'}
                        {r.metric_name === 'memory_used' && '💾'}
                        {r.metric_name === 'disk_usage_percent' && '💿'}
                        {r.metric_name === 'swap_used' && '🔄'}
                        {r.metric_name === 'temp_cpu' && '🌡️'}
                        {' '}{r.metric_name}
                      </span>
                    </td>
                    <td style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '0.95rem' }}>
                      {r.operator} {r.threshold}
                    </td>
                    <td>
                      <span className={`badge ${r.severity === 'critical' ? 'badge-critical' : 'badge-warning'}`}>
                        {r.severity === 'critical' ? '🔴' : '⚠️'} {r.severity.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <span className="badge badge-info">
                        ⏱️ {r.duration_minutes} min
                      </span>
                    </td>
                    <td style={{ fontWeight: 600 }}>
                      {r.host_id ? `🖥️ ${r.host_id}` : <span style={{ color: 'var(--text-secondary)' }}>🌐 Todos</span>}
                    </td>
                    <td>
                      <button 
                        className="btn-sm btn-danger" 
                        onClick={() => handleDelete(r.id)}
                        style={{ padding: '0.5rem 1rem' }}
                      >
                        🗑️ Eliminar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Users Page ─────────────────────────────────────────────────── */
function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formData, setFormData] = useState({ email: '', password: '', is_admin: false });
  const [formLoading, setFormLoading] = useState(false);

  const loadUsers = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getUsers();
      setUsers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar usuarios');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setFormLoading(true);
    try {
      if (editingId) {
        const updateData: UserUpdate = {
          email: formData.email,
          is_admin: formData.is_admin,
          ...(formData.password ? { password: formData.password } : {})
        };
        await updateUser(editingId, updateData);
      } else {
        await createUser(formData as UserCreate);
      }
      await loadUsers();
      setFormData({ email: '', password: '', is_admin: false });
      setShowForm(false);
      setEditingId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al guardar usuario');
    } finally {
      setFormLoading(false);
    }
  };

  const handleEdit = (user: User) => {
    setEditingId(user.id);
    setFormData({ email: user.email, password: '', is_admin: user.is_admin });
    setShowForm(true);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('¿Eliminar este usuario?')) return;
    try {
      await deleteUser(id);
      await loadUsers();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Error al eliminar');
    }
  };

  const handleCancel = () => {
    setFormData({ email: '', password: '', is_admin: false });
    setShowForm(false);
    setEditingId(null);
    setError('');
  };

  return (
    <div className="page-content" style={{ height: 'calc(100vh - 2rem)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ flexShrink: 0, marginBottom: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: '1.75rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '2rem' }}>👤</span>
              <span className="text-gradient">Usuarios</span>
            </h1>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0' }}>
              {users.length} usuario{users.length !== 1 ? 's' : ''} registrado{users.length !== 1 ? 's' : ''}
            </p>
          </div>
          <button 
            className="btn-primary"
            onClick={() => setShowForm(!showForm)}
            style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
          >
            {showForm ? '❌ Cancelar' : '➕ Nuevo Usuario'}
          </button>
        </div>
      </div>

      {/* Create/Edit Form */}
      {showForm && (
        <div className="card" style={{ marginBottom: '1rem', flexShrink: 0, padding: '1rem' }}>
          <h3 style={{ fontSize: '0.9rem', marginBottom: '0.75rem', fontWeight: 700 }}>
            {editingId ? '✏️ Editar Usuario' : '➕ Nuevo Usuario'}
          </h3>
          {error && <div style={{ padding: '0.5rem', marginBottom: '0.75rem', background: 'rgba(239,68,68,0.1)', border: '1px solid #ef4444', borderRadius: '0.25rem', color: '#ef4444', fontSize: '0.8rem' }}>{error}</div>}
          <form onSubmit={handleSubmit} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            <div className="field">
              <label style={{ fontWeight: 600, fontSize: '0.75rem', marginBottom: '0.25rem', display: 'block' }}>Email</label>
              <input
                type="email"
                required
                value={formData.email}
                onChange={e => setFormData({ ...formData, email: e.target.value })}
                placeholder="usuario@ejemplo.com"
              />
            </div>
            <div className="field">
              <label style={{ fontWeight: 600, fontSize: '0.75rem', marginBottom: '0.25rem', display: 'block' }}>
                Contraseña {editingId && <span style={{ color: 'var(--text-secondary)', fontWeight: 400 }}>(dejar vacío para no cambiar)</span>}
              </label>
              <input
                type="password"
                required={!editingId}
                value={formData.password}
                onChange={e => setFormData({ ...formData, password: e.target.value })}
                placeholder={editingId ? 'Nueva contraseña (opcional)' : 'Contraseña'}
              />
            </div>
            <div className="field">
              <label style={{ fontWeight: 600, fontSize: '0.75rem', marginBottom: '0.25rem', display: 'block' }}>Rol</label>
              <select value={formData.is_admin ? 'Admin' : 'User'} onChange={e => setFormData({ ...formData, is_admin: e.target.value === 'Admin' })}>
                <option value="User">User</option>
                <option value="Admin">Admin</option>
              </select>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-end' }}>
              <button type="submit" className="btn-primary" disabled={formLoading} style={{ flex: 1 }}>
                {formLoading ? '⏳' : editingId ? '💾 Actualizar' : '✓ Crear'}
              </button>
              <button type="button" className="btn-secondary" onClick={handleCancel} style={{ flex: 1 }}>
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Users Table */}
      <div className="card" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1, overflow: 'auto' }}>
          {loading ? (
            <div className="loading-msg">Cargando usuarios...</div>
          ) : (
            <table className="lams-table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Rol</th>
                  <th>Fecha de Registro</th>
                  <th style={{ textAlign: 'right' }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 ? (
                  <tr><td colSpan={4} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>No hay usuarios</td></tr>
                ) : (
                  users.map(user => (
                    <tr key={user.id}>
                      <td style={{ fontWeight: 500 }}>{user.email}</td>
                      <td>
                        <span style={{ 
                          padding: '0.25rem 0.5rem', 
                          borderRadius: '0.25rem', 
                          fontSize: '0.75rem', 
                          fontWeight: 600,
                          background: user.is_admin ? 'rgba(239,68,68,0.2)' : 'rgba(59,130,246,0.2)',
                          color: user.is_admin ? '#ef4444' : '#3b82f6'
                        }}>
                          {user.is_admin ? 'Admin' : 'User'}
                        </span>
                      </td>
                      <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        {new Date(user.created_at).toLocaleString('es-ES')}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button 
                          className="btn-icon" 
                          title="Editar usuario"
                          onClick={() => handleEdit(user)}
                          style={{ marginRight: '0.5rem' }}
                        >
                          ✏️
                        </button>
                        <button 
                          className="btn-icon" 
                          title="Eliminar usuario"
                          onClick={() => handleDelete(user.id)}
                        >
                          🗑️
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Notifications Page ─────────────────────────────────────────── */
function NotificationsPage() {
  type ProviderType = 'email' | 'slack' | 'discord';
  const [configs, setConfigs] = useState<NotificationConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [provider, setProvider] = useState<ProviderType>('email');
  const [severityFilter, setSeverityFilter] = useState<'all' | 'warning' | 'critical'>('all');
  const [config, setConfig] = useState<Record<string, string>>({});
  const [formLoading, setFormLoading] = useState(false);

  const loadConfigs = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getNotificationConfigs();
      setConfigs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar configuraciones');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadConfigs(); }, [loadConfigs]);

  const emailFields = ['smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'from_email', 'to_email'];
  const slackFields = ['webhook_url', 'username', 'icon_emoji'];
  const discordFields = ['webhook_url', 'username'];
  const currentFields = provider === 'email' ? emailFields : provider === 'slack' ? slackFields : discordFields;

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setFormLoading(true);
    try {
      const data: NotificationConfigCreate = {
        provider,
        config: {
          ...config,
          ...(provider === 'email' && { smtp_port: parseInt(config.smtp_port || '587'), use_tls: true }),
        },
        enabled: true,
        severity_filter: severityFilter,
      };
      await createNotificationConfig(data);
      await loadConfigs();
      setConfig({});
      setProvider('email');
      setSeverityFilter('all');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al crear configuración');
    } finally {
      setFormLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('¿Eliminar esta configuración?')) return;
    try {
      await deleteNotificationConfig(id);
      await loadConfigs();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Error al eliminar');
    }
  };

  const handleToggle = async (cfg: NotificationConfig) => {
    try {
      await updateNotificationConfig(cfg.id, { enabled: !cfg.enabled });
      await loadConfigs();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Error al actualizar');
    }
  };

  const handleTest = async (id: number) => {
    try {
      const result = await testNotificationConfig(id);
      alert('✅ ' + result.message);
    } catch (err) {
      alert('❌ ' + (err instanceof Error ? err.message : 'Error'));
    }
  };

  const providerIcons: Record<ProviderType, string> = { email: '📧', slack: '💬', discord: '🎮' };
  const severityBadge = {
    all: { label: 'Todas', color: '#3b82f6' },
    warning: { label: 'Warning+', color: '#f59e0b' },
    critical: { label: 'Critical', color: '#ef4444' },
  };

  return (
    <div className="page-content" style={{ height: 'calc(100vh - 2rem)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ flexShrink: 0, marginBottom: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: '1.75rem', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '2rem' }}>🔔</span>
              <span className="text-gradient">Notificaciones</span>
            </h1>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0' }}>
              {configs.length} canal{configs.length !== 1 ? 'es' : ''} configurado{configs.length !== 1 ? 's' : ''} · Configura cómo deseas recibir alertas
            </p>
          </div>
        </div>
      </div>

      {/* Create Form */}
      <div className="card" style={{ marginBottom: '0.75rem', flexShrink: 0, padding: '0.75rem' }}>
        <h3 style={{ fontSize: '0.8rem', marginBottom: '0.5rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          ➕ Nuevo Canal de Notificación
        </h3>
        <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
            <div className="field">
              <label style={{ fontWeight: 600, fontSize: '0.7rem', marginBottom: '0.25rem', display: 'block', color: 'var(--text-primary)' }}>Proveedor</label>
              <select value={provider} onChange={e => { setProvider(e.target.value as ProviderType); setConfig({}); }}>
                <option value="email">📧 Email (SMTP)</option>
                <option value="slack">💬 Slack</option>
                <option value="discord">🎮 Discord</option>
              </select>
            </div>
            <div className="field">
              <label style={{ fontWeight: 600, fontSize: '0.7rem', marginBottom: '0.25rem', display: 'block', color: 'var(--text-primary)' }}>Nivel de Severidad</label>
              <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value as any)}>
                <option value="all">📊 Todas las alertas</option>
                <option value="warning">⚠️ Warning y Critical</option>
                <option value="critical">🔴 Solo Critical</option>
              </select>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
            {currentFields.map(field => (
              <div key={field} className="field">
                <label style={{ fontWeight: 600, fontSize: '0.7rem', marginBottom: '0.25rem', display: 'block', color: 'var(--text-primary)', textTransform: 'capitalize' }}>
                  {field.replace(/_/g, ' ')}
                </label>
                <input
                  type={field.includes('password') ? 'password' : 'text'}
                  value={config[field] || ''}
                  onChange={e => setConfig({ ...config, [field]: e.target.value })}
                  placeholder={field === 'smtp_port' ? '587' : field === 'webhook_url' && provider === 'slack' ? 'https://hooks.slack.com/...' : field === 'webhook_url' ? 'https://discord.com/api/webhooks/...' : ''}
                />
              </div>
            ))}
          </div>
          {error && <p style={{ color: 'var(--accent-danger)', marginTop: '-0.5rem', fontSize: '0.75rem' }}>{error}</p>}
          <button 
            type="submit" 
            className="btn-primary" 
            disabled={formLoading || currentFields.some(f => !config[f])}
            style={{ alignSelf: 'flex-start', padding: '0.5rem 1rem', fontWeight: 700, fontSize: '0.8rem' }}
          >
            {formLoading ? '⏳ Creando...' : '✓ Crear'}
          </button>
        </form>
      </div>

      {/* List */}
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <h3 style={{ fontSize: '0.8rem', marginBottom: '0.5rem', flexShrink: 0, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          📋 Canales Activos
        </h3>
        
        {loading ? (
          <div className="loading-msg">⏳ Cargando configuraciones...</div>
        ) : configs.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🔕</div>
            <h3 className="empty-state-title">No hay notificaciones configuradas</h3>
            <p className="empty-state-text">Crea tu primer canal de notificación usando el formulario superior</p>
          </div>
        ) : (
          <div style={{ flex: 1, overflow: 'auto', display: 'grid', gap: '0.75rem', alignContent: 'start' }}>
          {configs.map(cfg => {
            const badge = severityBadge[cfg.severity_filter as keyof typeof severityBadge];
            return (
              <div key={cfg.id} className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem' }}>
                <div>
                  <h3 style={{ fontSize: '0.95rem', marginBottom: '0.35rem', fontWeight: 700 }}>
                    {providerIcons[cfg.provider]} {cfg.provider.charAt(0).toUpperCase() + cfg.provider.slice(1)}
                    {!cfg.enabled && <span className="badge badge-muted" style={{ marginLeft: '0.5rem', fontSize: '0.65rem' }}>DESACTIVADO</span>}
                  </h3>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                    {cfg.provider === 'email' && `📬 ${cfg.config.to_email}`}
                    {cfg.provider !== 'email' && '🔗 Webhook configurado'}
                  </div>
                  <span 
                    className="badge" 
                    style={{ 
                      backgroundColor: badge.color + '22', 
                      color: badge.color, 
                      border: `1px solid ${badge.color}`,
                      fontSize: '0.7rem'
                    }}
                  >
                    {badge.label}
                  </span>
                </div>
                <div className="table-actions">
                  <button 
                    className={`btn-sm ${cfg.enabled ? 'btn-warning' : 'btn-success'}`}
                    onClick={() => handleToggle(cfg)}
                    title={cfg.enabled ? 'Desactivar' : 'Activar'}
                    style={{ fontSize: '0.75rem', padding: '0.35rem 0.65rem' }}
                  >
                    {cfg.enabled ? '⏸️ Pausar' : '▶️ Activar'}
                  </button>
                  <button 
                    className="btn-sm btn-primary" 
                    onClick={() => handleTest(cfg.id)}
                    title="Enviar notificación de prueba"
                    style={{ fontSize: '0.75rem', padding: '0.35rem 0.65rem' }}
                  >
                    🧪 Probar
                  </button>
                  <button 
                    className="btn-sm btn-danger" 
                    onClick={() => handleDelete(cfg.id)}
                    title="Eliminar configuración"
                    style={{ fontSize: '0.75rem', padding: '0.35rem 0.65rem' }}
                  >
                    🗑️ Eliminar
                  </button>
                </div>
              </div>
            );
          })}
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Settings Page ──────────────────────────────────────────────── */
function SettingsPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'modules' | 'security' | 'system' | 'notifications'>('modules');
  
  // Configuraciones guardadas en localStorage
  const [config, setConfig] = useState(() => {
    const stored = localStorage.getItem('lams_settings');
    return stored ? JSON.parse(stored) : {
      modules: {
        dashboard: true,
        hosts: true,
        alerts: true,
        docker: true,
        rules: true,
        notifications: true,
        users: true
      },
      security: {
        sessionTimeout: 30, // minutos
        autoRefresh: 15, // segundos
        requireStrongPassword: true,
        twoFactorAuth: false
      },
      system: {
        metricsRetentionDays: 30,
        aggregationDays: 7,
        cleanupHour: 2,
        maxHostsPerUser: 50,
        enableDocker: true
      },
      notifications: {
        emailEnabled: false,
        slackEnabled: false,
        discordEnabled: false,
        defaultSeverity: 'all'
      }
    };
  });

  const saveConfig = (newConfig: typeof config) => {
    setConfig(newConfig);
    localStorage.setItem('lams_settings', JSON.stringify(newConfig));
  };

  // Verificación del rol de administrador
  const isAdmin = user?.is_admin === true;

  if (!isAdmin) {
    return (
      <div className="page-content">
        <div className="card" style={{ maxWidth: '700px', margin: '2rem auto', padding: '3rem' }}>
          <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>🔒 Acceso Denegado</h2>
            <p style={{ color: 'var(--text-secondary)' }}>
              Solo los administradores pueden acceder a la configuración del sistema.
            </p>
          </div>
          
          {/* Panel de información de debug */}
          <div style={{ 
            background: 'rgba(255, 193, 7, 0.1)', 
            border: '1px solid rgba(255, 193, 7, 0.3)',
            borderRadius: '8px',
            padding: '1.5rem',
            marginTop: '2rem'
          }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              🔍 Información de Debug
            </h3>
            <div style={{ fontSize: '0.9rem', fontFamily: 'monospace', lineHeight: '1.8' }}>
              <div><strong>Email:</strong> {user?.email || 'N/A'}</div>
              <div><strong>Administrador:</strong> <span style={{ color: '#ffc107', fontWeight: 'bold' }}>{user?.is_admin ? 'Sí' : 'No'}</span></div>
              <div><strong>ID:</strong> {user?.id || 'N/A'}</div>
            </div>
          </div>

          {/* Instrucciones de acceso */}
          <div style={{ 
            background: 'rgba(74, 222, 128, 0.1)', 
            border: '1px solid rgba(74, 222, 128, 0.3)',
            borderRadius: '8px',
            padding: '1.5rem',
            marginTop: '1rem'
          }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              💡 ¿Cómo acceder?
            </h3>
            <div style={{ fontSize: '0.9rem', lineHeight: '1.8', color: 'var(--text-secondary)' }}>
              <p style={{ marginBottom: '1rem' }}>Para acceder a la configuración del sistema, debes iniciar sesión con un usuario que tenga rol de <strong>Administrador</strong>.</p>
              
              <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '6px', marginBottom: '1rem' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem', color: '#4ade80' }}>
                  🔑 Credenciales del administrador por defecto:
                </div>
                <div style={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                  <div><strong>Email:</strong> admin@lams.io</div>
                  <div><strong>Password:</strong> lams2024</div>
                </div>
              </div>

              <p style={{ fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                <strong>Pasos:</strong>
              </p>
              <ol style={{ fontSize: '0.85rem', paddingLeft: '1.5rem', margin: 0 }}>
                <li>Cierra sesión usando el botón "Salir" en el menú lateral</li>
                <li>Inicia sesión con las credenciales de administrador</li>
                <li>Vuelve a acceder a esta página de Configuración</li>
              </ol>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      {/* Header - Fixed */}
      <div className="page-header" style={{ flexShrink: 0 }}>
        <div>
          <h1 className="page-title">
            <span className="page-title-icon">⚙️</span>
            Configuración del Sistema
          </h1>
          <p className="page-description">
            Gestiona módulos, seguridad y parámetros generales de LAMS
          </p>
        </div>
      </div>

      {/* Tabs - Fixed */}
      <div style={{ 
        display: 'flex', 
        gap: '0.5rem', 
        marginBottom: '1rem',
        borderBottom: '2px solid var(--border-light)',
        paddingBottom: '0.5rem',
        flexShrink: 0
      }}>
        {[
          { id: 'modules', label: '📦 Módulos', icon: '📦' },
          { id: 'security', label: '🔒 Seguridad', icon: '🔒' },
          { id: 'system', label: '⚙️ Sistema', icon: '⚙️' },
          { id: 'notifications', label: '🔔 Notificaciones', icon: '🔔' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            style={{
              padding: '0.75rem 1.5rem',
              borderRadius: '8px 8px 0 0',
              border: 'none',
              background: activeTab === tab.id ? 'var(--bg-card)' : 'transparent',
              color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '0.95rem',
              fontWeight: activeTab === tab.id ? 600 : 400,
              transition: 'all 0.3s ease',
              borderBottom: activeTab === tab.id ? '2px solid var(--accent-brand)' : 'none'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content Container - Scrollable */}
      <div style={{ 
        flex: 1, 
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column'
      }}>
        <div style={{
          flex: 1,
          overflowY: 'auto',
          paddingRight: '0.5rem'
        }}>
          {/* Tab: Módulos */}
          {activeTab === 'modules' && (
        <div className="card">
          <h2 style={{ fontSize: '0.8rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            📦 Gestión de Módulos
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.2rem', fontSize: '0.66rem' }}>
            Activa o desactiva módulos del dashboard. Los cambios se aplicarán inmediatamente.
          </p>
          
          <div style={{ display: 'grid', gap: '1rem' }}>
            {Object.entries(config.modules).map(([module, enabled]) => (
              <div
                key={module}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '1rem',
                  background: 'rgba(255,255,255,0.03)',
                  borderRadius: '8px',
                  border: '1px solid var(--border-light)',
                  transition: 'all 0.3s ease'
                }}
              >
                <div>
                  <div style={{ fontSize: '0.72rem', fontWeight: 600, marginBottom: '0.2rem', textTransform: 'capitalize' }}>
                    {getModuleIcon(module)} {module}
                  </div>
                  <div style={{ fontSize: '0.64rem', color: 'var(--text-secondary)' }}>
                    {getModuleDescription(module)}
                  </div>
                </div>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', cursor: 'pointer' }}>
                  <span style={{ fontSize: '0.64rem', color: 'var(--text-secondary)' }}>
                    {enabled ? 'Activo' : 'Inactivo'}
                  </span>
                  <input
                    type="checkbox"
                    checked={enabled as boolean}
                    onChange={(e) => {
                      const newConfig = {
                        ...config,
                        modules: { ...config.modules, [module]: e.target.checked }
                      };
                      saveConfig(newConfig);
                    }}
                    style={{
                      width: '48px',
                      height: '24px',
                      cursor: 'pointer',
                      accentColor: 'var(--accent-brand)'
                    }}
                  />
                </label>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Seguridad */}
      {activeTab === 'security' && (
        <div className="card">
          <h2 style={{ fontSize: '0.8rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            🔒 Configuración de Seguridad
          </h2>
          
          <div style={{ display: 'grid', gap: '1rem' }}>
            {/* Session Timeout */}
            <div>
              <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, marginBottom: '0.4rem' }}>
                ⏱️ Tiempo de Inactividad (minutos)
              </label>
              <p style={{ fontSize: '0.64rem', color: 'var(--text-secondary)', marginBottom: '0.6rem' }}>
                La sesión se cerrará automáticamente después de este tiempo sin actividad
              </p>
              <input
                type="number"
                min="5"
                max="1440"
                value={config.security.sessionTimeout}
                onChange={(e) => {
                  const newConfig = {
                    ...config,
                    security: { ...config.security, sessionTimeout: parseInt(e.target.value) }
                  };
                  saveConfig(newConfig);
                }}
                style={{
                  padding: '0.4rem',
                  borderRadius: '6px',
                  border: '1px solid var(--border-light)',
                  background: 'var(--bg-surface)',
                  color: 'var(--text-primary)',
                  fontSize: '0.72rem',
                  width: '130px'
                }}
              />
              <span style={{ marginLeft: '0.4rem', fontSize: '0.64rem', color: 'var(--text-secondary)' }}>minutos</span>
            </div>

            {/* Auto Refresh */}
            <div>
              <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, marginBottom: '0.4rem' }}>
                🔄 Intervalo de Actualización (segundos)
              </label>
              <p style={{ fontSize: '0.64rem', color: 'var(--text-secondary)', marginBottom: '0.6rem' }}>
                Frecuencia con la que se actualizan los datos del dashboard
              </p>
              <input
                type="number"
                min="5"
                max="300"
                value={config.security.autoRefresh}
                onChange={(e) => {
                  const newConfig = {
                    ...config,
                    security: { ...config.security, autoRefresh: parseInt(e.target.value) }
                  };
                  saveConfig(newConfig);
                }}
                style={{
                  padding: '0.4rem',
                  borderRadius: '6px',
                  border: '1px solid var(--border-light)',
                  background: 'var(--bg-surface)',
                  color: 'var(--text-primary)',
                  fontSize: '0.72rem',
                  width: '130px'
                }}
              />
              <span style={{ marginLeft: '0.4rem', fontSize: '0.64rem', color: 'var(--text-secondary)' }}>segundos</span>
            </div>

            {/* Password Policy */}
            <div style={{ 
              padding: '0.8rem',
              background: 'rgba(255,255,255,0.03)',
              borderRadius: '6px',
              border: '1px solid var(--border-light)'
            }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={config.security.requireStrongPassword}
                  onChange={(e) => {
                    const newConfig = {
                      ...config,
                      security: { ...config.security, requireStrongPassword: e.target.checked }
                    };
                    saveConfig(newConfig);
                  }}
                  style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: 'var(--accent-brand)' }}
                />
                <div>
                  <div style={{ fontSize: '0.72rem', fontWeight: 600, marginBottom: '0.2rem' }}>
                    🔐 Requerir Contraseñas Fuertes
                  </div>
                  <div style={{ fontSize: '0.64rem', color: 'var(--text-secondary)' }}>
                    Mínimo 8 caracteres con mayúsculas, minúsculas y números
                  </div>
                </div>
              </label>
            </div>

            {/* 2FA */}
            <div style={{ 
              padding: '0.8rem',
              background: 'rgba(255,255,255,0.03)',
              borderRadius: '6px',
              border: '1px solid var(--border-light)'
            }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={config.security.twoFactorAuth}
                  onChange={(e) => {
                    const newConfig = {
                      ...config,
                      security: { ...config.security, twoFactorAuth: e.target.checked }
                    };
                    saveConfig(newConfig);
                  }}
                  style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: 'var(--accent-brand)' }}
                />
                <div>
                  <div style={{ fontSize: '0.72rem', fontWeight: 600, marginBottom: '0.2rem' }}>
                    📱 Autenticación de Dos Factores (2FA)
                  </div>
                  <div style={{ fontSize: '0.64rem', color: 'var(--text-secondary)' }}>
                    Requerir código adicional al iniciar sesión (próximamente)
                  </div>
                </div>
              </label>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Sistema */}
      {activeTab === 'system' && (
        <div className="card">
          <h2 style={{ fontSize: '0.8rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            ⚙️ Configuración del Sistema
          </h2>
          
          <div style={{ display: 'grid', gap: '1rem' }}>
            {/* Metrics Retention */}
            <div>
              <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, marginBottom: '0.4rem' }}>
                💾 Retención de Métricas (días)
              </label>
              <p style={{ fontSize: '0.64rem', color: 'var(--text-secondary)', marginBottom: '0.6rem' }}>
                Días que se conservan las métricas antes de eliminarlas
              </p>
              <input
                type="number"
                min="7"
                max="365"
                value={config.system.metricsRetentionDays}
                onChange={(e) => {
                  const newConfig = {
                    ...config,
                    system: { ...config.system, metricsRetentionDays: parseInt(e.target.value) }
                  };
                  saveConfig(newConfig);
                }}
                style={{
                  padding: '0.4rem',
                  borderRadius: '6px',
                  border: '1px solid var(--border-light)',
                  background: 'var(--bg-surface)',
                  color: 'var(--text-primary)',
                  fontSize: '0.72rem',
                  width: '130px'
                }}
              />
              <span style={{ marginLeft: '0.4rem', fontSize: '0.64rem', color: 'var(--text-secondary)' }}>días</span>
            </div>

            {/* Aggregation Days */}
            <div>
              <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, marginBottom: '0.4rem' }}>
                📊 Agregación de Datos (días)
              </label>
              <p style={{ fontSize: '0.64rem', color: 'var(--text-secondary)', marginBottom: '0.6rem' }}>
                Después de estos días, las métricas se agregan por hora
              </p>
              <input
                type="number"
                min="1"
                max="30"
                value={config.system.aggregationDays}
                onChange={(e) => {
                  const newConfig = {
                    ...config,
                    system: { ...config.system, aggregationDays: parseInt(e.target.value) }
                  };
                  saveConfig(newConfig);
                }}
                style={{
                  padding: '0.5rem',
                  borderRadius: '8px',
                  border: '1px solid var(--border-light)',
                  background: 'var(--bg-surface)',
                  color: 'var(--text-primary)',
                  fontSize: '0.9rem',
                  width: '160px'
                }}
              />
              <span style={{ marginLeft: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>días</span>
            </div>

            {/* Cleanup Hour */}
            <div>
              <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, marginBottom: '0.4rem' }}>
                🕒 Hora de Limpieza Automática
              </label>
              <p style={{ fontSize: '0.64rem', color: 'var(--text-secondary)', marginBottom: '0.6rem' }}>
                Hora del día en que se ejecuta el mantenimiento de la base de datos
              </p>
              <input
                type="number"
                min="0"
                max="23"
                value={config.system.cleanupHour}
                onChange={(e) => {
                  const newConfig = {
                    ...config,
                    system: { ...config.system, cleanupHour: parseInt(e.target.value) }
                  };
                  saveConfig(newConfig);
                }}
                style={{
                  padding: '0.5rem',
                  borderRadius: '8px',
                  border: '1px solid var(--border-light)',
                  background: 'var(--bg-surface)',
                  color: 'var(--text-primary)',
                  fontSize: '0.9rem',
                  width: '160px'
                }}
              />
              <span style={{ marginLeft: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>:00 hrs</span>
            </div>

            {/* Max Hosts */}
            <div>
              <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, marginBottom: '0.4rem' }}>
                🖥️ Máximo de Hosts por Usuario
              </label>
              <p style={{ fontSize: '0.64rem', color: 'var(--text-secondary)', marginBottom: '0.6rem' }}>
                Número máximo de hosts que puede registrar cada usuario
              </p>
              <input
                type="number"
                min="1"
                max="1000"
                value={config.system.maxHostsPerUser}
                onChange={(e) => {
                  const newConfig = {
                    ...config,
                    system: { ...config.system, maxHostsPerUser: parseInt(e.target.value) }
                  };
                  saveConfig(newConfig);
                }}
                style={{
                  padding: '0.5rem',
                  borderRadius: '8px',
                  border: '1px solid var(--border-light)',
                  background: 'var(--bg-surface)',
                  color: 'var(--text-primary)',
                  fontSize: '0.9rem',
                  width: '160px'
                }}
              />
              <span style={{ marginLeft: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>hosts</span>
            </div>

            {/* Docker Support */}
            <div style={{ 
              padding: '0.8rem',
              background: 'rgba(255,255,255,0.03)',
              borderRadius: '6px',
              border: '1px solid var(--border-light)'
            }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={config.system.enableDocker}
                  onChange={(e) => {
                    const newConfig = {
                      ...config,
                      system: { ...config.system, enableDocker: e.target.checked }
                    };
                    saveConfig(newConfig);
                  }}
                  style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: 'var(--accent-brand)' }}
                />
                <div>
                  <div style={{ fontSize: '0.72rem', fontWeight: 600, marginBottom: '0.2rem' }}>
                    🐳 Habilitar Monitoreo Docker
                  </div>
                  <div style={{ fontSize: '0.64rem', color: 'var(--text-secondary)' }}>
                    Permitir que los agentes reporten información de contenedores Docker
                  </div>
                </div>
              </label>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Notificaciones */}
      {activeTab === 'notifications' && (
        <div className="card">
          <h2 style={{ fontSize: '0.8rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            🔔 Configuración de Notificaciones
          </h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '1.2rem', fontSize: '0.66rem' }}>
            Configuraciones globales para el sistema de notificaciones
          </p>
          
          <div style={{ display: 'grid', gap: '1rem' }}>
            {/* Email */}
            <div style={{ 
              padding: '0.8rem',
              background: 'rgba(255,255,255,0.03)',
              borderRadius: '6px',
              border: '1px solid var(--border-light)'
            }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={config.notifications.emailEnabled}
                  onChange={(e) => {
                    const newConfig = {
                      ...config,
                      notifications: { ...config.notifications, emailEnabled: e.target.checked }
                    };
                    saveConfig(newConfig);
                  }}
                  style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: 'var(--accent-brand)' }}
                />
                <div>
                  <div style={{ fontSize: '0.72rem', fontWeight: 600, marginBottom: '0.2rem' }}>
                    📧 Notificaciones por Email
                  </div>
                  <div style={{ fontSize: '0.64rem', color: 'var(--text-secondary)' }}>
                    Enviar alertas por correo electrónico (requiere configuración SMTP)
                  </div>
                </div>
              </label>
            </div>

            {/* Slack */}
            <div style={{ 
              padding: '0.8rem',
              background: 'rgba(255,255,255,0.03)',
              borderRadius: '6px',
              border: '1px solid var(--border-light)'
            }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={config.notifications.slackEnabled}
                  onChange={(e) => {
                    const newConfig = {
                      ...config,
                      notifications: { ...config.notifications, slackEnabled: e.target.checked }
                    };
                    saveConfig(newConfig);
                  }}
                  style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: 'var(--accent-brand)' }}
                />
                <div>
                  <div style={{ fontSize: '0.72rem', fontWeight: 600, marginBottom: '0.2rem' }}>
                    💬 Notificaciones por Slack
                  </div>
                  <div style={{ fontSize: '0.64rem', color: 'var(--text-secondary)' }}>
                    Enviar alertas a canales de Slack (requiere webhook URL)
                  </div>
                </div>
              </label>
            </div>

            {/* Discord */}
            <div style={{ 
              padding: '0.8rem',
              background: 'rgba(255,255,255,0.03)',
              borderRadius: '6px',
              border: '1px solid var(--border-light)'
            }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.8rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={config.notifications.discordEnabled}
                  onChange={(e) => {
                    const newConfig = {
                      ...config,
                      notifications: { ...config.notifications, discordEnabled: e.target.checked }
                    };
                    saveConfig(newConfig);
                  }}
                  style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: 'var(--accent-brand)' }}
                />
                <div>
                  <div style={{ fontSize: '0.72rem', fontWeight: 600, marginBottom: '0.2rem' }}>
                    🎮 Notificaciones por Discord
                  </div>
                  <div style={{ fontSize: '0.64rem', color: 'var(--text-secondary)' }}>
                    Enviar alertas a canales de Discord (requiere webhook URL)
                  </div>
                </div>
              </label>
            </div>

            {/* Default Severity */}
            <div>
              <label style={{ display: 'block', fontSize: '0.72rem', fontWeight: 600, marginBottom: '0.4rem' }}>
                ⚠️ Severidad por Defecto
              </label>
              <p style={{ fontSize: '0.64rem', color: 'var(--text-secondary)', marginBottom: '0.6rem' }}>
                Filtro de severidad por defecto para nuevas configuraciones
              </p>
              <select
                value={config.notifications.defaultSeverity}
                onChange={(e) => {
                  const newConfig = {
                    ...config,
                    notifications: { ...config.notifications, defaultSeverity: e.target.value }
                  };
                  saveConfig(newConfig);
                }}
                style={{
                  padding: '0.4rem',
                  borderRadius: '6px',
                  border: '1px solid var(--border-light)',
                  background: 'var(--bg-surface)',
                  color: 'var(--text-primary)',
                  fontSize: '0.72rem',
                  width: '180px',
                  cursor: 'pointer'
                }}
              >
                <option value="all">Todas las alertas</option>
                <option value="warning">Solo Warning y Critical</option>
                <option value="critical">Solo Critical</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Footer con información */}
      <div className="card" style={{ marginTop: '1.5rem', background: 'rgba(99, 102, 241, 0.1)', border: '1px solid rgba(99, 102, 241, 0.3)' }}>
        <div style={{ display: 'flex', gap: '0.8rem', alignItems: 'flex-start' }}>
          <span style={{ fontSize: '1.2rem' }}>ℹ️</span>
          <div>
            <h3 style={{ fontSize: '0.72rem', fontWeight: 600, marginBottom: '0.4rem' }}>
              💡 Información Importante
            </h3>
            <ul style={{ fontSize: '0.64rem', color: 'var(--text-secondary)', lineHeight: '1.5', paddingLeft: '1rem' }}>
              <li>Los cambios se guardan automáticamente en el navegador (localStorage)</li>
              <li>Las configuraciones de seguridad aplicarán en la próxima sesión</li>
              <li>Solo los administradores pueden acceder a esta página</li>
              <li>Para configuraciones avanzadas del servidor, edita las variables de entorno</li>
            </ul>
          </div>
        </div>
      </div>
        </div>
      </div>
    </div>
  );
}

// Helper functions para Settings
function getModuleIcon(module: string): string {
  const icons: Record<string, string> = {
    dashboard: '◈',
    hosts: '⬡',
    alerts: '⚡',
    docker: '🐳',
    rules: '⚙',
    notifications: '🔔',
    users: '👤'
  };
  return icons[module] || '📦';
}

function getModuleDescription(module: string): string {
  const descriptions: Record<string, string> = {
    dashboard: 'Vista principal con estadísticas y gráficos',
    hosts: 'Gestión de servidores monitoreados',
    alerts: 'Alertas activas y historial',
    docker: 'Monitoreo de contenedores Docker',
    rules: 'Reglas de alertas y umbrales',
    notifications: 'Configuración de notificaciones',
    users: 'Gestión de usuarios del sistema'
  };
  return descriptions[module] || 'Módulo del sistema';
}

/* ─── Root ──────────────────────────────────────────────────────── */
export default function Home() {
  const { user, logout, loading } = useAuth();
  const [page, setPage] = useState<Page>('dashboard');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const closeSidebar = () => {
    setIsSidebarOpen(false);
  };

  if (loading) return <div className="loading-msg full-screen">Iniciando LAMS…</div>;
  if (!user)   return <LoginScreen />;

  const pages: Record<Page, React.ReactNode> = {
    dashboard: <DashboardPage />,
    hosts:     <HostsPage />,
    alerts:    <AlertsPage />,
    docker:    <DockerPage />,
    rules:     <RulesPage />,
    notifications: <NotificationsPage />,
    users:     <UsersPage />,
    settings:  <SettingsPage />,
  };

  return (
    <div className="app-layout">
      {/* Hamburger menu button for mobile */}
      <button 
        className={`hamburger-btn ${isSidebarOpen ? 'open' : ''}`}
        onClick={toggleSidebar}
        aria-label="Toggle menu"
      >
        <div className="hamburger-icon">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </button>

      {/* Overlay para cerrar el sidebar al hacer click fuera (móvil) */}
      <div 
        className={`sidebar-overlay ${isSidebarOpen ? 'visible' : ''}`}
        onClick={closeSidebar}
      />

      <Sidebar 
        current={page} 
        setCurrent={setPage} 
        onLogout={logout}
        isOpen={isSidebarOpen}
        onClose={closeSidebar}
        userRole={user?.is_admin}
      />
      <main className="main-area">
        {pages[page]}
      </main>
    </div>
  );
}
