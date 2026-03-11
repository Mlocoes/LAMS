'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { login as apiLogin, getMe } from '@/lib/api';

interface AuthUser {
  id: number;
  email: string;
  is_admin: boolean;
}

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Validar token al montar (reload/refresh)
    const validateAuth = async () => {
      const stored = localStorage.getItem('lams_token');
      
      // Si no hay token, ir directo al login sin mostrar "cargando"
      if (!stored) {
        setLoading(false);
        return;
      }

      // Si hay token, validarlo inmediatamente con el backend
      // Timeout de seguridad: 5 segundos máximo para validación
      const timeoutId = setTimeout(() => {
        console.warn('⏱️ Timeout de validación alcanzado. Redirigiendo al login...');
        localStorage.removeItem('lams_token');
        setToken(null);
        setUser(null);
        setLoading(false);
      }, 5000);

      try {
        setToken(stored);
        const userData = await getMe();
        clearTimeout(timeoutId);
        setUser(userData);
      } catch (error) {
        // Token inválido o expirado - limpiar y forzar login
        clearTimeout(timeoutId);
        console.warn('🔒 Token inválido o sesión expirada. Redirigiendo al login...');
        localStorage.removeItem('lams_token');
        setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    validateAuth();
  }, []);

  const login = async (email: string, password: string) => {
    const data = await apiLogin(email, password);
    localStorage.setItem('lams_token', data.access_token);
    setToken(data.access_token);
    const me = await getMe();
    setUser(me);
  };

  const logout = () => {
    localStorage.removeItem('lams_token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
