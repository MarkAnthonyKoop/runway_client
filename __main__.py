"""CLI: `python3 -m runway_client <subcommand> …`"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import auth, generate, poll, download, batch


def _cmd_authcheck(args: argparse.Namespace) -> int:
    try:
        key = auth.get_api_key()
    except auth.MissingKey as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"key present ({len(key)} chars, ends …{key[-4:]})")
    return 0


def _cmd_setkey(args: argparse.Namespace) -> int:
    p = auth.save_api_key(args.key)
    print(f"saved → {p}")
    return 0


def _cmd_image(args: argparse.Namespace) -> int:
    task_id = generate.text_to_image(args.prompt, ratio=args.ratio)
    print(f"task {task_id} submitted")
    task = poll.wait(task_id, on_update=lambda t: print(f"  status={t.get('status')}", file=sys.stderr))
    paths = download.fetch(task, name=args.name or task_id)
    for p in paths:
        print(p)
    return 0


def _cmd_video(args: argparse.Namespace) -> int:
    task_id = generate.image_to_video(args.image, prompt=args.prompt,
                                      duration=args.duration, ratio=args.ratio)
    print(f"task {task_id} submitted")
    task = poll.wait(task_id, timeout=900,
                     on_update=lambda t: print(f"  status={t.get('status')}", file=sys.stderr))
    paths = download.fetch(task, name=args.name or task_id)
    for p in paths:
        print(p)
    return 0


def _cmd_batch(args: argparse.Namespace) -> int:
    gaps_path = Path(args.gaps_json)
    gaps = json.loads(gaps_path.read_text())
    if not isinstance(gaps, list):
        print("gaps file must be a JSON list", file=sys.stderr)
        return 2
    results = batch.fill_all(gaps)
    summary = {gid: (str(p) if isinstance(p, Path) else f"ERROR: {p}")
               for gid, p in results.items()}
    print(json.dumps(summary, indent=2))
    return 0 if all(isinstance(v, Path) for v in results.values()) else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="runway_client")
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("authcheck", help="verify an API key is discoverable")
    pa.set_defaults(func=_cmd_authcheck)

    ps = sub.add_parser("setkey", help="cache an API key to ~/.cache/runway_client/")
    ps.add_argument("key")
    ps.set_defaults(func=_cmd_setkey)

    pi = sub.add_parser("image", help="text → still image")
    pi.add_argument("prompt")
    pi.add_argument("--ratio", default="1920:1080")
    pi.add_argument("--name")
    pi.set_defaults(func=_cmd_image)

    pv = sub.add_parser("video", help="image (+ optional prompt) → motion clip")
    pv.add_argument("image", help="path, URL, or data: URI")
    pv.add_argument("--prompt", default="")
    pv.add_argument("--duration", type=int, default=5, choices=[5, 10])
    pv.add_argument("--ratio", default="1920:1080")
    pv.add_argument("--name")
    pv.set_defaults(func=_cmd_video)

    pb = sub.add_parser("batch", help="fill all GAP segments from a video_composer gaps.json")
    pb.add_argument("gaps_json")
    pb.set_defaults(func=_cmd_batch)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
