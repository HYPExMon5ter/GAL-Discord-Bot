'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertCircle, Lock, Shield } from 'lucide-react';

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
    <div className="min-h-screen flex items-center justify-center bg-gal-deep-bg p-4 xs:p-6">
      
      <Card className="w-full max-w-md border-border/20 bg-card/80 backdrop-blur supports-[backdrop-filter]:bg-card/60 gal-card relative z-10">
        <CardHeader className="space-y-4 text-center">
          <div className="flex justify-center mb-4">
            <img 
              src="/assets/GA_Logo_Transparent_Background_White_Text.png" 
              alt="Guardian Angel League Logo" 
              className="w-24 h-24 sm:w-32 sm:h-32 rounded-xl gal-glow-primary object-cover"
            />
          </div>
          <CardTitle className="text-2xl sm:text-4xl font-abrau font-bold text-gal-text-primary">
            GUARDIAN ANGEL LEAGUE
          </CardTitle>
          <CardDescription className="text-lg sm:text-xl font-montserrat text-gal-text-secondary">
            Live Graphics Dashboard
          </CardDescription>
          <CardDescription className="text-sm sm:text-base font-montserrat text-muted-foreground">
            Enter the master password to access the dashboard
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-3">
              <Label htmlFor="masterPassword" className="flex items-center gap-2 text-gal-cyan font-semibold font-montserrat text-base">
                <Shield className="h-5 w-5" />
                Master Password
              </Label>
              <Input
                id="masterPassword"
                type="password"
                placeholder="Enter the master password"
                value={masterPassword}
                onChange={(e) => setMasterPassword(e.target.value)}
                required
                disabled={loading}
                className="border-border/30 focus:border-gal-cyan focus:ring-gal-cyan/20 bg-gal-card text-gal-text-primary placeholder:text-muted-foreground/60 rounded-gal"
              />
            </div>
            
            {error && (
              <div className="flex items-center gap-2 p-3 rounded-xl bg-gradient-to-r from-gal-error/10 to-transparent border border-gal-error/30 text-gal-error">
                <AlertCircle className="h-5 w-5 flex-shrink-0" />
                <span className="text-sm font-montserrat">{error}</span>
              </div>
            )}
            
            <Button
              type="submit"
              className="w-full gal-button-primary text-white font-semibold font-montserrat text-base py-3 rounded-gal transition-all duration-300"
              disabled={loading}
            >
              <span className="flex items-center justify-center gap-2">
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Authenticating...
                  </>
                ) : (
                  <>
                    <Lock className="h-4 w-4" />
                    Access Dashboard
                  </>
                )}
              </span>
            </Button>
          </form>
          
          <div className="mt-8 text-center text-xs text-muted-foreground font-montserrat">
            Guardian Angel League - Live Graphics Dashboard
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
