"""Run quickstart.py, quickstart.sh and quickstart.mjs against a local fake of the video API.

Real HTTP on 127.0.0.1, no key and no internet. The shell test needs curl and jq,
the Node test needs node 18+; each is skipped when its tool is missing.
"""
import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


class FakeVideoAPI(BaseHTTPRequestHandler):
    jobs = {}
    log = []

    def _send(self, status, payload=None, raw=None):
        data = raw if raw is not None else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "video/mp4" if raw is not None else "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.log.append(("POST", self.path, self.headers["Authorization"], body))
        if self.path != "/v1/videos/generations":
            return self._send(404, {"error": {"code": "not_found"}})
        if body.get("resolution") == "1080p" and body.get("model") == "seedance-2.0-mini":
            return self._send(400, {"error": {"type": "invalid_request_error", "code": "request_unsupported",
                                              "message": "seedance-2.0-mini does not support video resolution 1080p"}})
        request_id = f"rq-{len(self.jobs) + 1}"
        self.jobs[request_id] = {"polls": 0, "fail": "FAIL" in body["prompt"], "seconds": body.get("duration", 5)}
        self._send(202, {"request_id": request_id})

    def do_GET(self):
        self.log.append(("GET", self.path, self.headers["Authorization"], None))
        parts = self.path.strip("/").split("/")  # v1 videos <id> [content]
        job = self.jobs.get(parts[2]) if len(parts) >= 3 else None
        if job is None:
            return self._send(404, {"error": {"code": "video_request_not_found"}})
        if len(parts) == 4:
            return self._send(200, raw=b"\x00\x00\x00\x18ftypisom-fake")
        job["polls"] += 1
        if job["polls"] == 1:
            return self._send(200, {"request_id": parts[2], "status": "pending", "progress": 35})
        if job["fail"]:
            return self._send(200, {"request_id": parts[2], "status": "failed",
                                    "error": {"code": "content_policy_violation", "message": "refused", "retryable": False}})
        seconds = job["seconds"]
        return self._send(200, {"request_id": parts[2], "status": "done", "progress": 100,
                                "usage": {"output_seconds": seconds, "reference_video_seconds": 0, "billed_seconds": seconds}})

    def log_message(self, *args):
        pass


@pytest.fixture
def api():
    FakeVideoAPI.jobs, FakeVideoAPI.log = {}, []
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeVideoAPI)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/v1"
    server.shutdown()


def run(command, base, cwd, **extra_env):
    env = {**os.environ, "SEEDANCE_API_KEY": "test-key", "SEEDANCE_BASE_URL": base, "POLL_EVERY": "0", **extra_env}
    return subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=60)


def check_success(result, out_file, seconds=5):
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout.strip().splitlines()[-1])["usage"]["billed_seconds"] == seconds
    assert out_file.read_bytes().endswith(b"ftypisom-fake")
    post = FakeVideoAPI.log[0]
    assert post[1] == "/v1/videos/generations" and post[2] == "Bearer test-key"
    assert [entry[1] for entry in FakeVideoAPI.log][-1].endswith("/content")
    return post[3]


def test_python_quickstart(api, tmp_path):
    result = run([sys.executable, str(REPO / "quickstart.py"), "a fox in snow", "--model", "seedance-2.0",
                  "--resolution", "720p", "--duration", "6", "--poll-every", "0"], api, tmp_path)
    body = check_success(result, tmp_path / "first-video.mp4", seconds=6)
    assert body == {"model": "seedance-2.0", "prompt": "a fox in snow", "duration": 6, "resolution": "720p", "aspect_ratio": "16:9"}
    assert "about $0.660" in result.stderr


def test_python_quickstart_reports_failures_and_api_errors(api, tmp_path):
    failed = run([sys.executable, str(REPO / "quickstart.py"), "FAIL please", "--poll-every", "0"], api, tmp_path)
    assert failed.returncode == 1 and "content_policy_violation" in failed.stderr
    rejected = run([sys.executable, str(REPO / "quickstart.py"), "x", "--resolution", "1080p"], api, tmp_path)
    assert rejected.returncode != 0 and "does not render 1080p" in rejected.stderr  # caught before any request


@pytest.mark.skipif(not (shutil.which("bash") and shutil.which("curl") and shutil.which("jq")), reason="needs bash, curl and jq")
def test_shell_quickstart(api, tmp_path):
    result = run(["bash", str(REPO / "quickstart.sh"), "a fox in snow"], api, tmp_path, MODEL="seedance-2.0-fast", RESOLUTION="720p")
    body = check_success(result, tmp_path / "first-video.mp4")
    assert body["model"] == "seedance-2.0-fast" and body["duration"] == 5
    assert "about $0.455" in result.stderr


@pytest.mark.skipif(not shutil.which("node"), reason="needs node")
def test_node_quickstart(api, tmp_path):
    result = run(["node", str(REPO / "quickstart.mjs"), "a fox in snow", "seedance-2.0-mini", "480p", "4"], api, tmp_path)
    body = check_success(result, tmp_path / "first-video.mp4", seconds=4)
    assert body == {"model": "seedance-2.0-mini", "prompt": "a fox in snow", "duration": 4, "resolution": "480p", "aspect_ratio": "16:9"}
