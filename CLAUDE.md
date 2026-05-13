# CLAUDE.md — runway_client

Instructions for any AI (or human) modifying this package. Read `README.md` first. Universal rules live in `~/CLAUDE.md`.

## We talk to Runway, nothing else

This package's single job: turn a prompt (and optionally a seed image) into a downloaded MP4 by way of the Runway public API. It does **not**:

- Choose prompts or rewrite them — that's the caller's job.
- Pull seed frames from existing clips — that's a future `video_frames/` sibling.
- Composite results into a timeline — that's `video_composer`.
- Pick between Runway / Pika / Luma — a future `broll_filler/` would.

When you're tempted to grow it, ask whether the new thing is *Runway-API-specific*. If not, put it in a sibling.

## API key handling — three sources, one priority

`auth.get_api_key()` checks env → `~/.cache/runway_client/api_key` → grep of `/mnt/c/z/personal/phones`. The phones-file fallback is deliberate: the user keeps every credential there. **Don't remove it.** If you add a fourth source, append it at the *end* of the chain (don't reorder — explicit env overrides should always win).

## The API version header is load-bearing

`X-Runway-Version: 2024-11-06` is set as `API_VERSION` in `api.py`. When Runway changes the wire format, you'll see 400s with body like `{"error": "Unsupported version"}`. The fix is **bump the constant**, then test all four endpoints (`/text_to_image`, `/image_to_video`, `/tasks/{id}`, and the download CDN). Don't add a version-negotiation layer; the docs publish a single supported version at a time.

## Don't reach for the `runwayml` SDK

It exists and would shorten `api.py`. But:

- It pins `pydantic` and `httpx` versions that have collided with our siblings before.
- It hides the request body, which is the first thing you want to see when debugging a 422.
- The whole reason `api.py` is 30 lines is so a `curl` reproduction is one copy-paste away.

If the API gets dramatically more complex, *then* reconsider — but the bar is "more complex than 100 lines of `requests`."

## Polling is blocking on purpose

`poll.wait` sleeps the calling thread until SUCCEEDED / FAILED / timeout. Don't add threading or asyncio inside this file. If a caller needs concurrency, the right pattern is "submit all jobs (collect ids), then poll all jobs in parallel" — and that orchestration belongs in the *caller* (or `batch.py`), not in `poll.py`.

## Duration must be 5 or 10

Runway turbo models reject other values. `batch._quantize_duration` rounds up. The downstream renderer (`video_composer`) trims the clip to the segment's actual duration, so a 7-second gap getting a 10-second clip works fine. Don't try to be clever with non-supported durations.

## Files stay small

Every file is well under 150 lines. The dependency graph is strictly bottom-up; no back-edges, no `utils.py`, `__init__.py` only re-exports.

## When something is broken, fix the root cause

- 401 → the key is wrong/missing; `authcheck` and re-set, don't catch+retry.
- 422 → the request body shape changed; update `api.py` / `generate.py`, don't sanitize the input.
- Task timeout → the model genuinely takes longer; raise the per-call `timeout`, don't loop forever.

## Documentation contract

Any behavior change updates `README.md` in the same change. New CLI subcommands go in §2 tables. New endpoints get a row in the "Request shape" table.

## Smoke test before declaring done

Without a key (offline, costs nothing):

```bash
python3 -c "import runway_client; print('import ok')"
python3 -m runway_client --help >/dev/null && echo "cli ok"

# Auth fallback chain shouldn't crash even when nothing is set:
unset RUNWAY_API_KEY
python3 -m runway_client authcheck; [ $? -eq 2 ] && echo "missing-key path ok"
```

With a key (one paid API hit, ~ a few cents):

```bash
python3 -m runway_client image "test still: a single white feather on black" --name smoke
ls /mnt/d/cache/runway_client/results/smoke.* && echo "image roundtrip ok"
```

End-to-end batch test belongs in the `theres_is_no_homeless` orchestrator's smoke test, not here.
