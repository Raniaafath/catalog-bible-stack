import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const plugins = [react()];
  
  // Only enable componentTagger if explicitly enabled via env var
  // This prevents ERR_BLOCKED_BY_PRIVATE_NETWORK_ACCESS_CHECKS errors
  // from telemetry requests to localhost:7245
  if (mode === "development" && process.env.VITE_ENABLE_LOVABLE_TAGGER === "true") {
    plugins.push(componentTagger());
  }
  
  return {
    server: {
      host: "::",
      port: 8080,
      hmr: {
        overlay: false,
      },
    },
    plugins,
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            "vendor-react": ["react", "react-dom", "react-router-dom"],
            "vendor-query": ["@tanstack/react-query"],
            "vendor-ui": ["@radix-ui/react-dialog", "@radix-ui/react-dropdown-menu", "@radix-ui/react-label", "@radix-ui/react-select", "@radix-ui/react-slot", "@radix-ui/react-tabs", "@radix-ui/react-toast", "@radix-ui/react-tooltip"],
          },
        },
      },
      chunkSizeWarningLimit: 600,
    },
  };
});
