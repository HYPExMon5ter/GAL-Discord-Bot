'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle, Lock } from 'lucide-react';

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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-4">
            <div className="p-3 rounded-full bg-primary/10">
              <Lock className="h-6 w-6 text-primary" />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold">
            GAL Live Graphics Dashboard
          </CardTitle>
          <CardDescription>
            Enter the master password to access the dashboard
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="masterPassword">Master Password</Label>
              <Input
                id="masterPassword"
                type="password"
                placeholder="Enter the master password"
                value={masterPassword}
                onChange={(e) => setMasterPassword(e.target.value)}
                required
                disabled={loading}
              />
            </div>
            
            {error && (
              <div className="flex items-center gap-2 p-3 rounded-md bg-destructive/10 text-destructive">
                <AlertCircle className="h-4 w-4" />
                <span className="text-sm">{error}</span>
              </div>
            )}
            
            <Button
              type="submit"
              className="w-full"
              disabled={loading}
            >
              {loading ? 'Authenticating...' : 'Access Dashboard'}
            </Button>
          </form>
          
          <div className="mt-6 text-center text-xs text-muted-foreground">
            Guardian Angel League - Live Graphics Dashboard v2.0
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
