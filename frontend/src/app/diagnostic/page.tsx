'use client';

import { useState } from 'react';

export default function DiagnosticPage() {
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const addResult = (name: string, success: boolean, data: any) => {
    setResults(prev => [...prev, { name, success, data, timestamp: new Date().toISOString() }]);
  };

  const runDiagnostics = async () => {
    setResults([]);
    setLoading(true);

    // Test 1: Health endpoint
    try {
      const res = await fetch(`${API_URL}/health`);
      const data = await res.json();
      addResult('Health Check', res.ok, { status: res.status, data });
    } catch (error) {
      addResult('Health Check', false, { error: String(error) });
    }

    // Test 2: API root
    try {
      const res = await fetch(`${API_URL}/`);
      const data = await res.json();
      addResult('API Root', res.ok, { status: res.status, data });
    } catch (error) {
      addResult('API Root', false, { error: String(error) });
    }

    // Test 3: Login con credenciales correctas
    try {
      const form = new URLSearchParams({
        username: 'admin@lams.io',
        password: 'lams2024'
      });
      
      const res = await fetch(`${API_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form,
      });
      
      const data = await res.json();
      addResult('Login (admin@lams.io / lams2024)', res.ok, { 
        status: res.status, 
        data: res.ok ? { token_received: true, token_length: data.access_token?.length } : data 
      });
    } catch (error) {
      addResult('Login', false, { error: String(error) });
    }

    // Test 4: Login con credenciales incorrectas
    try {
      const form = new URLSearchParams({
        username: 'admin@lams.io',
        password: 'wrong_password'
      });
      
      const res = await fetch(`${API_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form,
      });
      
      const data = await res.json();
      addResult('Login (credenciales incorrectas)', !res.ok, { 
        status: res.status, 
        data,
        expectation: 'Debería fallar con 400'
      });
    } catch (error) {
      addResult('Login (credenciales incorrectas)', false, { error: String(error) });
    }

    setLoading(false);
  };

  return (
    <div style={{ 
      padding: '40px',
      maxWidth: '1200px',
      margin: '0 auto',
      fontFamily: 'monospace',
      background: '#0f0f23',
      minHeight: '100vh',
      color: '#cccccc'
    }}>
      <h1 style={{ color: '#4ade80', marginBottom: '10px' }}>🔧 Diagnóstico de Conectividad LAMS</h1>
      <p style={{ marginBottom: '30px', color: '#888' }}>
        Esta página realiza pruebas de conectividad con el backend
      </p>

      <div style={{ 
        background: '#1a1a2e',
        padding: '20px',
        borderRadius: '8px',
        marginBottom: '20px',
        border: '1px solid #2a2a4e'
      }}>
        <h2 style={{ color: '#4ade80', marginBottom: '15px' }}>Configuración</h2>
        <div><strong>API URL:</strong> {API_URL}</div>
        <div><strong>Credenciales:</strong> admin@lams.io / lams2024</div>
      </div>

      <button
        onClick={runDiagnostics}
        disabled={loading}
        style={{
          padding: '15px 30px',
          background: '#4ade80',
          color: '#000',
          border: 'none',
          borderRadius: '8px',
          cursor: loading ? 'not-allowed' : 'pointer',
          fontWeight: 'bold',
          fontSize: '16px',
          marginBottom: '30px'
        }}
      >
        {loading ? '⏳ Ejecutando pruebas...' : '▶️ Ejecutar Diagnóstico'}
      </button>

      {results.length > 0 && (
        <div>
          <h2 style={{ color: '#4ade80', marginBottom: '20px' }}>Resultados</h2>
          {results.map((result, idx) => (
            <div
              key={idx}
              style={{
                background: result.success ? '#16213e' : '#2e1616',
                padding: '15px',
                borderRadius: '8px',
                marginBottom: '15px',
                border: `1px solid ${result.success ? '#0f3460' : '#5a1616'}`
              }}
            >
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                marginBottom: '10px',
                fontSize: '16px'
              }}>
                <span style={{ marginRight: '10px', fontSize: '20px' }}>
                  {result.success ? '✅' : '❌'}
                </span>
                <strong>{result.name}</strong>
              </div>
              <pre style={{ 
                background: '#0a0a15',
                padding: '10px',
                borderRadius: '4px',
                overflow: 'auto',
                fontSize: '12px',
                lineHeight: '1.5'
              }}>
                {JSON.stringify(result.data, null, 2)}
              </pre>
              <div style={{ fontSize: '11px', color: '#666', marginTop: '5px' }}>
                {new Date(result.timestamp).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ marginTop: '40px', padding: '15px', background: '#1a1a2e', borderRadius: '8px' }}>
        <h3 style={{ color: '#4ade80', marginBottom: '10px' }}>💡 Guía de Resolución</h3>
        <ul style={{ lineHeight: '1.8' }}>
          <li>Si <strong>Health Check</strong> falla: El servidor no está respondiendo</li>
          <li>Si <strong>Login correcto</strong> falla: Problema con autenticación del backend</li>
          <li>Si <strong>Login incorrecto</strong> retorna 200 OK: El backend no valida contraseñas</li>
          <li>Si todos fallan: Verifica la URL del API en .env.local</li>
        </ul>
      </div>

      <div style={{ marginTop: '20px', textAlign: 'center' }}>
        <a href="/" style={{ color: '#4ade80', textDecoration: 'none' }}>
          ← Volver al Dashboard
        </a>
      </div>
    </div>
  );
}
