import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");

  return {
    plugins: [react()],
    define: {
      "import.meta.env.VITE_SUPABASE_URL": JSON.stringify(env.SUPABASE_URL),
      "import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY": JSON.stringify(
        env.SUPABASE_PUBLISHABLE_KEY,
      ),
    },
  };
});
