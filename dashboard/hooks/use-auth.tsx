'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { isAxiosError } from 'axios';
import { authApi } from '@/lib/api';

interface AuthContextType {
  isAuthenticated: boolean;
  login: (masterPassword: string) => Promise<boolean>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    
    if (token) {
      setIsAuthenticated(true);
    }
    
    setLoading(false);
  }, []);

  const login = async (masterPassword: string): Promise<boolean> => {
    try {
      const response = await authApi.login({ master_password: masterPassword });
      
      localStorage.setItem('auth_token', response.access_token);
      localStorage.setItem('expires_at', new Date(Date.now() + response.expires_in * 1000).toISOString());
      
      setIsAuthenticated(true);
      
      return true;
    } catch (error) {
      if (isAxiosError(error) && error.response?.status === 401) {
        return false;
      }

      throw error;
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
