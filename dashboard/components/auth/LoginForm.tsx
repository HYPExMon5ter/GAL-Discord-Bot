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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gal-deep-bg via-gal-card to-gal-deep-bg p-4">
      <div className="absolute inset-0 bg-gradient-to-br from-gal-purple/10 via-transparent to-gal-cyan/10"></div>
      <Card className="w-full max-w-md border-border/20 bg-card/80 backdrop-blur supports-[backdrop-filter]:bg-card/60 gal-card relative z-10">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-4">
            <div className="w-20 h-20 gal-gradient-primary rounded-2xl flex items-center justify-center text-white font-bold text-2xl gal-glow-primary">
              GAL
            </div>
          </div>
          <CardTitle className="text-3xl font-bold gal-gradient-text flex items-center justify-center gap-2">
            <span className="text-yellow-300">✨</span> Live Graphics Dashboard
          </CardTitle>
          <CardDescription className="text-lg flex items-center justify-center gap-2 text-muted-foreground">
            <span className="text-gal-cyan">🔐</span> Enter the master password to access the dashboard
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="masterPassword" className="flex items-center gap-2 text-gal-purple font-semibold">
                <span className="text-gal-cyan">🔑</span> Master Password
              </Label>
              <Input
                id="masterPassword"
                type="password"
                placeholder="🔒 Enter the master password"
                value={masterPassword}
                onChange={(e) => setMasterPassword(e.target.value)}
                required
                disabled={loading}
                className="border-border/30 focus:border-primary focus:ring-primary/20 bg-background"
              />
            </div>
            
            {error && (
              <div className="flex items-center gap-2 p-3 rounded-xl bg-gradient-to-r from-red-500/10 to-orange-500/10 border border-red-500/30 text-red-300">
                <AlertCircle className="h-5 w-5 text-red-400" />
                <span className="text-sm flex items-center gap-1">
                  <span className="text-red-400">⚠️</span> {error}
                </span>
              </div>
            )}
            
            <Button
              type="submit"
              className="w-full gal-button-primary text-white font-semibold transition-all duration-300"
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
            <span className="text-gal-cyan">🛡️</span> Guardian Angel League - Live Graphics Dashboard v2.0
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
