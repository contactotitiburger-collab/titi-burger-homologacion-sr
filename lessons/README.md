# Lessons — Infraestructura de aprendizaje para sub-agentes

## Propósito

Permitir que cada sub-agente custom (definido en `~/.claude/agents/<nombre>.md`) acumule reglas aprendidas de correcciones humanas a través del tiempo, sin contaminar el contexto de Tito-main.

**Tito-main NO usa esta infraestructura.** Su aprendizaje vive en `MEMORY.md` y `~/.openclaw/workspace/memory/`. Esto es solo para sub-agentes.

## Cómo funciona

### Para cada sub-agente nuevo

1. Cuando se define un sub-agent type en `~/.claude/agents/<nombre>.md`, se crea simultáneamente `~/.openclaw/lessons/<nombre>.md` (puede arrancar vacío con header).
2. El systemPrompt del sub-agente incluye instrucción explícita:
   - "Al iniciar: lee `~/.openclaw/lessons/<nombre>.md`. Aplica esas reglas durante todo tu trabajo."
   - "Al terminar (después de corrección humana confirmada): appendea entrada nueva al archivo."

### Durante una sesión del sub-agente

- Lee su archivo de lessons como parte del contexto inicial.
- Si recibe corrección del invocador (Tito-main, Digol, Staff, Dude) → la aplica al trabajo actual.
- Cuando el invocador confirma "quedó bien" / "así sí" → el sub-agente appendea entrada a su archivo de lessons antes de devolver control.

### Formato de entrada

```markdown
## YYYY-MM-DD — <autor> — <título corto>
**Regla:** <enunciado preciso de qué hacer / qué no hacer>
**Razón:** <por qué — lo que el autor dijo o se infiere>
**Aplica:** <cuándo dispara la regla — condición concreta>
**Ejemplo del error:** <opcional — qué hice mal>
**Corrección:** <qué hago en su lugar>
```

### Mantenimiento (responsabilidad de Tito-main)

Cuando un archivo de lessons crece o acumula contradicciones:

1. Tito-main lo lee fuera de sesión normal (mantenimiento explícito o heartbeat).
2. Consolida reglas universales hacia los docs canónicos del sub-agente (SKILL.md, PATTERNS.md de su skill).
3. Deja en lessons solo las específicas o recientes.
4. Resuelve contradicciones — la regla más reciente y vigente gana; la obsoleta se borra o se anota como deprecada.

## Línea importante

Las lessons NO son fuente de verdad **del cliente** ni **del negocio**. Son reglas del **oficio** del sub-agente.

- ❌ "El cliente XYZ pidió que…" → eso va en `~/.openclaw/clients/<slug>/`.
- ✅ "Para rubro restaurante, navbar opaca siempre" → eso va en lessons.

## Manejo de contradicciones

Cuando un sub-agente detecta que una nueva corrección contradice una regla previa en su archivo:

1. NO decide solo cuál aplica.
2. Pregunta al invocador: "Hay regla previa que dice X (fecha, autor). Tu corrección dice Y. ¿Deprecamos X o Y aplica en contexto distinto?"
3. Actúa según la respuesta y reescribe la regla obsoleta (deprecar o ajustar condición de "Aplica").

## Por qué Tito-main está exento

- Mi contexto es escaso (1 ventana, 1M tokens nominal). Cada token cargado tiene costo cognitivo.
- Las correcciones a mi comportamiento ya viven en `MEMORY.md` con índice curado.
- Sub-agentes son stateless cada invocación; un archivo pequeño de lessons es barato cargarles.
- Decisión confirmada por Digol el 2026-06-01.

## Archivos por sub-agente

| Sub-agent type | Archivo                                 | Estado  |
|----------------|-----------------------------------------|---------|
| web-builder    | `~/.openclaw/lessons/web-builder.md`    | seed    |

Se agregan filas conforme se crean sub-agentes nuevos.
