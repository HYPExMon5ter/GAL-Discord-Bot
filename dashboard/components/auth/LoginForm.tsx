'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle, Lock, Sparkles, Shield } from 'lucide-react';

export function LoginForm() {
  const [masterPassword, setMasterPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const { login } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (!masterPassword.trim()) {
      setError('Please enter the master password');
      setLoading(false);
      return;
    }

    try {
      const success = await login(masterPassword);
      
      if (success) {
        router.push('/dashboard');
      } else {
        setError('Invalid master password. Please check your credentials and try again.');
      }
    } catch (err) {
      setError('Unable to connect to the dashboard. Please try again or contact support.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-4">
      <Card className="w-full max-w-md border-slate-700 bg-card shadow-xl">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-4">
            <div className="p-4 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 shadow-lg">
              <Shield className="h-8 w-8 text-white" />
            </div>
          </div>
          <CardTitle className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent flex items-center justify-center gap-2">
            <span className="text-yellow-400">✨</span> GAL Live Graphics Dashboard
          </CardTitle>
          <CardDescription className="text-lg flex items-center justify-center gap-2">
            <span className="text-blue-500">🔐</span> Enter the master password to access the dashboard
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="masterPassword" className="flex items-center gap-2 text-blue-600 font-semibold">
                <span className="text-purple-500">🔑</span> Master Password
              </Label>
              <Input
                id="masterPassword"
                type="password"
                placeholder="🔒 Enter the master password"
                value={masterPassword}
                onChange={(e) => setMasterPassword(e.target.value)}
                required
                disabled={loading}
                className="border-blue-200 focus:border-blue-400 focus:ring-blue-200"
              />
            </div>
            
            {error && (
              <div className="flex items-center gap-2 p-3 rounded-md bg-gradient-to-r from-red-50 to-orange-50 border border-red-200 text-red-700">
                <AlertCircle className="h-5 w-5 text-red-600" />
                <span className="text-sm flex items-center gap-1">
                  <span className="text-red-500">⚠️</span> {error}
                </span>
              </div>
            )}
            
            <Button
              type="submit"
              className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 shadow-lg hover:shadow-xl transition-all duration-200 text-white font-semibold"
              disabled={loading}
            >
              <span className="flex items-center gap-2">
                {loading ? (
                  <>
                    <span className="animate-spin">⏳</span> Authenticating...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    Access Dashboard <span className="text-yellow-300">🚀</span>
                  </>
                )}
              </span>
            </Button>
          </form>
          
          <div className="mt-6 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
            <span className="text-blue-500">🛡️</span> Guardian Angel League - Live Graphics Dashboard v2.0
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
