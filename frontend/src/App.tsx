import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { TransactionsPage } from './pages/Transactions';
import { UploadPage } from './pages/Upload';
import { BudgetingPage } from './pages/Budgeting';
import { Personalization } from './pages/Personalization';
import { Settings } from './pages/Settings';
import { LoginPage } from './pages/Login';
import Reports from './pages/Reports';
import { RegisterPage } from './pages/Register';
import { LandingPage } from './pages/Landing';
import { AuthProvider, useAuth } from './context/AuthContext';
import { PreferencesProvider } from './context/PreferencesContext';
import './index.css';

// Initialize React Query client with default options
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // Cache data for 5 minutes
      refetchOnWindowFocus: false, // Disable refetching on window focus
    },
  },
});

/**
 * A component that protects routes requiring authentication.
 * It checks the authentication status from the AuthContext.
 * While loading, it shows a loading indicator.
 * If the user is not authenticated, it redirects to the login page.
 * @param {object} props - The component props.
 * @param {React.ReactNode} props.children - The child components to render if authenticated.
 * @returns {JSX.Element} The protected route component.
 */
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div>Loading...</div>; // Or a spinner component
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

/**
 * The main application component.
 * It sets up the context providers (QueryClient, Preferences, Auth) and the router.
 * Public routes for login and register are available to everyone.
 * Other routes are protected and wrapped in the Layout component.
 * @returns {JSX.Element} The App component.
 */
function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <PreferencesProvider>
        <AuthProvider>
          <Router>
            <Routes>
              {/* Public Routes */}
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              
              {/* Protected Routes */}
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <Dashboard />
                    </Layout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/transactions"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <TransactionsPage />
                    </Layout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/upload"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <UploadPage />
                    </Layout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/budgeting"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <BudgetingPage />
                    </Layout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/personalization"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <Personalization />
                    </Layout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/settings"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <Settings />
                    </Layout>
                  </ProtectedRoute>
                }
              />
              <Route
                path="/reports"
                element={
                  <ProtectedRoute>
                    <Layout>
                      <Reports />
                    </Layout>
                  </ProtectedRoute>
                }
              />
              {/* Redirect any other path to the dashboard */}
              <Route path="*" element={<Navigate to="/dashboard" />} />
            </Routes>
          </Router>
        </AuthProvider>
      </PreferencesProvider>
    </QueryClientProvider>
  );
}

export default App;
