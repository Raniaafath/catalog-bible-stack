import { lazy, Suspense } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppLayout } from "@/components/AppLayout";
import { DocumentTitle } from "@/hooks/useDocumentTitle";

import Auth from "./pages/Auth";
import Dashboard from "./pages/Dashboard";

const ImportsList = lazy(() => import("./pages/imports/ImportsList"));
const ImportNew = lazy(() => import("./pages/imports/ImportNew"));
const ImportPreview = lazy(() => import("./pages/imports/ImportPreview"));
const ImportAssignCategory = lazy(() => import("./pages/imports/ImportAssignCategory"));
const ImportMapAttributes = lazy(() => import("./pages/imports/ImportMapAttributes"));
const ProductsList = lazy(() => import("./pages/products/ProductsList"));
const ProductNew = lazy(() => import("./pages/products/ProductNew"));
const ProductDetail = lazy(() => import("./pages/products/ProductDetail"));
const VariantsList = lazy(() => import("./pages/products/VariantsList"));
const GroupsList = lazy(() => import("./pages/groups/GroupsList"));
const GroupDetail = lazy(() => import("./pages/groups/GroupDetail"));
const TranslationsList = lazy(() => import("./pages/translations/TranslationsList"));
const TranslationNew = lazy(() => import("./pages/translations/TranslationNew"));
const TranslationDetail = lazy(() => import("./pages/translations/TranslationDetail"));
const KeywordsList = lazy(() => import("./pages/keywords/KeywordsList"));
const KeywordsNew = lazy(() => import("./pages/keywords/KeywordsNew"));
const KeywordsDetail = lazy(() => import("./pages/keywords/KeywordsDetail"));
const KeywordsMappings = lazy(() => import("./pages/keywords/KeywordsMappings"));
const KeywordsSavedTerms = lazy(() => import("./pages/keywords/KeywordsSavedTerms"));
const ContentList = lazy(() => import("./pages/content/ContentList"));
const ContentNew = lazy(() => import("./pages/content/ContentNew"));
const GenerateTitles = lazy(() => import("./pages/content/GenerateTitles"));
const GeneratedTitlesList = lazy(() => import("./pages/content/GeneratedTitlesList"));
const ExportsList = lazy(() => import("./pages/exports/ExportsList"));
const ExportsNew = lazy(() => import("./pages/exports/ExportsNew"));
const ExportCsvPage = lazy(() => import("./pages/exports/ExportCsvPage"));
const AttributesList = lazy(() => import("./pages/attributes/AttributesList"));
const AttributeEdit = lazy(() => import("./pages/attributes/AttributeEdit"));
const TemplatesList = lazy(() => import("./pages/templates/TemplatesList"));
const TemplateForm = lazy(() => import("./pages/templates/TemplateForm"));
const TemplateWizard = lazy(() => import("./pages/templates/TemplateWizard"));
const Settings = lazy(() => import("./pages/settings/Settings"));
const NotFound = lazy(() => import("./pages/NotFound"));

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
        <DocumentTitle />
        <AuthProvider>
          <Suspense fallback={<div className="flex min-h-screen items-center justify-center">Loading…</div>}>
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

            {/* Products */}
            <Route path="/products" element={<ProtectedRoute><AppLayout><ProductsList /></AppLayout></ProtectedRoute>} />
            <Route path="/products/new" element={<ProtectedRoute><AppLayout><ProductNew /></AppLayout></ProtectedRoute>} />
            <Route path="/products/:id" element={<ProtectedRoute><AppLayout><ProductDetail /></AppLayout></ProtectedRoute>} />
            <Route path="/variants" element={<ProtectedRoute><AppLayout><VariantsList /></AppLayout></ProtectedRoute>} />
            
            {/* Listing Groups (Channel Listings) */}
            <Route path="/groups" element={<ProtectedRoute><AppLayout><GroupsList /></AppLayout></ProtectedRoute>} />
            <Route path="/groups/:id" element={<ProtectedRoute><AppLayout><GroupDetail /></AppLayout></ProtectedRoute>} />
            
            {/* Translations */}
            <Route path="/translations" element={<ProtectedRoute><AppLayout><TranslationsList /></AppLayout></ProtectedRoute>} />
            <Route path="/translations/new" element={<ProtectedRoute><AppLayout><TranslationNew /></AppLayout></ProtectedRoute>} />
            <Route path="/translations/:id" element={<ProtectedRoute><AppLayout><TranslationDetail /></AppLayout></ProtectedRoute>} />
            
            {/* Keywords */}
            <Route path="/keywords" element={<ProtectedRoute><AppLayout><KeywordsList /></AppLayout></ProtectedRoute>} />
            <Route path="/keywords/saved-terms" element={<ProtectedRoute><AppLayout><KeywordsSavedTerms /></AppLayout></ProtectedRoute>} />
            <Route path="/keywords/new" element={<ProtectedRoute><AppLayout><KeywordsNew /></AppLayout></ProtectedRoute>} />
            <Route path="/keywords/:id" element={<ProtectedRoute><AppLayout><KeywordsDetail /></AppLayout></ProtectedRoute>} />
            <Route path="/keywords/:id/mappings" element={<ProtectedRoute><AppLayout><KeywordsMappings /></AppLayout></ProtectedRoute>} />
            
            {/* Content */}
            <Route path="/content" element={<ProtectedRoute><AppLayout><ContentList /></AppLayout></ProtectedRoute>} />
            <Route path="/content/new" element={<ProtectedRoute><AppLayout><ContentNew /></AppLayout></ProtectedRoute>} />
            <Route path="/content/generate-titles" element={<ProtectedRoute><AppLayout><GenerateTitles /></AppLayout></ProtectedRoute>} />
            <Route path="/content/generated-titles" element={<ProtectedRoute><AppLayout><GeneratedTitlesList /></AppLayout></ProtectedRoute>} />
            
            {/* Exports */}
            <Route path="/exports" element={<ProtectedRoute><AppLayout><ExportsList /></AppLayout></ProtectedRoute>} />
            <Route
              path="/exports/new"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <ExportsNew />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/exports/csv"
              element={
                <ProtectedRoute>
                  <AppLayout>
                    <ExportCsvPage />
                  </AppLayout>
                </ProtectedRoute>
              }
            />
            
            {/* Attributes */}
            <Route path="/attributes" element={<ProtectedRoute><AppLayout><AttributesList /></AppLayout></ProtectedRoute>} />
            <Route path="/attributes/new" element={<ProtectedRoute><AppLayout><AttributeEdit /></AppLayout></ProtectedRoute>} />
            <Route path="/attributes/:id/edit" element={<ProtectedRoute><AppLayout><AttributeEdit /></AppLayout></ProtectedRoute>} />

            {/* Templates */}
            <Route path="/templates" element={<ProtectedRoute><AppLayout><TemplatesList /></AppLayout></ProtectedRoute>} />
            <Route path="/templates/new" element={<ProtectedRoute><AppLayout><TemplateWizard /></AppLayout></ProtectedRoute>} />
            <Route path="/templates/:id/edit" element={<ProtectedRoute><AppLayout><TemplateForm /></AppLayout></ProtectedRoute>} />
            
            {/* Settings */}
            <Route path="/settings" element={<ProtectedRoute><AppLayout><Settings /></AppLayout></ProtectedRoute>} />
            
            <Route path="*" element={<NotFound />} />
          </Routes>
          </Suspense>
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
