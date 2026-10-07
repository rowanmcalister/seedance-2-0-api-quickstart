#!/usr/bin/env python3
"""Seedance 2.0 quickstart in Python: prompt in, MP4 out. Standard library only.

    export SEEDANCE_API_KEY=...
    python quickstart.py "A red fox crosses a snowy field at dawn" --model seedance-2.0 --resolution 720p
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

USER_AGENT = "seedance-2-0-api-quickstart/1.0"
RATES = {  # USD per output second, 2026-10-07
    "seedance-2.0": {"480p": 0.053, "720p": 0.11, "1080p": 0.28, "4k": 0.58},
    "seedance-2.0-fast": {"480p": 0.042, "720p": 0.091},
    "seedance-2.0-mini": {"480p": 0.026, "720p": 0.057},
}


def call(base, key, method, path, body=None, raw=False):
    request = urllib.request.Request(base + path, method=method, data=json.dumps(body).encode() if body else None)
    request.add_header("Authorization", f"Bearer {key}")
    request.add_header("User-Agent", USER_AGENT)
    if body:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = response.read()
    except urllib.error.HTTPError as error:
        sys.exit(f"{method} {path} failed with HTTP {error.code}: {error.read().decode(errors='replace')}")
    return data if raw else json.loads(data)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate one Seedance 2.0 video.")
    parser.add_argument("prompt", nargs="?", default="A red fox crosses a snowy field at dawn, low tracking shot")
    parser.add_argument("--model", default="seedance-2.0-mini", choices=sorted(RATES))
    parser.add_argument("--resolution", default="480p")
    parser.add_argument("--duration", type=int, default=5, help="4-15 seconds")
    parser.add_argument("--ratio", default="16:9")
    parser.add_argument("--out", default="first-video.mp4")
    parser.add_argument("--poll-every", type=float, default=10)
    args = parser.parse_args(argv)

    key = os.environ.get("SEEDANCE_API_KEY") or sys.exit("export SEEDANCE_API_KEY=... first")
    base = os.environ.get("SEEDANCE_BASE_URL", "https://argolink.io/v1").rstrip("/")
    rate = RATES[args.model].get(args.resolution) or sys.exit(f"{args.model} does not render {args.resolution}")
    print(f"step 0  {args.model}, {args.duration} s at {args.resolution}: about ${rate * args.duration:.3f}", file=sys.stderr)

    # Step 1: submit -> {"request_id": "..."}
    request_id = call(base, key, "POST", "/videos/generations", {
        "model": args.model, "prompt": args.prompt, "duration": args.duration,
        "resolution": args.resolution, "aspect_ratio": args.ratio,
    })["request_id"]
    print(f"step 1  submitted, request_id {request_id}", file=sys.stderr)

    # Step 2: poll while pending
    while True:
        job = call(base, key, "GET", f"/videos/{request_id}")
        if job["status"] != "pending":
            break
        print(f"step 2  pending {job.get('progress', 0)}%", file=sys.stderr)
        time.sleep(args.poll_every)
    if job["status"] != "done":
        print(f"step 2  job {job['status']} (not billed): {json.dumps(job.get('error'))}", file=sys.stderr)
        return 1

    # Step 3: download with the same key
    with open(args.out, "wb") as handle:
        handle.write(call(base, key, "GET", f"/videos/{request_id}/content", raw=True))
    print(f"step 3  saved {args.out}", file=sys.stderr)
    print(json.dumps({"request_id": request_id, "usage": job.get("usage")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
