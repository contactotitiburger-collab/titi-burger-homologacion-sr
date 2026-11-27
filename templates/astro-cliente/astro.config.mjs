import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  integrations: [
    tailwind({
      applyBaseStyles: false,
    }),
  ],
  build: {
    inlineStylesheets: 'auto',
  },
  image: {
    service: { entrypoint: 'astro/assets/services/sharp' },
  },
});
