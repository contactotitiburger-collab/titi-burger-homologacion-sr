# astro-cliente — skeleton mínimo

Punto de partida que el sub-agente `web-builder` copia a `~/.openclaw/clients/<slug>/site/` antes de escribir el sitio.

## Qué incluye

- Astro 5 + Tailwind 3
- TypeScript strict + path aliases (`@components/*`, `@layouts/*`, `@styles/*`)
- `src/layouts/Base.astro` — base con SEO meta + JSON-LD slot
- `src/styles/tokens.css` — CSS vars (colores, motion, radii) — el sub-agente sobreescribe colores con `brand` del brief
- `src/styles/global.css` — reset + tipografía + utilidades (`.container-page`, `.section-pad`)
- `src/pages/index.astro` — placeholder que el sub-agente SOBREESCRIBE
- `prefers-reduced-motion` ya respetado en global

## Qué NO incluye (intencional)

- Cero componentes "out of the box" — render libre: el sub-agente decide qué componentes crear.
- Cero secciones pre-construidas — render libre: el sub-agente diseña la estructura por sitio.
- Cero fuentes web cargadas — stack system-first; si el sub-agente decide cargar Inter o similar, lo agrega.

## Uso (por el sub-agente)

```bash
# 1. Copiar skeleton al cliente
cp -r ~/.openclaw/templates/astro-cliente ~/.openclaw/clients/<slug>/site

# 2. Instalar deps
cd ~/.openclaw/clients/<slug>/site && npm install

# 3. Personalizar tokens.css con colores del brief

# 4. Escribir src/pages/index.astro desde cero (render libre)

# 5. Build de validación
npm run build

# 6. Lighthouse de validación
# (Lighthouse local o equivalente)

# 7. Preview
npm run preview
```

Ver `~/.openclaw/skills/crear-sitio/SKILL.md` para el procedimiento completo.
