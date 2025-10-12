'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { authApi } from '@/lib/api';

interface AuthContextType {
  isAuthenticated: boolean;
  username: string | null;
  login: (masterPassword: string) => Promise<boolean>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    
    if (token) {
      setIsAuthenticated(true);
      setUsername('Dashboard User');
    }
    
    setLoading(false);
  }, []);

  const login = async (masterPassword: string): Promise<boolean> => {
    try {
      const response = await authApi.login({ master_password: masterPassword });
      
      localStorage.setItem('auth_token', response.access_token);
      localStorage.setItem('expires_at', new Date(Date.now() + response.expires_in * 1000).toISOString());
      
      setIsAuthenticated(true);
      setUsername('Dashboard User');
      
      return true;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('expires_at');
      
      setIsAuthenticated(false);
      setUsername(null);
      
      router.push('/login');
    }
  };

  // Check token expiration
  useEffect(() => {
    if (!isAuthenticated) return;

    const checkExpiration = () => {
      const expiresAt = localStorage.getItem('expires_at');
      if (expiresAt) {
        const expirationTime = new Date(expiresAt).getTime();
        const now = new Date().getTime();
        
        if (now >= expirationTime) {
          logout();
        }
      }
    };

    const interval = setInterval(checkExpiration, 60000); // Check every minute

    return () => clearInterval(interval);
  }, [isAuthenticated]);

  const value: AuthContextType = {
    isAuthenticated,
    username,
    login,
    logout,
    loading,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
