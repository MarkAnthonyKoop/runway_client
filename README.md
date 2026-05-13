# runway_client

Minimal client for the Runway public API, sized for one job: **filling GAP segments produced by `video_composer`** with AI-generated b-roll. Two-step flow per gap: `text_to_image` → `image_to_video` → download.

---

## 1. User manual

### Install (already done on this machine)

Pure Python; uses only `requests` (already installed). No SDK dependency — we hit the REST endpoints directly so the request shape stays visible.

Results land in `/mnt/d/cache/runway_client/results/`.

### Auth — one-time

```bash
python3 -m runway_client setkey "<your_runway_api_key>"
# → ~/.cache/runway_client/api_key (chmod 600)

python3 -m runway_client authcheck   # confirms a key is discoverable
```

The auth lookup order is **(1) `RUNWAY_API_KEY` env**, **(2) `~/.cache/runway_client/api_key`**, **(3) a `runway: <key>` line in `/mnt/c/z/personal/phones`**. Setting any one of these is enough.

### Single still

```bash
python3 -m runway_client image "Cinematic shot of empty street at dawn, 35mm" \
    --ratio 1920:1080 --name dawn_street
# prints the local MP4/PNG path on stdout
```

### Single motion clip

```bash
python3 -m runway_client video /path/to/still.png \
    --prompt "Slow zoom in, dust drifting in shaft of light" \
    --duration 5 --ratio 1920:1080 --name seg-04
```

### Batch-fill all GAP segments of an episode

```bash
python3 -m video_composer gaps episodes/ep003.md --json > /tmp/gaps.json
python3 -m runway_client batch /tmp/gaps.json
# → JSON map of gap_id → local MP4 path (or error string)
```

Plug each returned path back into the matching segment via `runway_result: <path>` in `episode.md`, then re-render with `video_composer`.

---

## 2. Reference

### CLI subcommands

`python3 -m runway_client {authcheck|setkey|image|video|batch} …`

| Subcommand | Args / flags | Notes |
| --- | --- | --- |
| `authcheck` | — | Exits 0 if a key is discoverable; 2 otherwise. |
| `setkey KEY` | — | Saves to `~/.cache/runway_client/api_key`. |
| `image PROMPT` | `--ratio`, `--name` | Runs text_to_image, polls, downloads. |
| `video IMAGE` | `--prompt`, `--duration {5,10}`, `--ratio`, `--name` | IMAGE may be a path, URL, or `data:` URI. |
| `batch GAPS_JSON` | — | GAPS_JSON is the `video_composer gaps --json` output. |

### Python API

```python
from runway_client import (
    text_to_image, image_to_video,    # submit jobs (return task id)
    status, wait,                     # poll
    fetch,                            # download outputs
    fill_gap, fill_all,               # high-level orchestration
    get_api_key, save_api_key,
    RunwayError, MissingKey,
)
```

`fill_gap(gap_dict)` is the one-call gap fill. `fill_all(list_of_gaps)` loops with per-gap error isolation.

### Request shape

All POSTs go to `https://api.dev.runwayml.com/v1` with:
```
Authorization: Bearer <key>
X-Runway-Version: 2024-11-06
Content-Type: application/json
```

| Endpoint | Body fields (we set) |
| --- | --- |
| `POST /text_to_image` | `promptText`, `model="gen4_image"`, `ratio` |
| `POST /image_to_video` | `promptImage` (URL or data URI), `promptText`, `model="gen4_turbo"`, `ratio`, `duration` (5 or 10) |
| `GET  /tasks/{id}` | — |

Models and ratios are kwargs on every function — override per call when Runway adds new ones.

### File system contract

| Path | Purpose |
| --- | --- |
| `~/.cache/runway_client/api_key` | API key, plain text, `chmod 600` |
| `/mnt/d/cache/runway_client/results/<id>.mp4` | Downloaded motion clip |
| `/mnt/d/cache/runway_client/results/<id>.png` | Downloaded still |

Results are never auto-pruned. Drop the directory to start fresh.

---

## 3. Architecture

### Module layout

```
runway_client/
├── __init__.py    re-export surface
├── __main__.py    argparse CLI
├── auth.py        API key discovery + cache
├── api.py         requests session, base URL, headers, error type
├── generate.py    text_to_image / image_to_video submitters
├── poll.py        wait-until-terminal polling
├── download.py    fetch outputs to /mnt/d
└── batch.py       fill_gap / fill_all orchestration
```

Dependency direction is strictly bottom-up:

```
__main__ ──► batch ──► generate ──► api ──► auth
                  └──► poll      ──► api
                  └──► download  ──► (requests directly; no auth needed for the CDN)
```

No back-edges. No `utils.py`. `__init__.py` only re-exports.

### Why these splits

- **`auth.py` is offline.** No network calls. Useful in isolation to *check* whether a key is present before kicking off any work.
- **`api.py` owns the wire format.** When Runway bumps `X-Runway-Version`, exactly one constant changes.
- **`generate.py` knows the two job types.** If Runway adds `audio_to_video` or `lipsync`, add a function here — not a new module.
- **`poll.py` is dumb on purpose.** It only knows "is this task in a terminal state?" That isolation makes it reusable when other Runway endpoints are added.
- **`download.py` is the only place we touch the CDN URLs.** No auth header on those — they're signed pre-signed URLs.
- **`batch.py` is pure orchestration.** ~60 lines. If you need a different orchestration (gap → still → motion → ffmpeg loudnorm → publish), copy this file and adjust; don't expand `fill_gap`.

### Future siblings, not future submodules

| If we need… | Build it as a sibling |
| --- | --- |
| Pika / Luma / Sora / Veo clients | `pika_client/`, `luma_client/`, etc. — one per provider, same `fill_gap` shape |
| Provider-agnostic gap filler | `broll_filler/` — picks a provider based on prompt or config, delegates here |
| Frame-extract helper (pull a still from a neighboring clip to seed motion) | `video_frames/` — uses ffmpeg, no API knowledge |
| Prompt rewriter (consistent style across an episode) | `prompt_studio/` — pure text; no media |

`runway_client` stays narrow: talk to Runway. The "what prompt to use" question is a different concern.

### Things to know if you're modifying this

1. **Auth lookup is intentionally permissive.** The phones-file fallback exists because the user keeps all credentials in `/mnt/c/z/personal/phones` and an explicit `runway: <key>` line is cheap to add. Don't remove it.
2. **Polling is blocking.** Each `wait()` sleeps the calling thread. For batch jobs that's fine because we submit sequentially. If you ever want concurrency, spawn jobs first (collecting ids) then poll in parallel — don't try to thread `fill_gap` directly.
3. **Don't pull in the `runwayml` SDK.** It looked nice at first but it pins library versions and obscures the request body. Keeping `requests` direct means a `curl --header ... --data '@payload.json'` reproduction is one copy-paste away when debugging.
4. **Duration is quantized.** Runway turbo models only support 5s or 10s outputs. `batch._quantize_duration` rounds up. A 7s gap becomes a 10s clip; the renderer will trim it back down because the segment's timeline duration governs.
5. **Smoke test** is in `CLAUDE.md`.

---

## 4. Next steps

Concrete additions, ordered by what the in-flight music-video work
(`bottle/`) and documentary work (`theres_is_no_homeless/`) need:

1. **Seed-image from a neighboring clip.** Today `image_to_video` seeds from
   a still we generated. For a music video we usually want continuity with
   the *previous* segment's last frame. The frame-extract is one ffmpeg call
   — but it belongs in a `video_frames/` sibling (planned in `INDEX.md`).
   Once that sibling lands, `fill_gap` should accept a `seed_from_segment:`
   pointer.
2. **Style-consistency across an episode.** Each gap gets prompted in
   isolation, so the resulting clips don't share a look. A
   `prompt_studio/` sibling (planned) would prepend an episode-level style
   sheet before every prompt. Until then, callers can hardcode a style
   suffix in their episode `.md` and `runway_prompt` lines.
3. **Provider-agnostic dispatch.** When Pika / Luma / Veo clients show up as
   siblings, `broll_filler/` (planned) should pick a provider per gap. This
   package stays Runway-only.
4. **github-readiness:**
   - Remove the `/mnt/c/z/personal/phones` fallback in `auth.py:18`. It
     leaks a personal-credentials-file path; on the public version the chain
     should be `RUNWAY_API_KEY` env → `~/.cache/runway_client/api_key` and
     nothing else.
   - Move `RESULTS_DIR` in `download.py:9` to `RUNWAY_CACHE` env var
     (default `~/.cache/runway_client/results`).
   - LICENSE, .gitignore, fixture-based test for the auth fallback chain
     (no network needed).
   - Pin `requests` in `requirements.txt`.
