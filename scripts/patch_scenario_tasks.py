"""Patch scenario.toml tasks for DMC evaluation.

This is intended for GitHub Actions manual runs (workflow_dispatch), so you can
quickly evaluate a purple agent on a smaller set of tasks without committing
changes to scenario.toml.

- If --tasks is omitted or empty, we use DEFAULT_TASKS (5 representative tasks).
- --tasks accepts:
  - Single task: walker_walk
  - Comma-separated string: cartpole_balance,reacher_easy,walker_walk
  - JSON list: ["cartpole_balance", "reacher_easy", "walker_walk"]

The script rewrites scenario.toml with the updated [config].tasks field.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Union

try:
    import tomli
except ImportError:
    import tomllib as tomli  # py>=3.11

try:
    import tomli_w
except ImportError as e:
    raise SystemExit("tomli-w is required. Install with: pip install tomli-w") from e


DEFAULT_TASKS = [
    # Classic control / dense reward
    "cartpole_balance",
    # Classic control / swing-up
    "acrobot_swingup",
    # Manipulation
    "reacher_easy",
    # Locomotion (biped)
    "walker_walk",
    # Locomotion (fast)
    "cheetah_run",
]


def parse_tasks(raw: str | None) -> Union[str, list[str]]:
    if raw is None:
        return DEFAULT_TASKS
    raw = raw.strip()
    if not raw:
        return DEFAULT_TASKS

    # Special-case: request full suite
    if raw.lower() == "all":
        return "all"

    # JSON list
    if raw.startswith("["):
        try:
            val = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON for tasks: {e}") from e
        if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
            raise ValueError("JSON tasks must be a list of strings")
        tasks = [x.strip() for x in val if x.strip()]
        if not tasks:
            raise ValueError("tasks list is empty")
        return tasks

    # Comma-separated
    if "," in raw:
        tasks = [t.strip() for t in raw.split(",") if t.strip()]
        if not tasks:
            raise ValueError("tasks list is empty")
        return tasks

    # Single task
    return [raw]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", type=Path, required=True)
    ap.add_argument("--tasks", type=str, default="")
    args = ap.parse_args()

    if not args.scenario.exists():
        print(f"Error: scenario not found: {args.scenario}", file=sys.stderr)
        return 2

    data: dict[str, Any] = tomli.loads(args.scenario.read_text())
    cfg = data.get("config")
    if cfg is None or not isinstance(cfg, dict):
        data["config"] = {}
        cfg = data["config"]

    try:
        cfg["tasks"] = parse_tasks(args.tasks)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    # Rewrite the whole file (submission artifact captures the exact config used).
    args.scenario.write_text(tomli_w.dumps(data))

    print(f"Updated [config].tasks -> {cfg['tasks']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
