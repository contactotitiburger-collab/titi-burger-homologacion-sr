#!/usr/bin/env python3
"""
tito_escalar.py — escalador del bot de WhatsApp de Tito a Claude Opus 4.7 (Claude Max, $0).

Uso:
    python3 tito_escalar.py "<pregunta del usuario>"

Contexto:
    El bot de WhatsApp corre con Sonnet 4.6 (o Haiku antes). Cuando duda / alucina /
    no encuentra el script correcto, en vez de responder basura invoca este escalador.
    El escalador arma un prompt con el contexto del negocio + scripts disponibles y
    lo pasa a `claude -p --model claude-opus-4-7`. Como Claude Code corre bajo la
    suscripción Claude Max del usuario, el costo es $0.

    Opus puede responder directo o pedir ejecutar un comando con `EXEC: <cmd>`. En ese
    caso el escalador ejecuta y vuelve a llamar a Opus con el output (loop máx 3).

Salida:
    Una respuesta corta lista para copiar/pegar en WhatsApp (<= 4 líneas).
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from datetime import datetime

CLAUDE_BIN = "claude"
MODEL = "claude-opus-4-7"
MAX_ITER = 5               # loop máx (bot: 3; agregados como top-1 pueden pedir 4-5)
CLAUDE_TIMEOUT_S = 120     # timeout por llamada a Opus
EXEC_TIMEOUT_S   = 45      # timeout por comando delegado
MAX_OUTPUT_CHARS = 6000    # trunca outputs enormes al re-llamar Opus


SYSTEM_PROMPT = """Eres Tito (Doble T), el cerebro de IA de Titi Burger (hamburguesería en Mexicali, BC).
El bot de WhatsApp (que corre con Sonnet 4.6) NO supo responder una pregunta y te escaló a ti (Opus 4.7).
Tu trabajo: producir UNA respuesta corta (máximo 4 líneas) LISTA para copiar/pegar al usuario en WhatsApp.

# Negocio
- 6 sucursales: A=L Montejano, B=Hacienda del Río, C=Montecarlo, D=Villas del Rey, E=San Marcos, + Cine Curto.
- Dueño: Don Titi. Equipo: Rafael (papá, codename Staff), El Gatito, Digol, Angel.
- Encargado de horarios: Félix (patrón, no ficha).
- 16-30 empleados. Sistemas: SESAME (asistencia), Soft Restaurant (ventas), Google Sheet (horarios).

# Scripts disponibles (puedes pedir ejecución con EXEC:)
1. `python3 /home/tito/.openclaw/scripts/tito_query.py <flags>`  — asistencia/horas/faltas SESAME (última semana descargada).
   Subcomandos ÚNICOS: --quien-falto [--semana-pasada|--fecha YYYY-MM-DD], --horas <nombre>,
   --resumen-semana, --dias-trabajados <nombre>. NO inventes otros flags.
2. `python3 /home/tito/.openclaw/scripts/tito_sheet.py <accion>` — Google Sheet de HORARIOS FUTUROS.
   Acciones: cambiar_turno, marcar_falta, listar_personas. Solo si te piden ESCRIBIR al Sheet.
3. Puedes leer archivos con `cat`, `head`, `ls`, `python3 -c "..."` si necesitas ver datos crudos.
   Datos en: /home/tito/.openclaw/data/nomina/ (sesame_export_semXX.xlsx del sem 18 al 27, catalogo_empleados.json).

# Pistas para preguntas agregadas (top, ranking, promedio, comparativos)
`tito_query.py` NO tiene subcomando de top/ranking. Para "quién trabajó más horas", "los 3 que más faltaron",
"cuánto llevan entre todos los de Hacienda", etc. reusa las funciones internas de tito_query.py con python3 -c.
Usa EXACTAMENTE este patrón (probado, funciona):
  EXEC: python3 -c "import sys; sys.path.insert(0,'/home/tito/.openclaw/scripts'); from tito_query import load_sesame; h,f=load_sesame(); top=sorted(((sum(v.values()),k) for k,v in h.items()), reverse=True)[:3]; [print(f'{n}: {t:.1f}h') for t,n in top]"
Detalles del xlsx (por si necesitas otro corte): hoja 'Grupos y tipos de registro', columnas:
Empleado, Tipo, Nº ident, Fecha (DD/MM/YYYY string), Actividad, Grupo, Entrada, Salida, Tiempo registrado
El campo 'Tiempo registrado' es string 'HH:MM:SS' o datetime.time — NO int. Filas con Empleado=='TOTAL' son subtotales, ignóralas.
NO pidas subcomandos de tito_query.py que no estén en la lista de arriba.

# Cómo respondes
Formato exacto de tu turno (una de dos):

Opción A — sabes la respuesta sin ejecutar nada:
```
ANSWER: <respuesta corta lista para WhatsApp, máximo 4 líneas>
```

Opción B — necesitas ejecutar UN comando para saber la respuesta:
```
EXEC: <comando shell completo, una línea>
```
El sistema ejecutará el comando y te devolverá el output; en la siguiente vuelta responde con ANSWER:.

REGLAS DURAS
- SIEMPRE empieza tu turno con `ANSWER:` o `EXEC:`. Nada de bloques ```. Nada de explicaciones fuera.
- No inventes datos de asistencia/horas: si necesitas cifras, EXEC primero.
- Si la pregunta es imposible con los datos que tienes, di ANSWER: y explica al usuario qué falta (2 líneas).
- No mandes emojis extra. Máximo 1 emoji si el tono lo pide.
- Tono: fresa-respetuoso con Rafael/familia; directo y neutro con Félix/equipo; nunca slang naco.
- Si la pregunta pide algo fuera de scope (Soft Restaurant, Clip, Banorte, alta empleado nuevo, cubrir turno), di que aún no lo tienes y que le avisas a Rafael.
- Datos SESAME actuales: semana 22-28 jun 2026 en sesame_ultima_semana.xlsx; semanas anteriores en sesame_export_sem18..sem27.xlsx.
"""


def run_claude(user_message: str) -> str:
    """Llama a `claude -p` con Opus y devuelve el texto. Lanza RuntimeError si falla."""
    cmd = [
        CLAUDE_BIN,
        "-p",
        "--model", MODEL,
        "--output-format", "text",
        "--append-system-prompt", SYSTEM_PROMPT,
        user_message,
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT_S,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "Claude Code CLI no está instalado o no está en PATH. "
            "Instala con: npm i -g @anthropic-ai/claude-code"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Timeout ({CLAUDE_TIMEOUT_S}s) llamando a Opus.")

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()[:500]
        raise RuntimeError(f"claude -p falló (rc={proc.returncode}): {stderr}")

    out = (proc.stdout or "").strip()
    if not out:
        raise RuntimeError("claude -p devolvió output vacío.")
    return out


def parse_response(text: str) -> tuple[str, str]:
    """Extrae ('ANSWER' | 'EXEC', contenido). Tolerante a fences ``` y ruido leve."""
    # Limpia fences ``` que a veces mete el modelo.
    cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
    cleaned = re.sub(r"\n?```$", "", cleaned).strip()

    # Prioriza EXEC si aparece antes de ANSWER.
    m_exec = re.search(r"^\s*EXEC:\s*(.+)$", cleaned, re.MULTILINE)
    m_ans  = re.search(r"^\s*ANSWER:\s*(.+)$", cleaned, re.MULTILINE | re.DOTALL)

    if m_exec and (not m_ans or m_exec.start() < m_ans.start()):
        # EXEC es una línea (el comando shell). Tómala hasta el primer newline.
        return "EXEC", m_exec.group(1).strip()
    if m_ans:
        return "ANSWER", m_ans.group(1).strip()

    # Fallback: si Opus no siguió formato, trata todo como respuesta.
    return "ANSWER", cleaned


def run_exec(cmd: str) -> str:
    """Ejecuta el comando shell propuesto por Opus y devuelve el output truncado."""
    try:
        proc = subprocess.run(
            ["bash", "-c", cmd],
            capture_output=True,
            text=True,
            timeout=EXEC_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT {EXEC_TIMEOUT_S}s]"

    out = proc.stdout or ""
    err = proc.stderr or ""
    combined = out
    if err.strip():
        combined += ("\n[stderr]\n" + err)
    combined = combined.strip()
    if len(combined) > MAX_OUTPUT_CHARS:
        combined = combined[:MAX_OUTPUT_CHARS] + f"\n[...truncado, {len(combined)} chars]"
    if not combined:
        combined = f"[sin output; rc={proc.returncode}]"
    return combined


def _dbg(msg: str) -> None:
    if os.environ.get("TITO_ESCALAR_DEBUG"):
        print(f"[dbg] {msg}", file=sys.stderr)


def escalate(pregunta: str) -> str:
    """Loop hasta MAX_ITER: pregunta → Opus → (EXEC → output → Opus) → ANSWER."""
    hoy = datetime.now().strftime("%Y-%m-%d (%A)")
    conversacion = (
        f"Fecha de hoy: {hoy}.\n"
        f"Pregunta del usuario en WhatsApp (que el bot Sonnet no supo responder):\n"
        f"---\n{pregunta}\n---\n"
        "Responde con ANSWER: <texto> o EXEC: <comando>."
    )

    for it in range(1, MAX_ITER + 1):
        raw = run_claude(conversacion)
        kind, content = parse_response(raw)
        _dbg(f"iter {it} kind={kind} content_head={content[:200]!r}")

        if kind == "ANSWER":
            return content

        # kind == EXEC
        output = run_exec(content)
        _dbg(f"iter {it} exec_out_head={output[:200]!r}")
        conversacion = (
            f"Fecha de hoy: {hoy}.\n"
            f"Pregunta original del usuario:\n---\n{pregunta}\n---\n"
            f"Ejecuté el comando que pediste (iteración {it}/{MAX_ITER}):\n"
            f"$ {content}\n"
            f"--- output ---\n{output}\n--- fin output ---\n"
            "Ahora arma la respuesta final con ANSWER: <texto listo para WA>. "
            "Si de plano necesitas otro comando, usa EXEC: pero ya casi se acaban las vueltas."
        )

    # Se acabaron las iteraciones sin ANSWER final.
    return (
        "No pude armar una respuesta clara en este momento. "
        f"Rafael, revísalo por favor (escalación agotó {MAX_ITER} vueltas)."
    )


def main() -> int:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("uso: tito_escalar.py \"<pregunta>\"", file=sys.stderr)
        return 2
    pregunta = " ".join(sys.argv[1:]).strip()

    try:
        respuesta = escalate(pregunta)
    except RuntimeError as e:
        # Mensaje claro para el bot: no inventar, decir que falló la escalación.
        print(
            f"No pude consultar a Tito main (Opus) en este momento: {e}. "
            "Rafael, avísale a Digol por favor.",
        )
        return 1

    print(respuesta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
