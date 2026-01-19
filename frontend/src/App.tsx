import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppLayout } from "@/components/AppLayout";

import Auth from "./pages/Auth";
import Dashboard from "./pages/Dashboard";
import ImportsList from "./pages/imports/ImportsList";
import ImportNew from "./pages/imports/ImportNew";
import ImportPreview from "./pages/imports/ImportPreview";
import ImportAssignCategory from "./pages/imports/ImportAssignCategory";
import ImportMapAttributes from "./pages/imports/ImportMapAttributes";
import TranslationsList from "./pages/translations/TranslationsList";
import TranslationNew from "./pages/translations/TranslationNew";
import TranslationDetail from "./pages/translations/TranslationDetail";
import KeywordsList from "./pages/keywords/KeywordsList";
import KeywordsNew from "./pages/keywords/KeywordsNew";
import KeywordsDetail from "./pages/keywords/KeywordsDetail";
import ContentList from "./pages/content/ContentList";
import ContentNew from "./pages/content/ContentNew";
import ExportsList from "./pages/exports/ExportsList";
import ExportsNew from "./pages/exports/ExportsNew";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      retry: 1,
    },
  },
});

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/auth" element={<Auth />} />
            
            {/* Protected Routes */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <Dashboard />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            
            {/* Imports */}
            <Route path="/imports" element={<ProtectedRoute><AppLayout><ImportsList /></AppLayout></ProtectedRoute>} />
            <Route path="/imports/new" element={<ProtectedRoute><AppLayout><ImportNew /></AppLayout></ProtectedRoute>} />
            <Route path="/imports/:id" element={<ProtectedRoute><AppLayout><ImportPreview /></AppLayout></ProtectedRoute>} />
            <Route path="/imports/:id/assign-category" element={<ProtectedRoute><AppLayout><ImportAssignCategory /></AppLayout></ProtectedRoute>} />
            <Route path="/imports/:id/map-attributes" element={<ProtectedRoute><AppLayout><ImportMapAttributes /></AppLayout></ProtectedRoute>} />
            
            {/* Translations */}
            <Route path="/translations" element={<ProtectedRoute><AppLayout><TranslationsList /></AppLayout></ProtectedRoute>} />
            <Route path="/translations/new" element={<ProtectedRoute><AppLayout><TranslationNew /></AppLayout></ProtectedRoute>} />
            <Route path="/translations/:id" element={<ProtectedRoute><AppLayout><TranslationDetail /></AppLayout></ProtectedRoute>} />
            
            {/* Keywords */}
            <Route path="/keywords" element={<ProtectedRoute><AppLayout><KeywordsList /></AppLayout></ProtectedRoute>} />
            <Route path="/keywords/new" element={<ProtectedRoute><AppLayout><KeywordsNew /></AppLayout></ProtectedRoute>} />
            <Route path="/keywords/:id" element={<ProtectedRoute><AppLayout><KeywordsDetail /></AppLayout></ProtectedRoute>} />
            
            {/* Content */}
            <Route path="/content" element={<ProtectedRoute><AppLayout><ContentList /></AppLayout></ProtectedRoute>} />
            <Route path="/content/new" element={<ProtectedRoute><AppLayout><ContentNew /></AppLayout></ProtectedRoute>} />
            
            {/* Exports */}
            <Route path="/exports" element={<ProtectedRoute><AppLayout><ExportsList /></AppLayout></ProtectedRoute>} />
            <Route path="/exports/new" element={<ProtectedRoute><AppLayout><ExportsNew /></AppLayout></ProtectedRoute>} />
            
            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
