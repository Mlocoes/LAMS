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
    const stored = localStorage.getItem('lams_token');
    if (stored) {
      setToken(stored);
      getMe()
        .then(setUser)
        .catch(() => {
          localStorage.removeItem('lams_token');
          setToken(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
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
