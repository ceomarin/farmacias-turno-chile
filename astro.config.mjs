// astro.config.mjs
// ============================================================
// CONFIGURACIÓN DE ASTRO PARA GITHUB PAGES
// ============================================================

// astro.config.mjs
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://ceomarin.github.io',
  base: '/farmacias-turno-chile',
  vite: {
    plugins: [tailwindcss()]
  },
  build: {
    outDir: './dist'
  }
});