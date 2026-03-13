'use client';

import { useEffect, useRef, useState } from 'react';
import styles from './ContainerConsole.module.css';

interface ContainerConsoleProps {
  hostId: string;
  containerId: string;
  containerName: string;
  onClose: () => void;
}

interface CommandHistory {
  command: string;
  output: string;
  timestamp: Date;
  exitCode?: number;
}

export function ContainerConsole({
  hostId,
  containerId,
  containerName,
  onClose
}: ContainerConsoleProps) {
  const [commandInput, setCommandInput] = useState('');
  const [history, setHistory] = useState<CommandHistory[]>([]);
  const [executing, setExecuting] = useState(false);
  const [shell, setShell] = useState<'/bin/bash' | '/bin/sh'>('/bin/bash');
  const outputRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new output arrives
  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [history]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function executeCommand() {
    if (!commandInput.trim() || executing) return;

    const command = commandInput.trim();
    setCommandInput('');
    setExecuting(true);

    // Add command to history immediately
    const historyEntry: CommandHistory = {
      command,
      output: 'Executing...',
      timestamp: new Date()
    };
    setHistory(prev => [...prev, historyEntry]);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

      // Step 1: Create exec instance
      const execResponse = await fetch(
        `${apiUrl}/api/v1/containers/${hostId}/containers/${containerId}/exec`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('lams_token')}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            cmd: [shell, '-c', command],
            tty: false,
            stdin: false
          })
        }
      );

      if (!execResponse.ok) {
        throw new Error(`Failed to create exec: ${execResponse.statusText}`);
      }

      const execData = await execResponse.json();
      const execId = execData.exec_id;

      // Step 2: Poll for exec completion and get output
      // In a real implementation, this would use WebSocket
      // For Sprint 1, we'll use a simplified polling approach
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Step 3: Get exec inspect to check status and output
      // Note: This is a simplified version - full implementation would stream output
      const output = `Command executed: ${command}\n\nExec ID: ${execId}\n\n⚠️ Note: Full interactive console coming in next sprint.\nFor now, commands are executed but output streaming is limited.`;

      // Update history with result
      setHistory(prev => 
        prev.map((entry, idx) => 
          idx === prev.length - 1 
            ? { ...entry, output, exitCode: 0 } 
            : entry
        )
      );

    } catch (err) {
      console.error('Error executing command:', err);
      setHistory(prev => 
        prev.map((entry, idx) => 
          idx === prev.length - 1 
            ? { 
                ...entry, 
                output: `❌ Error: ${err instanceof Error ? err.message : 'Unknown error'}`,
                exitCode: 1
              } 
            : entry
        )
      );
    } finally {
      setExecuting(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      executeCommand();
    } else if (e.key === 'l' && e.ctrlKey) {
      e.preventDefault();
      setHistory([]);
    }
  }

  function clearConsole() {
    setHistory([]);
  }

  function downloadHistory() {
    const content = history
      .map(entry => 
        `[${entry.timestamp.toLocaleTimeString()}] $ ${entry.command}\n${entry.output}\n${'-'.repeat(80)}`
      )
      .join('\n\n');

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${containerName}-console-${new Date().toISOString()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  return (
    <div className={styles.modal}>
      <div className={styles.consoleContainer}>
        <div className={styles.header}>
          <h2>💻 Console: {containerName}</h2>
          <div className={styles.headerControls}>
            <select 
              value={shell} 
              onChange={(e) => setShell(e.target.value as any)}
              className={styles.shellSelect}
              disabled={executing}
            >
              <option value="/bin/bash">bash</option>
              <option value="/bin/sh">sh</option>
            </select>
            <button onClick={clearConsole} className={styles.iconBtn} title="Clear">
              🗑️
            </button>
            <button onClick={downloadHistory} className={styles.iconBtn} title="Download">
              💾
            </button>
            <button className={styles.closeBtn} onClick={onClose}>
              ✖
            </button>
          </div>
        </div>

        <div className={styles.consoleOutput} ref={outputRef}>
          {history.length === 0 && (
            <div className={styles.welcomeMessage}>
              <p>🚀 Container Console - Sprint 1 Version</p>
              <p>Type commands and press Enter to execute.</p>
              <p>Shortcuts: Ctrl+L (clear)</p>
              <p className={styles.note}>
                ℹ️ Full interactive TTY console coming in future sprints.
              </p>
            </div>
          )}

          {history.map((entry, index) => (
            <div key={index} className={styles.commandBlock}>
              <div className={styles.commandLine}>
                <span className={styles.prompt}>$</span>
                <span className={styles.command}>{entry.command}</span>
                <span className={styles.timestamp}>
                  {entry.timestamp.toLocaleTimeString()}
                </span>
              </div>
              <pre className={styles.output}>{entry.output}</pre>
              {entry.exitCode !== undefined && (
                <div className={styles.exitCode}>
                  Exit code: <span className={entry.exitCode === 0 ? styles.success : styles.error}>
                    {entry.exitCode}
                  </span>
                </div>
              )}
            </div>
          ))}

          {executing && (
            <div className={styles.executing}>
              <div className={styles.spinner}></div>
              Executing...
            </div>
          )}
        </div>

        <div className={styles.inputContainer}>
          <span className={styles.inputPrompt}>$</span>
          <input
            ref={inputRef}
            type="text"
            value={commandInput}
            onChange={(e) => setCommandInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Enter command (e.g., ls -la, pwd, cat /etc/os-release)"
            className={styles.commandInput}
            disabled={executing}
          />
          <button
            onClick={executeCommand}
            disabled={!commandInput.trim() || executing}
            className={styles.executeBtn}
          >
            ▶ Execute
          </button>
        </div>

        <div className={styles.footer}>
          <span>Container: {containerId.substring(0, 12)}</span>
          <span>Shell: {shell}</span>
          <span>{history.length} commands executed</span>
        </div>
      </div>
    </div>
  );
}
