#!/usr/bin/env python3
"""Fail fast unless named human approval gates are explicitly approved."""
from __future__ import annotations
import argparse
from pathlib import Path
from approval_utils import require_approved

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--approvals", type=Path, required=True)
    p.add_argument("--require", nargs="+", required=True, dest="required_gates")
    args = p.parse_args()
    try:
        require_approved(args.approvals, args.required_gates)
    except ValueError as exc:
        raise SystemExit(str(exc))
    print("approved: " + ", ".join(args.required_gates))

if __name__ == "__main__":
    main()
