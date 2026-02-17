import React, { createContext, useContext, useEffect, useState } from 'react';
import axios from 'axios';
import { AUTH_TOKEN_KEY, AuthUser, getMe, login, logout, signup } from '@/lib/api';

type AppRole = 'admin' | 'user';

interface AuthContextType {
  user: AuthUser | null;
  role: AppRole | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<{ error: Error | null }>;
  signUp: (email: string, password: string, fullName?: string) => Promise<{ error: Error | null }>;
  signOut: () => Promise<void>;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [role, setRole] = useState<AppRole | null>(null);
  const [loading, setLoading] = useState(true);

  // #region agent log
  const _logDebug = (
    message: string,
    data: Record<string, unknown>,
    hypothesisId: string,
    runId: string = 'login'
  ) => {
    try {
      fetch('http://localhost:7245/ingest/96b3f58c-3c40-4802-bee1-1d92711a2981', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          location: 'frontend/src/contexts/AuthContext.tsx:signIn',
          message,
          data,
          hypothesisId,
          runId,
          timestamp: Date.now(),
        }),
      }).catch(() => {});
    } catch {
      // ignore debug logging errors
    }
  };
  // #endregion

  const isAdminUser = (authUser: AuthUser | null) =>
    Boolean(authUser?.is_staff || authUser?.is_superuser);

  const getErrorMessage = (error: unknown, fallback: string) => {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status;
      const detail = error.response?.data?.detail;
      if (typeof detail === 'string' && detail.trim()) {
        return detail;
      }
      // Helpful message when API is unreachable (proxy not forwarding /api or backend down)
      if (status === 404) {
        return 'API not found. Ensure the reverse proxy forwards /api to the Django backend.';
      }
      if (status === 502 || status === 503 || error.code === 'ERR_NETWORK') {
        return 'Cannot reach the server. Check that Django is running and the proxy forwards /api to it.';
      }
    }
    if (error instanceof Error && error.message) {
      return error.message;
    }
    return fallback;
  };

  useEffect(() => {
    const bootstrapAuth = async () => {
      const token = window.localStorage.getItem(AUTH_TOKEN_KEY);
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const { user: currentUser } = await getMe();
        setUser(currentUser);
        setRole(isAdminUser(currentUser) ? 'admin' : 'user');
      } catch (error) {
        console.error('Error restoring session:', error);
        window.localStorage.removeItem(AUTH_TOKEN_KEY);
        setUser(null);
        setRole(null);
      } finally {
        setLoading(false);
      }
    };

    bootstrapAuth();
  }, []);

  const signIn = async (email: string, password: string) => {
    // Hypothesis H1: incorrect API base URL or path – verify we are calling expected endpoint
    _logDebug('signIn:start', { hasEmail: !!email }, 'H1');
    try {
      const { token, user: loggedInUser } = await login(email, password);
      // Hypothesis H2: backend reachable and returns token/user correctly
      _logDebug('signIn:success', { hasUser: !!loggedInUser }, 'H2');
      window.localStorage.setItem(AUTH_TOKEN_KEY, token);
      setUser(loggedInUser);
      setRole(isAdminUser(loggedInUser) ? 'admin' : 'user');
      return { error: null };
    } catch (error) {
      const message = getErrorMessage(error, 'Login failed.');
      // Hypothesis H3: proxy/backend returns 502 or other network error on auth
      _logDebug(
        'signIn:error',
        {
          message,
          status: axios.isAxiosError(error) ? error.response?.status : null,
          url: axios.isAxiosError(error) ? error.config?.url : null,
        },
        'H3'
      );
      return { error: new Error(message) };
    }
  };

  const signUp = async (email: string, password: string, fullName?: string) => {
    try {
      const { token, user: newUser } = await signup(email, password, fullName);
      window.localStorage.setItem(AUTH_TOKEN_KEY, token);
      setUser(newUser);
      setRole(isAdminUser(newUser) ? 'admin' : 'user');
      return { error: null };
    } catch (error) {
      return { error: new Error(getErrorMessage(error, 'Signup failed.')) };
    }
  };

  const signOut = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Error logging out:', error);
    }
    window.localStorage.removeItem(AUTH_TOKEN_KEY);
    setUser(null);
    setRole(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role,
        loading,
        signIn,
        signUp,
        signOut,
        isAdmin: role === 'admin',
      }}
    >
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
