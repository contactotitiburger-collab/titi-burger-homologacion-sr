#!/usr/bin/env python3
"""
run_nomina_batch.py — orquesta el batch de 10 semanas de nómina.

Para cada semana:
  1) Bajar SESAME con el robot (--from/--to)
  2) Generar Excel formato Nancy
  3) Subir a Drive convirtiendo a Google Sheet
  4) Borrar /tmp intermedio

Emite métricas al final en JSON.
"""
from __future__ import annotations
import json
import subprocess
import sys
import time
from pathlib import Path

SESAME_BOT_DIR = Path.home() / ".openclaw/scripts/sesame_bot"
NOMINA_DIR = Path.home() / ".openclaw/data/nomina"
SCRIPTS = Path.home() / ".openclaw/scripts"
DRIVE_FOLDER = "1qBpjmHZr_-F-bBo793J_7I6Q1yPWEHnU"

MES_ES = {
    5: "may", 6: "jun", 7: "jul",
}

# Semanas ISO (lun-dom) que hay que procesar
SEMANAS = [
    # (num_semana, from_YYYY-MM-DD, to_YYYY-MM-DD, human_range)
    (18, "2026-04-27", "2026-05-03", "27 abr al 3 may"),
    (19, "2026-05-04", "2026-05-10", "4 al 10 may"),
    (20, "2026-05-11", "2026-05-17", "11 al 17 may"),
    (21, "2026-05-18", "2026-05-24", "18 al 24 may"),
    (22, "2026-05-25", "2026-05-31", "25 al 31 may"),
    (23, "2026-06-01", "2026-06-07", "1 al 7 jun"),
    (24, "2026-06-08", "2026-06-14", "8 al 14 jun"),
    (25, "2026-06-15", "2026-06-21", "15 al 21 jun"),
    (26, "2026-06-22", "2026-06-28", "22 al 28 jun"),   # ya existe en Drive
    (27, "2026-06-29", "2026-07-05", "29 jun al 5 jul"),
]

# Semanas que se saltan (ya existen en Drive)
# sem 25 subida en el piloto de este mismo batch (v1). sem 26 v2 pre-existente.
SKIP_UPLOAD_SEMS = {25, 26}
PREEXISTING_LINKS = {
    25: ("1mka8GlzLpeZGyFG_0uOuyLen04LUuaToypFRo9S8qk4",
         "https://docs.google.com/spreadsheets/d/1mka8GlzLpeZGyFG_0uOuyLen04LUuaToypFRo9S8qk4/edit"),
    26: ("1zdo1lIa_Qlr3P5OHhnW5psX--jmOdwU1ZJTugZINsY4",
         "https://docs.google.com/spreadsheets/d/1zdo1lIa_Qlr3P5OHhnW5psX--jmOdwU1ZJTugZINsY4/edit"),
}


def run_cmd(cmd, cwd=None, timeout=180, capture=True):
    print(f"$ {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=cwd, timeout=timeout, capture_output=capture, text=True)
    if capture:
        # imprimir solo últimas líneas para no saturar
        if r.stdout: print(r.stdout[-500:])
        if r.stderr: print("STDERR:", r.stderr[-300:], file=sys.stderr)
    return r


def download_sesame(sem, from_date, to_date, max_retries=3):
    """Corre el robot Playwright. Retorna path si OK, None si falla."""
    out_path = NOMINA_DIR / f"sesame_export_sem{sem:02d}.xlsx"
    # Si ya existe y pesa OK, saltar la descarga (idempotencia + ahorro de logins)
    if out_path.exists() and out_path.stat().st_size > 5000:
        print(f"[SEM {sem}] Ya existe {out_path.name} ({out_path.stat().st_size/1024:.1f}KB), skip download")
        return out_path, {"ok": True, "path": str(out_path), "sizeKB": out_path.stat().st_size / 1024, "cached": True}
    for attempt in range(1, max_retries + 1):
        print(f"\n[SEM {sem}] Descarga SESAME (intento {attempt}/{max_retries}) rango {from_date}..{to_date}")
        r = subprocess.run(
            ["node", "download_sesame.js", "--from", from_date, "--to", to_date, "--sem", str(sem)],
            cwd=SESAME_BOT_DIR,
            capture_output=True, text=True, timeout=180,
        )
        # Buscar la línea JSON en stdout
        last_json = None
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith("{") and '"ok"' in line:
                try:
                    last_json = json.loads(line)
                except json.JSONDecodeError:
                    pass
        if last_json and last_json.get("ok"):
            return out_path, last_json
        print(f"   FAIL sem {sem}: rc={r.returncode} last_json={last_json}")
        print(f"   stderr: {r.stderr[-300:]}")
        if attempt < max_retries:
            wait = 60 * attempt
            print(f"   esperando {wait}s antes de reintentar...")
            time.sleep(wait)
    return None, None


def generate_nomina(sem, from_date, to_date, sesame_path):
    out_path = f"/tmp/nomina_sem{sem:02d}.xlsx"
    r = subprocess.run(
        ["python3", str(SCRIPTS / "generate_nomina_semana.py"),
         "--sem", str(sem), "--from", from_date, "--to", to_date,
         "--sesame", str(sesame_path), "--output", out_path],
        capture_output=True, text=True, timeout=60,
    )
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                data = json.loads(line)
                if data.get("ok"):
                    return out_path, data
            except json.JSONDecodeError:
                pass
    print(f"   FAIL generate sem {sem}: {r.stderr[-400:]}")
    return None, None


def upload_drive(sem, human_range, xlsx_path):
    name = f"Nómina - Semana {sem} ({human_range} 2026)"
    r = subprocess.run(
        ["python3", str(SCRIPTS / "upload_nomina_to_drive.py"),
         "--file", xlsx_path, "--name", name, "--folder", DRIVE_FOLDER,
         "--replace-existing"],
        capture_output=True, text=True, timeout=90,
    )
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                data = json.loads(line)
                if data.get("ok"):
                    return data
            except json.JSONDecodeError:
                pass
    print(f"   FAIL upload sem {sem}: {r.stderr[-300:]}")
    return None


def main():
    batch_t0 = time.time()
    results = []
    logins = 0

    for sem, from_d, to_d, human in SEMANAS:
        wk_t0 = time.time()
        rec = {
            "sem": sem, "from": from_d, "to": to_d, "human": human,
            "download_ok": False, "generate_ok": False, "upload_ok": False,
            "sesame_size_kb": None, "empleados_total": None,
            "con_fichaje": None, "sin_fichaje": None,
            "elapsed_s": None, "drive_id": None, "drive_link": None,
            "notes": [],
        }
        # 1) SESAME download
        sesame_path, dl_json = download_sesame(sem, from_d, to_d)
        if dl_json and not dl_json.get("cached"):
            logins += 1
        if not sesame_path:
            rec["notes"].append("SESAME download failed after retries")
            rec["elapsed_s"] = round(time.time() - wk_t0, 1)
            results.append(rec)
            continue
        rec["download_ok"] = True
        rec["sesame_size_kb"] = dl_json.get("sizeKB")

        # 2) Generar Excel
        xlsx_path, gen_json = generate_nomina(sem, from_d, to_d, sesame_path)
        if not xlsx_path:
            rec["notes"].append("Generate failed")
            rec["elapsed_s"] = round(time.time() - wk_t0, 1)
            results.append(rec)
            continue
        rec["generate_ok"] = True
        rec["empleados_total"] = gen_json.get("total_empleados")
        rec["con_fichaje"] = gen_json.get("con_fichaje")
        rec["sin_fichaje"] = gen_json.get("sin_fichaje")
        rec["sesame_names"] = gen_json.get("sesame_names")

        # 3) Upload (salvo semanas ya subidas / pre-existentes)
        if sem in SKIP_UPLOAD_SEMS:
            fid, flink = PREEXISTING_LINKS.get(sem, (None, None))
            rec["notes"].append("upload_skipped: ya existe en Drive")
            rec["drive_id"] = fid
            rec["drive_link"] = flink
            rec["upload_ok"] = True
        else:
            up = upload_drive(sem, human, xlsx_path)
            if up:
                rec["upload_ok"] = True
                rec["drive_id"] = up.get("id")
                rec["drive_link"] = up.get("webViewLink")

        # 4) Cleanup /tmp
        try:
            Path(xlsx_path).unlink(missing_ok=True)
        except Exception:
            pass

        rec["elapsed_s"] = round(time.time() - wk_t0, 1)
        results.append(rec)

        # Espera cortés entre semanas (no reventar SESAME)
        if sem != SEMANAS[-1][0]:
            print(f"[sleep 20s entre semanas]")
            time.sleep(20)

    total_elapsed_s = round(time.time() - batch_t0, 1)
    ok_count = sum(1 for r in results if r["upload_ok"])
    downloads_ok = sum(1 for r in results if r["download_ok"])

    summary = {
        "batch_total_s": total_elapsed_s,
        "batch_total_min": round(total_elapsed_s / 60, 1),
        "semanas_total": len(SEMANAS),
        "semanas_ok": ok_count,
        "downloads_ok": downloads_ok,
        "sesame_logins_estimated": logins,  # 1 por descarga
        "avg_per_week_s": round(total_elapsed_s / len(SEMANAS), 1),
        "results": results,
    }
    # Escribir reporte
    report_path = Path.home() / ".openclaw/data/nomina/batch_report.json"
    report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print("\n=== BATCH SUMMARY ===")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2, ensure_ascii=False))
    print(f"\nReporte completo: {report_path}")


if __name__ == "__main__":
    main()
