---
name: patterns-crear-sitio
description: Principios universales de buena web que el sub-agente `web-builder` aplica en TODO sitio, encima de los patterns que extraiga de la investigación del rubro. No es un sistema estético fijo — es la base.
status: V1
---

# Principios universales — web-builder

Esto NO dicta cómo se ve el sitio (eso depende del rubro y del research). Esto es la base no negociable que aplica a todo sitio que el sub-agente emita, sin importar el rubro.

Si el research del rubro contradice alguno de estos principios, **gana el principio universal**. Esto evita que se replique algo malo solo porque es común en un rubro.

---

## 1. Jerarquía visual clara

**Principio:** el visitante entiende en <2 segundos qué es el negocio y qué se espera que haga. La jerarquía tipográfica + composición lo guían sin pensar.

**Aplicación:**
- Hero: 1 título principal + 1 subtítulo + 1 CTA primario. No más.
- Cada sección tiene un H2 claro, no decorativo.
- Tamaños tipográficos diferenciados (mínimo 3x ratio entre body y display).
- El CTA primario es visualmente dominante en cada bloque.

---

## 2. Legibilidad

**Principio:** el texto se lee sin esfuerzo en cualquier dispositivo y condición.

**Aplicación:**
- Body mínimo 16px en móvil, 18px en desktop.
- Line-height generoso (1.5-1.7 para body).
- Ancho de línea controlado (`max-w-prose` o `~65ch` para párrafos).
- Contraste WCAG AA mínimo (AAA preferido para body). Verificar con cualquier checker.
- Cero texto sobre imagen sin overlay/scrim suficiente.
- Cero párrafos sin aire — si hay tres oraciones, hay separación.

---

## 3. Performance

**Principio:** el sitio carga rápido en 4G mexicano promedio. Lighthouse Performance ≥ 90 obligatorio.

**Aplicación:**
- Astro static-first (SSR solo si justificado).
- Imágenes vía `<Image>` de Astro → WebP/AVIF auto + lazy loading.
- Fuentes web minimizadas: máximo 2 familias, máximo 4 pesos totales, subset latin si aplica.
- Cero librerías JS innecesarias. Tailwind purgado.
- CSS crítico inline si el render lo requiere (Astro lo hace por default razonablemente).
- Animaciones con `transform` y `opacity` solamente (compositor-friendly).
- Cero carga de scripts de terceros sin justificación (no FB pixel/GA sin pedirlo el cliente).

---

## 4. Mobile-first responsive

**Principio:** la mayoría del tráfico es móvil. El sitio se diseña móvil primero y se expande.

**Aplicación:**
- Layouts en columna en móvil; horizontales en `md+`.
- Botones táctiles mínimo 44×44px de área tocable.
- Navegación móvil: hamburguesa O bottom-bar; nunca menú escondido sin affordance.
- Imágenes con `srcset` para resoluciones distintas.
- Probar en breakpoints reales: 375px (móvil chico), 768px (tablet), 1280px (desktop).

---

## 5. Accesibilidad (a11y)

**Principio:** el sitio funciona con teclado, lector de pantalla, y ojos imperfectos. Lighthouse Accessibility ≥ 95.

**Aplicación:**
- HTML semántico: `<nav>`, `<main>`, `<section>`, `<article>`, `<footer>`. No todo divs.
- Headings sin saltarse niveles (H1 → H2 → H3, no H1 → H3).
- Alt text en TODA imagen no decorativa. `alt=""` en decorativas.
- Focus visible en todo elemento interactivo (no `outline: none` sin reemplazo).
- Labels asociados a inputs (`<label for="...">` o input dentro de label).
- `prefers-reduced-motion`: si el usuario lo activa, animaciones se desactivan o reducen.
- `prefers-color-scheme` respetado si el sitio tiene dark mode.
- Color no es la única señal (errores no son solo rojos — tienen ícono o texto).

---

## 6. SEO técnico

**Principio:** Google y similares encuentran y entienden el sitio. Lighthouse SEO ≥ 95.

**Aplicación:**
- `<title>` único por página, ≤60 chars, con nombre del negocio.
- `<meta name="description">` ≤155 chars, descripción real (no keywords spam).
- Open Graph + Twitter Card tags con imagen.
- Schema.org JSON-LD: `LocalBusiness`, `Restaurant`, o el tipo que aplique al rubro. Datos vienen del brief.
- URLs limpias (sin query strings innecesarios).
- `robots.txt` y `sitemap.xml` generados por Astro.
- Lang attribute en `<html>` correcto (`es-MX` o lo que diga el brief).

---

## 7. Consistencia interna

**Principio:** el sitio se siente diseñado, no ensamblado.

**Aplicación:**
- Tokens CSS para colores, spacing, radii, sombras — definidos en un solo lugar.
- Espaciados de un mismo sistema (escala 4/8 o múltiplos consistentes).
- Tipografía con escala definida (no tamaños arbitrarios).
- Componentes reutilizan estilos, no inline-styles dispersos.
- Animaciones con duración y easing consistentes (ej. 600ms ease-out en todo).

---

## 8. Carga visual proporcional al contenido

**Principio:** cada bloque visualmente compite por atención lo que su importancia merece.

**Aplicación:**
- CTA primario: alto contraste, alto peso.
- CTA secundario: presente pero menor (outline, link).
- Botones de baja prioridad (compartir, login): no compiten con el principal.
- Headers de sección: visibles pero no saturan.
- Footer: presente, discreto.

---

## 9. Adaptación al rubro (research-driven)

**Principio:** el rubro define el lenguaje visual. El sub-agente NO impone su preferencia.

**Aplicación:**
- Después del research, el sub-agente extrae:
  - Paleta dominante del rubro (cálido vs frío, saturado vs sobrio).
  - Tipografía típica (serif elegante para abogados, sans display para tech, custom hand para gastronomía artesanal).
  - Densidad de información (servicios técnicos = más data; lifestyle = más aire).
  - Tratamiento fotográfico (producto centrado vs ambient, alto vs medio contraste).
- Adopta esos patrones, NO los suyos personales.
- Si el rubro no tiene buenas referencias (rubro raro), aplica los principios universales con paleta y tipografía neutras.

---

## 10. Cero copia, máxima inspiración

**Principio:** aprender de las referencias está bien; replicarlas literal no.

**Aplicación:**
- NUNCA copiar HTML/CSS/JS de las referencias. Solo describir el patrón en lenguaje natural y reimplementar.
- NUNCA usar assets de las referencias (imágenes, iconos, vectores).
- NUNCA usar copy textual de las referencias.
- Si hay duda de cercanía, ajustar — más vale diferente que copia.

---

## Cuándo dark mode

NO automático en todo sitio. Aplicar dark mode solo si:

- El rubro lo usa típicamente (apps tech, productos digitales, gaming, contenido editorial nocturno).
- El cliente lo pide explícitamente en el brief.

NO aplicar dark mode si:

- Rubro tradicional/cálido (gastronomía, salud, retail físico, servicios profesionales conservadores).
- Imágenes del cliente son crudas/con fondo blanco (se ven mal en dark).

---

## Cuándo animaciones agresivas

NO automático. Aplicar solo si:

- El rubro las usa (creativos, fashion, gaming, entretenimiento).
- Refuerzan jerarquía (fade-in al scroll para revelar contenido por etapas).
- Tienen `prefers-reduced-motion` respetado.

NO aplicar si:

- Rubro serio/conservador (legal, médico, gubernamental, financiero conservador).
- El sitio carga lento por animaciones.
- Hay más de 3 elementos animándose simultáneamente en viewport.

---

## Tokens base sugeridos (skeleton)

Pueden sobreescribirse por cliente, pero esto va en el skeleton de Astro como punto de partida:

```css
:root {
  /* Tipografía: stack system-first (renderea SF Pro en Mac/iOS gratis) */
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", system-ui, sans-serif;
  --font-display: var(--font-sans);

  /* Escala (sobreescrita por brief si aplica) */
  --color-bg: #ffffff;
  --color-fg: #111111;
  --color-muted: #6e6e73;
  --color-subtle: #f5f5f7;
  --color-border: #d2d2d7;
  --color-brand: <del brief primary_color>;
  --color-brand-secondary: <del brief secondary_color>;

  /* Espaciado / radii */
  --space-section: clamp(5rem, 10vw, 8rem);  /* py-20 a py-32 */
  --radius-card: 1rem;
  --radius-button: 9999px;  /* pill por default; sub-agente puede cambiar según rubro */

  /* Easing/duration */
  --motion-duration: 700ms;
  --motion-easing: cubic-bezier(0.16, 1, 0.3, 1);
}
```

---

## Referencias internas

- Procedimiento que usa estos principios: `~/.openclaw/skills/crear-sitio/SKILL.md`
- Lessons acumuladas del sub-agente: `~/.openclaw/lessons/web-builder.md`
- Sub-agent definition: `~/.claude/agents/web-builder.md`
