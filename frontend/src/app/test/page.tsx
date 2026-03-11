'use client';

import { useState } from 'react';

export default function TestPage() {
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);

  const testLogin = async () => {
    setLoading(true);
    setResult('Probando login...\n');

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      setResult(prev => prev + `API URL: ${apiUrl}\n\n`);

      const form = new URLSearchParams({ 
        username: 'admin@lams.io', 
        password: 'lams2024' 
      });

      setResult(prev => prev + 'Enviando request a /auth/login...\n');

      const res = await fetch(`${apiUrl}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form,
      });

      setResult(prev => prev + `Status: ${res.status} ${res.statusText}\n`);

      if (!res.ok) {
        const text = await res.text();
        setResult(prev => prev + `Error body: ${text}\n`);
        throw new Error(`Login failed: ${res.statusText}`);
      }

      const data = await res.json();
      setResult(prev => prev + '✅ LOGIN EXITOSO!\n');
      setResult(prev => prev + `Token: ${data.access_token.substring(0, 50)}...\n\n`);

      // Test /me endpoint
      setResult(prev=> prev + 'Probando /auth/me...\n');
      const meRes = await fetch(`${apiUrl}/api/v1/auth/me`, {
        headers: { 'Authorization': `Bearer ${data.access_token}` }
      });

      setResult(prev => prev + `Status: ${meRes.status} ${meRes.statusText}\n`);

      if (meRes.ok) {
        const meData = await meRes.json();
        setResult(prev => prev + '✅ /me EXITOSO!\n');
        setResult(prev => prev + `Usuario: ${meData.email} (${meData.is_admin ? 'Admin' : 'User'})\n`);
      } else {
        const text = await meRes.text();
        setResult(prev => prev + `Error: ${text}\n`);
      }

    } catch (err: any) {
      setResult(prev => prev + `\n❌ ERROR: ${err.message}\n`);
      setResult(prev => prev + `Stack: ${err.stack}\n`);
    } finally {
      setLoading(false);
    }
  };

  const testCORS = async () => {
    setLoading(true);
    setResult('Probando CORS...\n');

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      setResult(prev => prev + `API URL: ${apiUrl}\n\n`);

      const res = await fetch(`${apiUrl}/`, {
        method: 'GET',
      });

      setResult(prev => prev + `Status: ${res.status}\n`);
      const data = await res.json();
      setResult(prev => prev + `Response: ${JSON.stringify(data)}\n`);
      setResult(prev => prev + '✅ CORS funciona correctamente\n');

    } catch (err: any) {
      setResult(prev => prev + `\n❌ ERROR CORS: ${err.message}\n`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <h1>LAMS - Página de Diagnóstico</h1>
      
      <div style={{ marginBottom: '2rem' }}>
        <h2>Información del Sistema</h2>
        <p>API URL configurada: {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}</p>
        <p>Window location: {typeof window !== 'undefined' ? window.location.href : 'N/A'}</p>
      </div>

      <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
        <button 
          onClick={testCORS}
          disabled={loading}
          style={{ 
            padding: '0.75rem 1.5rem', 
            background: '#6366f1', 
            color: 'white', 
            border: 'none', 
            borderRadius: '6px',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          {loading ? 'Probando...' : 'Test CORS'}
        </button>

        <button 
          onClick={testLogin}
          disabled={loading}
          style={{ 
            padding: '0.75rem 1.5rem', 
            background: '#10b981', 
            color: 'white', 
            border: 'none', 
            borderRadius: '6px',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          {loading ? 'Probando...' : 'Test Login'}
        </button>
      </div>

      <pre style={{ 
        background: '#1e2235', 
        padding: '1rem', 
        borderRadius: '8px', 
        whiteSpace: 'pre-wrap',
        minHeight: '200px',
        color: '#e2e8f0' 
      }}>
        {result || 'Haz clic en un botón para ejecutar pruebas...'}
      </pre>
    </div>
  );
}
