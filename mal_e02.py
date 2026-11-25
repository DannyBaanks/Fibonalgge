#!/usr/bin/env python3
"""CLI de reproducción MAL-E02: slot reutilizable de direcciones completas."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

from fibonalgge.address_slot import (
    MASK_ALL_ONES,
    build_default_targets,
    build_one_cycle,
    model_exhaustive,
    model_sequence,
    validate_one_cycle,
    wrong_store_value,
)
from fibonalgge.oracle import run_mb_ref

ROOT = Path(__file__).resolve().parent
ORIGINAL_RUNNER = Path(os.environ.get(
    "MALBOLGE_ORIGINAL_RUNNER",
    str(ROOT.parent / "MALBOLGE-MB-DATABASE" / "runners" / "malbolge-original" / "malbolge"),
)).resolve()
MB_REF = (ROOT.parent / "BolgeForge" / "mb_ref").resolve()
SCHEMA = "fibonalgge-mal-e02/v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_hashes() -> dict[str, str | None]:
    paths = {
        "fibonalgge/address_slot.py": ROOT / "fibonalgge" / "address_slot.py",
        "fibonalgge/planner.py": ROOT / "fibonalgge" / "planner.py",
        "mal_e02.py": ROOT / "mal_e02.py",
        "tests/test_address_slot.py": ROOT / "tests" / "test_address_slot.py",
        "original_planner.py": ROOT.parent / "MALBOLGE-MB-DATABASE" / "vm_malbolge" / "evidence" / "epoch_resolver_word_v1" / "plan.py",
    }
    return {name: (sha256_file(path) if path.exists() else None) for name, path in paths.items()}


def run_original(image: bytes, name: str, work: Path, max_steps: int = 100_000) -> dict:
    program = work / "programs" / f"{name}.mb"
    program.parent.mkdir(parents=True, exist_ok=True)
    program.write_bytes(image)
    if not ORIGINAL_RUNNER.exists():
        return {
            "available": False,
            "path": str(ORIGINAL_RUNNER),
            "terminal": "UNAVAILABLE",
        }
    completed = subprocess.run(
        [str(ORIGINAL_RUNNER), str(program), str(max_steps)],
        input=b"",
        capture_output=True,
        check=False,
        timeout=120,
    )
    raw_stdout = completed.stdout
    normalized = raw_stdout.rstrip(b"\n")
    stderr = completed.stderr.decode("utf-8", "backslashreplace")
    match = re.search(r"steps:\s*(\d+)\s*\|\s*status:\s*(\w+)", stderr)
    return {
        "available": True,
        "path": str(ORIGINAL_RUNNER),
        "sha256": sha256_file(ORIGINAL_RUNNER),
        "returncode": completed.returncode,
        "stdout_hex_raw": raw_stdout.hex(),
        "output_hex": normalized.hex(),
        "stderr_utf8": stderr,
        "steps": int(match.group(1)) if match else None,
        "status": match.group(2) if match else "UNKNOWN",
        "command": [str(ORIGINAL_RUNNER), str(program), str(max_steps)],
    }


def run_strict(image: bytes, name: str, work: Path, max_steps: int = 100_000) -> dict:
    program = work / "programs" / f"{name}.mb"
    if not MB_REF.exists():
        return {"available": False, "path": str(MB_REF), "terminal": "UNAVAILABLE"}
    result = run_mb_ref(MB_REF, program, b"", max_steps)
    result["available"] = True
    result["path"] = str(MB_REF)
    result["sha256"] = sha256_file(MB_REF)
    return result


def write_trace(path: Path, trace: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for event in trace:
            handle.write(json.dumps(event, sort_keys=True) + "\n")


def case_record(target: int, work: Path, *, negative: bool,
                max_steps: int = 100_000) -> dict:
    store = wrong_store_value(target) if negative else None
    built = build_one_cycle(target, store_value=store)
    report = validate_one_cycle(built, negative=negative)
    label = f"{'negative' if negative else 'positive'}_{target}"
    trace = report.pop("trace")
    write_trace(work / "traces" / f"{label}.jsonl", trace)
    original = run_original(built.image, label, work, max_steps)
    strict = run_strict(built.image, label, work, max_steps)
    return {
        "label": label,
        "kind": "negative_control" if negative else "positive",
        "target": target,
        "store_value": built.slot_value,
        "slot_addr": built.slot_addr,
        "pointer_addr": built.pointer_addr,
        "target_pointer_addr": built.target_pointer_addr,
        "return_addr": built.return_addr,
        "halt_addr": built.halt_addr,
        "sentinel_addr": built.sentinel_addr,
        "masks": list(built.masks),
        "image_bytes": len(built.image),
        "image_sha256": built.sha256,
        "expected_output_hex": f"{built.expected_output:02x}",
        "vm": {
            "ok": report["ok"],
            "checks": report["checks"],
            "terminal": report["terminal"],
            "output_hex": report["output_hex"],
            "steps": report["steps"],
            "events": report["events"],
            "first_target_event": report["first_target_event"],
            "jump_events": report["jump_events"],
            "final": report["final"],
        },
        "original_runner": original,
        "strict_mb_ref": strict,
    }


def claims_for(cases: list[dict], model: dict, sequence: dict) -> list[dict]:
    positives = [case for case in cases if case["kind"] == "positive"]
    negatives = [case for case in cases if case["kind"] == "negative_control"]
    positive_ok = all(case["vm"]["ok"] for case in positives)
    original_ok = all(
        case["original_runner"].get("returncode") == 0
        and case["original_runner"].get("output_hex") == case["expected_output_hex"]
        and case["original_runner"].get("status") == "HALTED"
        for case in positives
    )
    negative_ok = all(case["vm"]["ok"] for case in negatives)
    strict_rejected = all(
        case["strict_mb_ref"].get("terminal") == "ERROR"
        and "INVALID_OPCODE" in case["strict_mb_ref"].get("stderr_utf8", "")
        for case in cases
    )
    return [
        {
            "claim": "escritura exacta de las 59 049 palabras en el modelo de slot",
            "status": "DEMONSTRATED" if model["exact_write_ok"] else "FALSIFIED",
            "evidence": "model.exact_write_failures",
        },
        {
            "claim": "rearme del slot a 29524 para las 59 049 palabras",
            "status": "DEMONSTRATED" if model["rearm_ok"] else "FALSIFIED",
            "evidence": "model.rearm_failures",
        },
        {
            "claim": "imagen Classic real: slot con dirección completa, salto indirecto y aterrizaje en target",
            "status": "DEMONSTRATED" if positive_ok and original_ok else "NOT_DEMONSTRATED",
            "evidence": "positive cases + runner C original",
        },
        {
            "claim": "el incremento de c y el cifrado de la celda de aterrizaje se observan en la traza",
            "status": "DEMONSTRATED" if positive_ok else "NOT_DEMONSTRATED",
            "evidence": "vm.jump_events / checks",
        },
        {
            "claim": "un valor de slot incorrecto aterriza fuera de target",
            "status": "DEMONSTRATED" if negative_ok else "NOT_DEMONSTRATED",
            "evidence": "negative cases",
        },
        {
            "claim": "rearme y repetición de saltos dentro de la misma imagen",
            "status": "NOT_DEMONSTRATED",
            "evidence": "sólo model_sequence; no hay imagen de dos ciclos",
        },
        {
            "claim": "composición con los dos slots de retorno de P12",
            "status": "NOT_DEMONSTRATED",
            "evidence": "diseño pendiente; no se ejecutó P12 con el slot nuevo",
        },
        {
            "claim": "el cargador estricto de mb_ref acepta la imagen con celdas de dato no-opcode",
            "status": "FALSIFIED" if strict_rejected else "NOT_DEMONSTRATED",
            "evidence": "strict_mb_ref INVALID_OPCODE; se usa el runner C original",
        },
        {
            "claim": "modelo global reducido de ejecución",
            "status": "NOT_DEMONSTRATED",
            "evidence": "sin cambios respecto de MAL-E01",
        },
    ]


def build_report(run_id: str) -> tuple[dict, dict, dict]:
    targets = build_default_targets()
    model = model_exhaustive()
    sequence = model_sequence(targets)
    work = ROOT / "evidence" / run_id
    work.mkdir(parents=True, exist_ok=False)
    cases = []
    for target in targets:
        cases.append(case_record(target, work, negative=False))
    for target in targets:
        cases.append(case_record(target, work, negative=True))
    claims = claims_for(cases, model, sequence)
    report = {
        "schema": SCHEMA,
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version,
            "root": str(ROOT),
            "original_runner": str(ORIGINAL_RUNNER),
            "original_runner_sha256": sha256_file(ORIGINAL_RUNNER) if ORIGINAL_RUNNER.exists() else None,
            "mb_ref": str(MB_REF),
            "mb_ref_sha256": sha256_file(MB_REF) if MB_REF.exists() else None,
            "git_head": subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                check=False,
            ).stdout.strip(),
            "sources": source_hashes(),
        },
        "question": (
            "¿Puede un slot Classic almacenar una dirección completa de diez trits, "
            "restaurarla, usarla como destino indirecto con el incremento de c y el "
            "cifrado del aterrizaje, y rearmarse para otro destino?"
        ),
        "scope": {
            "language": "Classic Malbolge de 59 049 palabras de diez trits",
            "one_cycle_image": True,
            "same_image_repetition": False,
            "p12_composition": False,
            "strict_mb_ref_loader": False,
        },
        "targets": list(targets),
        "mask": MASK_ALL_ONES,
        "model": model,
        "model_sequence": sequence,
        "cases": cases,
        "claims": claims,
        "limitations": [
            "La imagen de un ciclo no rearma el slot después del retorno: el retorno termina en HALT.",
            "El modelo de secuencia demuestra la aritmética de escribir/aterrizar/rearmar, no una imagen de dos ciclos.",
            "mb_ref rechaza la imagen en carga porque exige que toda celda fuente sea un opcode válido; el runner C original y la VM instrumentada sí la ejecutan.",
            "No se conectó todavía el slot a la pila de dos slots de P12.",
        ],
    }
    cases_json = {
        "schema": SCHEMA,
        "run_id": run_id,
        "model": model,
        "model_sequence": sequence,
        "cases": [
            {k: v for k, v in case.items() if k not in ("vm", "original_runner", "strict_mb_ref")}
            for case in cases
        ],
        "case_status": [
            {
                "label": case["label"],
                "kind": case["kind"],
                "vm_ok": case["vm"]["ok"],
                "terminal": case["vm"]["terminal"],
                "output_hex": case["vm"]["output_hex"],
                "original_runner_status": case["original_runner"].get("status"),
                "strict_mb_ref_status": case["strict_mb_ref"].get("terminal"),
            }
            for case in cases
        ],
    }
    return report, cases_json, {"work": work, "cases": cases}


def run(run_id: str) -> int:
    evidence = ROOT / "evidence" / run_id
    if evidence.exists():
        raise SystemExit(f"el directorio de evidencia ya existe: {evidence}")
    report, cases_json, meta = build_report(run_id)
    work = meta["work"]
    (work / "RESULTS.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (work / "cases.json").write_text(json.dumps(cases_json, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (ROOT / "RESULTS_MAL_E02.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "hash_run.py"), str(work)],
        capture_output=True, text=True, check=False,
    )
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr, file=sys.stderr)
        return completed.returncode
    print(f"run_id={run_id}")
    for case in meta["cases"]:
        print(f"{case['label']}: vm={case['vm']['terminal']} out={case['vm']['output_hex']} "
              f"c_runner={case['original_runner'].get('status')} "
              f"strict={case['strict_mb_ref'].get('terminal')}")
    print(f"evidence={work}")
    print(f"claims={len(report['claims'])}")
    return 0


def pilot() -> int:
    model = model_exhaustive()
    sequence = model_sequence(build_default_targets())
    print(json.dumps({
        "domain": model["domain"],
        "exact_write_ok": model["exact_write_ok"],
        "rearm_ok": model["rearm_ok"],
        "sequence_ok": sequence["all_ok"],
        "targets": list(build_default_targets()),
    }, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("pilot", help="modelo exhaustivo sin escribir evidencia")
    run_parser = sub.add_parser("run", help="genera imágenes, ejecuta VM y runner C, y escribe evidencia")
    run_parser.add_argument("--run-id", required=True, help="identificador nuevo; no reutiliza directorios")
    args = parser.parse_args()
    if args.command == "pilot":
        return pilot()
    return run(args.run_id)


if __name__ == "__main__":
    raise SystemExit(main())
