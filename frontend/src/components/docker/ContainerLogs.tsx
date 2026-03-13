'use client';

import { useEffect, useState, useRef } from 'react';
import styles from './ContainerLogs.module.css';

interface ContainerLogsProps {
  hostId: string;
  containerId: string;
  containerName: string;
  onClose: () => void;
}

export function ContainerLogs({
  hostId,
  containerId,
  containerName,
  onClose
}: ContainerLogsProps) {
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const logsEndRef = useRef<HTMLDivElement>(null);
  const logsContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadLogs();
  }, [hostId, containerId]);

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  async function loadLogs() {
    try {
      setLoading(true);
      setError(null);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      const response = await fetch(
        `${apiUrl}/api/v1/containers/${hostId}/containers/${containerId}/logs?tail=1000`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch logs: ${response.statusText}`);
      }

      const data = await response.json();
      setLogs(data.logs || []);
    } catch (err) {
      console.error('Error loading logs:', err);
      setError(err instanceof Error ? err.message : 'Failed to load logs');
    } finally {
      setLoading(false);
    }
  }

  function downloadLogs() {
    const blob = new Blob([logs.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${containerName}-logs-${new Date().toISOString()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function clearLogs() {
    setLogs([]);
  }

  function copyToClipboard() {
    navigator.clipboard.writeText(logs.join('\n'));
    alert('Logs copied to clipboard!');
  }

  const filteredLogs = searchTerm
    ? logs.filter(line => line.toLowerCase().includes(searchTerm.toLowerCase()))
    : logs;

  return (
    <div className={styles.modal}>
      <div className={styles.logsContainer}>
        <div className={styles.header}>
          <h2>📄 Logs: {containerName}</h2>
          <button className={styles.closeBtn} onClick={onClose}>
            ✖
          </button>
        </div>

        <div className={styles.controls}>
          <div className={styles.leftControls}>
            <input
              type="text"
              placeholder="Search logs..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className={styles.searchInput}
            />
            <span className={styles.logCount}>
              {filteredLogs.length} / {logs.length} lines
            </span>
          </div>

          <div className={styles.rightControls}>
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
              />
              Auto-scroll
            </label>
            <button onClick={loadLogs} className={styles.iconBtn} title="Refresh">
              🔄
            </button>
            <button onClick={copyToClipboard} className={styles.iconBtn} title="Copy">
              📋
            </button>
            <button onClick={clearLogs} className={styles.iconBtn} title="Clear">
              🗑️
            </button>
            <button onClick={downloadLogs} className={styles.iconBtn} title="Download">
              💾
            </button>
          </div>
        </div>

        <div className={styles.logsContent} ref={logsContainerRef}>
          {loading && (
            <div className={styles.loadingState}>
              <div className={styles.spinner}></div>
              <p>Loading logs...</p>
            </div>
          )}

          {error && (
            <div className={styles.errorState}>
              <p>❌ {error}</p>
              <button onClick={loadLogs} className={styles.retryBtn}>
                Retry
              </button>
            </div>
          )}

          {!loading && !error && filteredLogs.length === 0 && (
            <div className={styles.emptyState}>
              <p>No logs found</p>
            </div>
          )}

          {!loading && !error && filteredLogs.map((line, index) => (
            <div key={index} className={styles.logLine}>
              <span className={styles.lineNumber}>{index + 1}</span>
              <span className={styles.lineContent}>{line}</span>
            </div>
          ))}
          
          <div ref={logsEndRef} />
        </div>

        <div className={styles.footer}>
          <span>Container ID: {containerId.substring(0, 12)}</span>
          <span>Host: {hostId}</span>
        </div>
      </div>
    </div>
  );
}
