# Seedance 2.0 API Quickstart — $0.053/s at 480p, first clip in five minutes

**ByteDance Seedance 2.0 is live on [ArgoLink](https://argolink.io/gh-seedance-2-0-api-quickstart)**: $0.053/s at 480p and $0.11/s at 720p (1080p $0.28/s, 4K $0.58/s), about 25% below the official price; the Mini variant used for the first test below is $0.026/s. This quickstart goes from an API key to a finished MP4 in three HTTP calls, and shows the exact response you should see at each step.

[Seedance 2.0 model page →](https://argolink.io/en/models/seedance-2.0) · [Run it](#five-minute-run) · [The three calls](#the-three-calls) · [Modes](#generation-modes) · [First-run errors](#first-run-errors)

<sub>Last checked: 2026-10-07 against the model pages and API docs linked below.</sub>

## What you need

- an API key from the [ArgoLink console](https://argolink.io/en/models/seedance-2.0), exported as `SEEDANCE_API_KEY`
- one of: `curl` + `jq`, Python 3.8+, or Node.js 18+ (no packages for any of them)

## Five-minute run

```bash
git clone https://github.com/rowanmcalister/seedance-2-0-api-quickstart && cd seedance-2-0-api-quickstart
export SEEDANCE_API_KEY=your-key
./quickstart.sh "A red fox crosses a snowy field at dawn, low tracking shot"
```

```text
step 0  seedance-2.0-mini, 5 s at 480p: about $0.13
step 1  submitted, request_id 6b1f0e2a-41c8-4d55-9f0e-2c7d1e93a5b0
step 2  pending 0%
step 2  pending 42%
step 2  pending 87%
step 3  saved first-video.mp4
{"request_id":"6b1f0e2a-41c8-4d55-9f0e-2c7d1e93a5b0","usage":{"billed_seconds":5,"output_seconds":5,"reference_video_seconds":0}}
```

The first test runs on `seedance-2.0-mini` at 480p to keep it cheap. Change it with environment variables: `MODEL=seedance-2.0 RESOLUTION=1080p DURATION=8 ./quickstart.sh "…"`. The same flow in other languages:

```bash
python quickstart.py "A red fox crosses a snowy field at dawn" --model seedance-2.0 --resolution 720p
node quickstart.mjs "A red fox crosses a snowy field at dawn" seedance-2.0-fast 720p 6
```

## The three calls

All calls go to `https://argolink.io/v1` with `Authorization: Bearer $SEEDANCE_API_KEY`. Step 0 is optional and needs no key.

### Step 0: confirm the model IDs

```bash
curl -s https://argolink.io/v1/models | jq -r '.data[].id' | grep seedance-2.0
```

```text
seedance-2.0-fast
seedance-2.0
seedance-2.0-mini
```

### Step 1: submit the job

```bash
curl https://argolink.io/v1/videos/generations \
  -H "Authorization: Bearer $SEEDANCE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "seedance-2.0-mini", "prompt": "A red fox crosses a snowy field at dawn, low tracking shot", "duration": 5, "resolution": "480p", "aspect_ratio": "16:9"}'
```

Answer: HTTP 202 with `{"request_id": "6b1f0e2a-41c8-4d55-9f0e-2c7d1e93a5b0"}`. Keep the ID: it is the only handle for the status, the download and the billing record, and it only works with the key that created it.

### Step 2: poll the status

```bash
curl https://argolink.io/v1/videos/$REQUEST_ID -H "Authorization: Bearer $SEEDANCE_API_KEY"
```

While the video renders (poll every 10–15 seconds):

```json
{"request_id": "6b1f0e2a-…", "status": "pending", "model": "seedance-2.0-mini", "created_at": 1791377410, "progress": 42, "estimated_seconds_remaining": 71}
```

When it is ready:

```json
{
  "request_id": "6b1f0e2a-…",
  "status": "done",
  "model": "seedance-2.0-mini",
  "progress": 100,
  "usage": {"output_seconds": 5, "reference_video_seconds": 0, "billed_seconds": 5},
  "video": {"duration": 5, "url": "https://argolink.io/v1/videos/6b1f0e2a-…/content"}
}
```

If it could not be made (nothing is charged):

```json
{"request_id": "6b1f0e2a-…", "status": "failed", "model": "seedance-2.0-mini",
 "error": {"code": "invalid_input", "message": "…", "retryable": false, "field": "start_image"}}
```

| Status | Means | Next |
|---|---|---|
| `pending` | queued or rendering; `progress` 0–99 | poll again |
| `done` | MP4 ready; `usage.billed_seconds` is the bill | download |
| `failed` | no video; `error.retryable` says whether resending is safe | fix `error.field` or resend |
| `expired` | no video | submit again |

### Step 3: download

```bash
curl -L https://argolink.io/v1/videos/$REQUEST_ID/content -H "Authorization: Bearer $SEEDANCE_API_KEY" -o first-video.mp4
```

`video.url` from step 2 is this same address. It needs your key, so a browser or `<video>` tag cannot open it directly: download the file and serve your copy. Before `done` the endpoint answers `409 job_video_not_ready`; for a failed job, `424 job_failed`.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/v1/models` | public model list, no key needed |
| `POST` | `/v1/videos/generations` | create a job (202 + `request_id`) |
| `GET` | `/v1/videos/{request_id}` | job status, progress, usage |
| `GET` | `/v1/videos/{request_id}/content` | the MP4 |
| `POST` | `/v1/media/uploads` | upload ticket for a local image, video or audio file |

## Models and the price of a 5-second clip

| Model | Resolutions | 5 s at 480p | 5 s at 720p | 5 s at 1080p | 5 s at 4K |
|---|---|---:|---:|---:|---:|
| `seedance-2.0-mini` | 480p, 720p | $0.13 | $0.285 | — | — |
| `seedance-2.0-fast` | 480p, 720p | $0.21 | $0.455 | — | — |
| `seedance-2.0` | 480p–4K | $0.265 | $0.55 | $1.40 | $2.90 |

<sub>ArgoLink per-second rates × 5, from the [2.0](https://argolink.io/en/models/seedance-2.0), [Fast](https://argolink.io/en/models/seedance-2.0-fast) and [Mini](https://argolink.io/en/models/seedance-2.0-mini) pages on 2026-10-07. For comparison, BytePlus's own 5-second, 16:9 examples for Seedance 2.0 are $0.35, $0.76, $1.87 and $3.89 ([ModelArk pricing](https://docs.byteplus.com/en/docs/modelark/model-pricing), same day).</sub>

A job without `duration` renders and bills 5 seconds; failed and expired jobs cost nothing.

## Generation modes

Every mode is the same call; the fields in the body choose it.

| Mode | Add to the body | Notes |
|---|---|---|
| Text to video | nothing beyond `prompt` | `aspect_ratio` one of 21:9, 16:9, 4:3, 1:1, 3:4, 9:16 |
| First frame | `"start_image": {"url": "https://…"}` | `"aspect_ratio": "adaptive"` follows the image |
| First + last frame | `start_image` + `"end_image": {"url": "https://…"}` | the model animates between them |
| Reference | `"reference_images"`, `"reference_videos"`, `"reference_audios"`: lists of `{"url": …}` | name them as `@Image 1`, `@Video 1`, `@Audio 1`; up to 9 / 3 / 3 |

```json
{
  "model": "seedance-2.0",
  "prompt": "The cat in @Image 1 naps on the windowsill from @Image 2 as rain streaks the glass",
  "duration": 6,
  "resolution": "720p",
  "reference_images": [{"url": "https://example.com/cat.png"}, {"url": "https://example.com/windowsill.jpg"}]
}
```

Media must be public HTTPS URLs. For a local file, `POST /v1/media/uploads` with `{"model", "type", "content_type", "size_bytes"}`, `PUT` the bytes to the returned `upload_url`, then send the returned `media_url`.

## Parameters

| Field | Default | Allowed |
|---|---|---|
| `model` | — | `seedance-2.0`, `seedance-2.0-fast`, `seedance-2.0-mini` |
| `prompt` | — | required in every mode |
| `duration` | 5 | 4–15 (integer seconds) |
| `resolution` | `720p` | `480p`, `720p`; `1080p`, `4k` on `seedance-2.0` only |
| `aspect_ratio` | `16:9` | six fixed ratios; `adaptive` with frames only |
| `generate_audio` | `true` | `false` for a silent video |

`seed`, `watermark: true` and `n` above 1 are rejected.

## First-run errors

| You see | Cause | Fix |
|---|---|---|
| `401` | key missing, mistyped or revoked | `echo ${#SEEDANCE_API_KEY}` should print a length; create a new key if needed |
| `402` or `403` | balance too low, or the key's group has no video access | top up, or use a key that can call video models |
| `400 request_unsupported` | a combination the model refuses: `1080p` on Mini, 16 s, a `seed` | pick a supported value; the message names it |
| `400` with `adaptive` | `adaptive` sent in a text or reference request | use a fixed ratio there |
| `404 video_request_not_found` | typo in the ID, or a different key | poll with the key that submitted the job |
| `409 job_video_not_ready` | downloaded before `done` | keep polling |
| `429` | too many jobs at once | wait for running jobs to finish |
| `503` | no capacity at the moment | retry after the `Retry-After` header; nothing is charged |

## FAQ

**Do I need an SDK?**
No. The API is three JSON-over-HTTPS calls, which is why all three quickstarts here use only built-in libraries.

**Is there a webhook instead of polling?**
The API docs describe polling only. Ten to fifteen seconds between polls is the documented pace; a 5-second clip usually takes a few minutes.

**What happens if my script stops while the job is pending?**
Nothing is lost. The job keeps running; poll the same `request_id` later and download it.

**Why did my first-frame video come out in a different shape?**
With `adaptive`, the video takes whichever of the six ratios is closest to your image. Send a fixed ratio such as `9:16` to crop the image to that shape instead.

## Tests

```bash
pip install pytest && pytest
```

The tests start a fake video API on `127.0.0.1` and run all three quickstarts against it: no key, no internet.

## License

MIT
