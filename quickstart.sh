#!/usr/bin/env bash
# Seedance 2.0 quickstart: prompt in, MP4 out, in three HTTP calls. Needs curl and jq.
#
#   export SEEDANCE_API_KEY=...
#   ./quickstart.sh "A red fox crosses a snowy field at dawn, low tracking shot"
#
# Optional: MODEL (seedance-2.0 | seedance-2.0-fast | seedance-2.0-mini), RESOLUTION,
# DURATION (4-15), RATIO, OUT, POLL_EVERY (seconds), SEEDANCE_BASE_URL.
set -euo pipefail

: "${SEEDANCE_API_KEY:?export SEEDANCE_API_KEY=... first}"
BASE="${SEEDANCE_BASE_URL:-https://argolink.io/v1}"
PROMPT="${1:-A red fox crosses a snowy field at dawn, low tracking shot, soft breath clouds}"
MODEL="${MODEL:-seedance-2.0-mini}"
RESOLUTION="${RESOLUTION:-480p}"
DURATION="${DURATION:-5}"
RATIO="${RATIO:-16:9}"
OUT="${OUT:-first-video.mp4}"
POLL_EVERY="${POLL_EVERY:-10}"
AUTH="Authorization: Bearer $SEEDANCE_API_KEY"

# Per-second rates on 2026-10-07; the job's usage.billed_seconds is the real bill.
case "$MODEL/$RESOLUTION" in
  seedance-2.0/480p) RATE=0.053 ;; seedance-2.0/720p) RATE=0.11 ;;
  seedance-2.0/1080p) RATE=0.28 ;; seedance-2.0/4k) RATE=0.58 ;;
  seedance-2.0-fast/480p) RATE=0.042 ;; seedance-2.0-fast/720p) RATE=0.091 ;;
  seedance-2.0-mini/480p) RATE=0.026 ;; seedance-2.0-mini/720p) RATE=0.057 ;;
  *) echo "$MODEL does not render $RESOLUTION" >&2; exit 2 ;;
esac
echo "step 0  $MODEL, $DURATION s at $RESOLUTION: about \$$(jq -n "$RATE * $DURATION * 1000 | round / 1000")" >&2

# Step 1: submit. 202 Accepted with {"request_id": "..."}
BODY=$(jq -n --arg model "$MODEL" --arg prompt "$PROMPT" --arg res "$RESOLUTION" --arg ratio "$RATIO" \
  --argjson duration "$DURATION" \
  '{model: $model, prompt: $prompt, duration: $duration, resolution: $res, aspect_ratio: $ratio}')
REQUEST_ID=$(curl -fsS "$BASE/videos/generations" -H "$AUTH" -H "Content-Type: application/json" -d "$BODY" |
  jq -er .request_id)
echo "step 1  submitted, request_id $REQUEST_ID" >&2

# Step 2: poll until the status is no longer "pending"
while :; do
  JOB=$(curl -fsS "$BASE/videos/$REQUEST_ID" -H "$AUTH")
  STATUS=$(jq -r .status <<<"$JOB")
  [ "$STATUS" = pending ] || break
  echo "step 2  pending $(jq -r '.progress // 0' <<<"$JOB")%" >&2
  sleep "$POLL_EVERY"
done
if [ "$STATUS" != done ]; then
  echo "step 2  job $STATUS (not billed):" >&2
  jq '.error // .' <<<"$JOB" >&2
  exit 1
fi

# Step 3: download the MP4 with the same key
curl -fsSL "$BASE/videos/$REQUEST_ID/content" -H "$AUTH" -o "$OUT"
echo "step 3  saved $OUT" >&2
jq -c '{request_id, usage}' <<<"$JOB"
