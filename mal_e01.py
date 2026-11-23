#!/usr/bin/env python3
"""CLI de reproducción MAL-E01."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fibonalgge.experiment import default_corpus, pilot, run_all


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("pilot", help="ejecuta el piloto algebraico sin escribir evidencia")
    run = sub.add_parser("run", help="ejecuta piloto, corpus, trazas y validación")
    run.add_argument("--run-id", help="identificador nuevo; no reutiliza directorios")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    if args.command == "pilot":
        result = pilot(root, default_corpus())
        print(json.dumps({
            "classification": result["classification"],
            "cycles": result["algebra"]["pair_graph"]["cycles"],
            "joint_period": result["algebra"]["pair_graph"]["joint_period_lcm"],
            "maximum_transient": result["algebra"]["pair_graph"]["maximum_transient"],
            "trit_prediction": result["trit_prediction"],
            "memory_parity": {k: v for k, v in result["memory_parity"].items() if k != "hashes"},
            "acceleration": result["acceleration"],
        }, indent=2))
        return 0 if result["classification"] == "DEMONSTRATED" else 1
    result = run_all(root, args.run_id)
    print(json.dumps({
        "run_id": result["run_id"],
        "gates": result["gates"],
        "cases": [{"name": case["case"]["name"], "terminal": case["python"]["terminal"], "steps": case["python"]["steps"], "parity": case["parity"]["pass"]} for case in result["cases"]],
    }, indent=2))
    return 0 if all(result["gates"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
