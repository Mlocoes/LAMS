'use client';

import { useEffect, useState } from 'react';
import styles from './ContainerInspect.module.css';

interface ContainerInspectProps {
  hostId: string;
  containerId: string;
  containerName: string;
  onClose: () => void;
}

export function ContainerInspect({
  hostId,
  containerId,
  containerName,
  onClose
}: ContainerInspectProps) {
  const [inspectData, setInspectData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['State', 'Config', 'NetworkSettings']));

  useEffect(() => {
    loadInspect();
  }, [hostId, containerId]);

  async function loadInspect() {
    try {
      setLoading(true);
      setError(null);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      const response = await fetch(
        `${apiUrl}/api/v1/containers/${hostId}/containers/${containerId}/inspect`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch inspect data: ${response.statusText}`);
      }

      const data = await response.json();
      setInspectData(data.inspect_data || {});
    } catch (err) {
      console.error('Error loading inspect:', err);
      setError(err instanceof Error ? err.message : 'Failed to load inspect data');
    } finally {
      setLoading(false);
    }
  }

  function downloadInspect() {
    const blob = new Blob([JSON.stringify(inspectData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${containerName}-inspect-${new Date().toISOString()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function copyToClipboard() {
    navigator.clipboard.writeText(JSON.stringify(inspectData, null, 2));
    alert('Inspect data copied to clipboard!');
  }

  function toggleSection(section: string) {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  }

  function renderValue(value: any, depth: number = 0): JSX.Element {
    if (value === null) return <span className={styles.null}>null</span>;
    if (value === undefined) return <span className={styles.undefined}>undefined</span>;
    if (typeof value === 'boolean') return <span className={styles.boolean}>{value.toString()}</span>;
    if (typeof value === 'number') return <span className={styles.number}>{value}</span>;
    if (typeof value === 'string') return <span className={styles.string}>"{value}"</span>;

    if (Array.isArray(value)) {
      if (value.length === 0) return <span className={styles.array}>[]</span>;
      return (
        <span className={styles.array}>
          [{value.map((item, index) => (
            <span key={index}>
              {index > 0 && ', '}
              {renderValue(item, depth + 1)}
            </span>
          ))}]
        </span>
      );
    }

    if (typeof value === 'object') {
      return <span className={styles.object}>{`{${Object.keys(value).length} keys}`}</span>;
    }

    return <span>{String(value)}</span>;
  }

  const filteredData = searchTerm && inspectData
    ? JSON.stringify(inspectData, null, 2).toLowerCase().includes(searchTerm.toLowerCase())
      ? inspectData
      : {}
    : inspectData;

  return (
    <div className={styles.modal}>
      <div className={styles.inspectContainer}>
        <div className={styles.header}>
          <h2>🔍 Inspect: {containerName}</h2>
          <button className={styles.closeBtn} onClick={onClose}>
            ✖
          </button>
        </div>

        <div className={styles.controls}>
          <input
            type="text"
            placeholder="Search in JSON..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className={styles.searchInput}
          />

          <div className={styles.actions}>
            <button onClick={loadInspect} className={styles.iconBtn} title="Refresh">
              🔄
            </button>
            <button onClick={copyToClipboard} className={styles.iconBtn} title="Copy">
              📋
            </button>
            <button onClick={downloadInspect} className={styles.iconBtn} title="Download">
              💾
            </button>
          </div>
        </div>

        <div className={styles.inspectContent}>
          {loading && (
            <div className={styles.loadingState}>
              <div className={styles.spinner}></div>
              <p>Loading inspect data...</p>
            </div>
          )}

          {error && (
            <div className={styles.errorState}>
              <p>❌ {error}</p>
              <button onClick={loadInspect} className={styles.retryBtn}>
                Retry
              </button>
            </div>
          )}

          {!loading && !error && filteredData && (
            <div className={styles.jsonTree}>
              {Object.entries(filteredData).map(([key, value]) => (
                <div key={key} className={styles.jsonSection}>
                  <div
                    className={styles.jsonKey}
                    onClick={() => toggleSection(key)}
                  >
                    <span className={styles.expander}>
                      {expandedSections.has(key) ? '▼' : '▶'}
                    </span>
                    <span className={styles.keyName}>{key}</span>
                    {!expandedSections.has(key) && (
                      <span className={styles.collapsed}>
                        {renderValue(value)}
                      </span>
                    )}
                  </div>

                  {expandedSections.has(key) && (
                    <div className={styles.jsonValue}>
                      <pre>{JSON.stringify(value, null, 2)}</pre>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className={styles.footer}>
          <span>Container ID: {containerId.substring(0, 12)}</span>
          <span>Host: {hostId}</span>
        </div>
      </div>
    </div>
  );
}
