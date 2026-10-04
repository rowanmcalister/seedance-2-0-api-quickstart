# seedance-2.0 on Argolink

This document is the concrete request contract for `seedance-2.0` on Argolink. It keeps the request lifecycle explicit so clients do not confuse submission, status, and content retrieval.

## Contract summary

| Item | Argolink contract |
| --- | --- |
| Base URL | `https://api.argolink.io` |
| Authentication | `Authorization: Bearer $ARGOLINK_API_KEY` |
| Submit | `POST /v1/videos/generations` |
| Poll | `GET /v1/videos/{request_id}` |
| Download | `GET /v1/videos/{request_id}/content` |
| Duration | 4–15 seconds |
| Resolution | 720p, 1080p, 4K |
| References | up to 9 images, 3 videos, 3 audio tracks; 12 assets total |
| Modes | text, image, reference, and first/last frame |

## Submit, poll, download

```bash
export ARGOLINK_API_KEY='replace-me'
BASE='https://api.argolink.io'

REQUEST_ID=$(curl -fsS "$BASE/v1/videos/generations" \
  -H "Authorization: Bearer $ARGOLINK_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "seedance-2.0",
    "prompt": "A calm product film with a slow camera move and clean natural sound",
    "duration": 6,
    "resolution": "720p",
    "aspect_ratio": "16:9"
  }' | jq -er '.request_id')

while :; do
  STATUS=$(curl -fsS "$BASE/v1/videos/$REQUEST_ID" \
    -H "Authorization: Bearer $ARGOLINK_API_KEY")
  STATE=$(jq -r '.status' <<<"$STATUS")
  case "$STATE" in
    done) break ;;
    failed|expired) jq . <<<"$STATUS" >&2; exit 1 ;;
    pending|running) sleep 5 ;;
    *) echo "unexpected status: $STATE" >&2; exit 1 ;;
  esac
done

curl -fL "$BASE/v1/videos/$REQUEST_ID/content" \
  -H "Authorization: Bearer $ARGOLINK_API_KEY" -o output.mp4
```

## Media inputs

Local files must be uploaded through the documented Argolink media-ticket flow first. The generation JSON then carries the returned HTTPS `media_url`; do not put multipart bytes or base64 data in the video JSON request. Name assets in the prompt consistently (`image 1`, `video 1`, `audio 1`) when the model supports references.

## Failure handling

- `pending` and `running` are retryable states; use bounded polling with backoff.
- `failed` and `expired` are terminal; preserve the error object and do not download as if it were media.
- Retry a submission only with an idempotency strategy owned by the calling application.
- Recheck the live model page for accepted combinations before sending optional fields.
