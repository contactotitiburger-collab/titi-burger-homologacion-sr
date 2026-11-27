---
name: crear-sitio
description: Genera un sitio web one-pager para un cliente. El sub-agente `web-builder` investiga referencias del rubro y escribe el código desde cero (render libre). Stack Astro + Tailwind, deploy a Cloudflare Pages.
owner: tito-main
invoked_by: web-builder sub-agent type
status: V1 - render libre
quality_bar: alto — el sitio resultante debe ser tan bueno o mejor que las referencias top del rubro
---

# Skill: crear-sitio

## Propósito

Emite un sitio web one-pager de calidad alta a partir de un brief estructurado. El sub-agente `web-builder` no rellena una plantilla fija — investiga referencias del rubro del cliente, extrae patrones observables, y escribe el código desde cero usando esos patrones + reglas de `PATTERNS.md` + lessons acumuladas.

**Quality bar:** el sitio resultante debe quedar tan bueno o mejor que las referencias top del rubro. No "decente" — bueno de verdad. Indicador: si el cliente pudiera pagar a una agencia de calidad media, ¿este sitio sería preferible? La respuesta debe ser sí.

## Cuándo se invoca

- Brief de cliente nuevo completo y validado.
- Iteración a sitio existente: rehacer desde el brief (la fuente de verdad es siempre el brief, no el código generado).

## Quién lo invoca

Tito-main vía el sub-agent type `web-builder`. Tito-main NUNCA ejecuta esta skill en su contexto principal — siempre delega.

## Input: brief.yaml

Ubicación: `~/.openclaw/clients/<slug>/brief.yaml`. Los creadores (Digol/Staff/Dude) llenan TODO el contenido. El sub-agente no inventa nada.

```yaml
business:
  name: string                    # requerido
  slug: string                    # requerido — kebab-case
  industry: string                # requerido — libre, ej. "hamburguesería", "papelería"
  tagline: string                 # requerido — 1 línea de propuesta de valor
  language: "es-MX" | "en"        # default "es-MX"

contact:                          # al menos un canal requerido
  phone: string                   # E.164 — ej. "+52 686 123 4567"
  whatsapp: string                # E.164 con +521 para México móvil (ver [[whatsapp-mexico-numero-1]])
  email: string

locations:                        # opcional — si no hay, omite sección
  - name: string
    address: string
    hours: string
    maps_url: string

branding:
  logo: string                    # path relativo al brief o URL
  primary_color: string           # hex
  secondary_color: string         # hex

products:                         # mínimo 3 si la sección se incluye
  - name: string
    description: string           # los creadores escriben — el agente no expande
    price: number                 # opcional
    image: string                 # path o URL

about: string                     # markdown, escrito por los creadores

cta:                              # objetivo principal del sitio
  type: "whatsapp" | "call" | "form" | "external_link"
  label: string
  target: string

social:                           # opcional
  facebook: string
  instagram: string
  tiktok: string
```

### Validaciones

- Campos requeridos presentes.
- `slug` matches `[a-z0-9-]+`.
- Colores hex válidos.
- Al menos un canal de contacto.
- Si `cta.type == "whatsapp"`: target empieza con `+521` (México móvil).
- Si `products` presente: mínimo 3 items.
- Assets (logo, fotos) existen en filesystem o URL responde.

Si validación falla → no genera, devuelve lista de errores.

## Procedimiento (orden estricto)

### Fase 0 — Carga de contexto

1. Lee `brief.yaml` del cliente.
2. Lee `~/.openclaw/lessons/web-builder.md` — aplica esas reglas durante todo el trabajo.
3. Lee `PATTERNS.md` (principios universales de buena web).
4. Valida brief. Si falla, aborta con reporte de errores.

### Fase 1 — Research del rubro

1. Identifica el rubro por `business.industry`.
2. Vía `WebSearch`: encuentra 5-7 sitios web actuales considerados buenos del rubro. Mezcla:
   - 3-4 referencias internacionales reconocidas (premium quality).
   - 1-2 referencias del mercado mexicano si existen (familiaridad cultural).
   - 1-2 referencias adyacentes que aporten ideas (ej. para restaurantes, ver también hotelería boutique).
3. Vía `WebFetch`: obtiene HTML observable de cada referencia.
4. Para cada referencia extrae y documenta **solo patrones**, NUNCA copia HTML/CSS literal:
   - Estructura del hero (layout, tipografía, imagen).
   - Paleta dominante (en lenguaje natural: "blanco con acento rojo cálido").
   - Secciones que tienen y orden.
   - Tratamiento de fotografía (overlay, ratio, encuadre).
   - Densidad tipográfica (jerarquía, pesos, tamaños relativos).
   - Microinteracciones notables.
5. Escribe `~/.openclaw/clients/<slug>/research.md` con el resumen y links a las 5-7 fuentes.
6. **Línea roja:** si no encuentras al menos 3 referencias decentes del rubro, reporta al invocador antes de seguir. No improvises sin base.

### Fase 2 — Síntesis del diseño

1. Decide tono visual del sitio en base a:
   - Brief (`industry`, `tagline`, colores del cliente).
   - Patterns observados del rubro.
   - Reglas universales de `PATTERNS.md`.
   - Lessons aplicables.
2. Escribe `~/.openclaw/clients/<slug>/design-decision.md` — qué decisiones tomaste y por qué. 5-8 bullets.
3. Esto NO es para el cliente — es trazabilidad para Tito-main y para Digol cuando revise.

### Fase 3 — Scaffolding

1. Copia `~/.openclaw/templates/astro-cliente/` (skeleton mínimo: package.json, astro.config, tailwind.config, layout base, tipografía, tokens CSS) a `~/.openclaw/clients/<slug>/site/`.
2. Personaliza `tailwind.config` y CSS tokens con los colores del brief.
3. Copia assets del brief (logo, fotos) a `public/`.

### Fase 4 — Código del sitio (render libre)

1. Escribe `src/pages/index.astro` desde cero, NO desde plantilla. Estructura, secciones y micro-componentes son decisión del sub-agente basada en research + brief.
2. Crea componentes auxiliares en `src/components/` solo si aplican (Nav, Footer, ProductCard, etc.). Cero componentes inservibles.
3. Implementa animaciones on-scroll si el rubro las usa (con `prefers-reduced-motion` respetado).
4. Implementa responsive: móvil primero, tablet, desktop. Probar en breakpoints `sm`, `md`, `lg`.
5. Implementa dark mode SOLO si el rubro lo justifica (apps tech sí, restaurante tradicional no).
6. SEO metadata: title, description, OG tags, schema.org JSON-LD (LocalBusiness o Restaurant según `industry`). Esto el sub-agente lo escribe desde campos del brief — NO inventa.
7. Alt text de imágenes: el sub-agente puede generar describiendo lo que ve en la imagen (objetiva, no marketinera).

### Fase 5 — QA antes de reportar

Checklist interna ejecutada por el sub-agente antes de devolver control:

- [ ] `npm install` completa sin errores.
- [ ] `npm run build` exitoso. Falla = no proceder.
- [ ] `npm run preview` arranca y el sitio carga.
- [ ] Lighthouse local (vía `npx lighthouse` o equivalente): Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 90, SEO ≥ 95. Si no llega, ajusta antes de reportar.
- [ ] Vista móvil revisada: nada cortado, CTAs accesibles, tipografía legible.
- [ ] Todos los CTAs apuntan a target correcto del brief.
- [ ] Imágenes optimizadas (usar `<Image>` de Astro para conversión automática a WebP).
- [ ] Cero `console.log` o código de debug.
- [ ] No queda copy placeholder ("Lorem ipsum", "TODO", "Pendiente").
- [ ] No queda referencia visual a competidores ni Apple — todo es propio.

Si algún ítem falla, el sub-agente lo arregla antes de reportar.

### Fase 6 — Output al invocador

Reporta a Tito-main con:

1. Ruta del sitio: `~/.openclaw/clients/<slug>/site/`.
2. Comando de preview: `cd ~/.openclaw/clients/<slug>/site && npm run preview`.
3. Path a `research.md` y `design-decision.md` para trazabilidad.
4. Resumen de decisiones clave (2-3 bullets).
5. Gaps detectados en el brief si los hay (faltó foto de producto X, etc.).

### Fase 7 — Iteración con correcciones

Si Tito-main (o Digol/Staff/Dude por su voz) devuelve correcciones:

1. Aplica al sitio actual.
2. Espera confirmación "quedó bien".
3. Tras confirmar, **appendea entrada a `~/.openclaw/lessons/web-builder.md`** con el formato del template (ver `~/.openclaw/lessons/README.md`).
4. Si la corrección contradice una regla previa de lessons, NO decide solo — pregunta al invocador cuál aplica.

## Output esperado

```
~/.openclaw/clients/<slug>/
├── brief.yaml                  # input original — fuente de verdad
├── research.md                 # generado en Fase 1 — referencias del rubro
├── design-decision.md          # generado en Fase 2 — decisiones tomadas
├── DEPLOY.md                   # generado al final — instrucciones de deploy
└── site/                       # proyecto Astro listo
    ├── src/
    │   ├── pages/index.astro   # escrito desde cero por el sub-agente
    │   ├── components/         # solo los necesarios
    │   ├── layouts/            # base layout
    │   └── styles/             # tokens CSS personalizados
    ├── public/                 # logo + fotos del cliente
    ├── astro.config.mjs
    ├── tailwind.config.mjs
    ├── package.json
    └── dist/                   # build de validación
```

## Reglas críticas (no negociables)

1. **Cero copia de código/assets ajeno.** Patrones observados se reimplementan en código propio.
2. **Cero invención de contenido.** Cada palabra del sitio viene del brief o es marca/SEO derivado de campos existentes.
3. **Quality bar alto.** Si el sub-agente no está orgulloso del output, no lo entrega.
4. **Performance no negociable.** Build pasa Lighthouse o no se reporta.
5. **Lessons primero.** Cada invocación lee lessons antes de empezar; cada corrección confirmada se escribe a lessons.

## Versionado

Esta skill vive en `~/.openclaw/skills/crear-sitio/`. Cambios al procedimiento se hacen aquí, no en clientes individuales. Skeleton de Astro vive en `~/.openclaw/templates/astro-cliente/` y se actualiza con mejoras de toolkit; los clientes existentes pueden re-emitirse desde su `brief.yaml` para adoptar mejoras.

## Referencias

- Principios de diseño: `~/.openclaw/skills/crear-sitio/PATTERNS.md`
- Skeleton de scaffolding: `~/.openclaw/templates/astro-cliente/`
- Lessons del sub-agente: `~/.openclaw/lessons/web-builder.md`
- Sub-agent que lo ejecuta: `~/.claude/agents/web-builder.md`
- Decisiones arquitectónicas: [[eficiencia-contexto-y-agentes]], [[arquitectura-un-solo-tito]], [[lessons-infra-subagentes]]
