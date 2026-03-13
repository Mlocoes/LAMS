'use client';

import { useState } from 'react';
import styles from './DeleteContainer.module.css';

interface DeleteContainerProps {
  hostId: string;
  containerId: string;
  containerName: string;
  containerStatus: string;
  onClose: () => void;
  onSuccess: () => void;
}

export function DeleteContainer({
  hostId,
  containerId,
  containerName,
  containerStatus,
  onClose,
  onSuccess
}: DeleteContainerProps) {
  const [force, setForce] = useState(false);
  const [removeVolumes, setRemoveVolumes] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isRunning = containerStatus === 'running';

  async function handleDelete() {
    if (!force && isRunning) {
      setError('Container is running. Enable "Force delete" to remove it.');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
      const params = new URLSearchParams();
      if (force) params.append('force', 'true');
      if (removeVolumes) params.append('volumes', 'true');

      const response = await fetch(
        `${apiUrl}/api/v1/containers/${hostId}/containers/${containerId}?${params.toString()}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Failed to delete container: ${response.statusText}`);
      }

      onSuccess();
      onClose();
    } catch (err) {
      console.error('Error deleting container:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete container');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.modal}>
      <div className={styles.deleteContainer}>
        <div className={styles.header}>
          <h2>🗑️ Delete Container</h2>
          <button className={styles.closeBtn} onClick={onClose} disabled={loading}>
            ✖
          </button>
        </div>

        <div className={styles.content}>
          <div className={styles.warning}>
            {isRunning && (
              <div className={styles.runningWarning}>
                ⚠️ <strong>Warning:</strong> This container is currently running!
              </div>
            )}
            
            <p className={styles.confirmText}>
              Are you sure you want to delete the container <strong>{containerName}</strong>?
            </p>
            <p className={styles.idText}>
              ID: <code>{containerId.substring(0, 12)}</code>
            </p>
          </div>

          <div className={styles.options}>
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={force}
                onChange={(e) => setForce(e.target.checked)}
                disabled={loading}
              />
              <span>
                <strong>Force delete</strong>
                <span className={styles.hint}>Kill running container before deletion</span>
              </span>
            </label>

            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={removeVolumes}
                onChange={(e) => setRemoveVolumes(e.target.checked)}
                disabled={loading}
              />
              <span>
                <strong>Remove volumes</strong>
                <span className={styles.hint}>Delete associated anonymous volumes</span>
              </span>
            </label>
          </div>

          {error && (
            <div className={styles.errorMessage}>
              ❌ {error}
            </div>
          )}

          <div className={styles.dangerZone}>
            <span className={styles.dangerIcon}>⚠️</span>
            <div className={styles.dangerText}>
              <strong>This action cannot be undone.</strong>
              <br />
              The container will be permanently removed from the host.
            </div>
          </div>
        </div>

        <div className={styles.footer}>
          <button
            onClick={onClose}
            className={styles.cancelBtn}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            onClick={handleDelete}
            className={styles.deleteBtn}
            disabled={loading || (!force && isRunning)}
          >
            {loading ? (
              <>
                <div className={styles.spinner}></div>
                Deleting...
              </>
            ) : (
              <>
                🗑️ Delete Container
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
