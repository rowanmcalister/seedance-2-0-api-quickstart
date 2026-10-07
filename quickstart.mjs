#!/usr/bin/env node
// Seedance 2.0 quickstart in Node.js 18+: prompt in, MP4 out. No packages.
//
//   export SEEDANCE_API_KEY=...
//   node quickstart.mjs "A red fox crosses a snowy field at dawn" [model] [resolution] [duration]

import { writeFile } from "node:fs/promises";

const key = process.env.SEEDANCE_API_KEY;
if (!key) {
  console.error("export SEEDANCE_API_KEY=... first");
  process.exit(1);
}
const base = (process.env.SEEDANCE_BASE_URL ?? "https://argolink.io/v1").replace(/\/+$/, "");
const [prompt = "A red fox crosses a snowy field at dawn, low tracking shot", model = "seedance-2.0-mini",
  resolution = "480p", duration = "5"] = process.argv.slice(2);
const pollEveryMs = Number(process.env.POLL_EVERY ?? 10) * 1000;
const headers = { Authorization: `Bearer ${key}` };

async function call(method, path, body) {
  const response = await fetch(base + path, {
    method,
    headers: body ? { ...headers, "Content-Type": "application/json" } : headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) throw new Error(`${method} ${path} failed with HTTP ${response.status}: ${await response.text()}`);
  return response;
}

// Step 1: submit -> {"request_id": "..."}
const { request_id: requestId } = await (await call("POST", "/videos/generations", {
  model, prompt, duration: Number(duration), resolution, aspect_ratio: "16:9",
})).json();
console.error(`step 1  submitted, request_id ${requestId}`);

// Step 2: poll while pending
let job;
for (;;) {
  job = await (await call("GET", `/videos/${requestId}`)).json();
  if (job.status !== "pending") break;
  console.error(`step 2  pending ${job.progress ?? 0}%`);
  await new Promise((resolve) => setTimeout(resolve, pollEveryMs));
}
if (job.status !== "done") {
  console.error(`step 2  job ${job.status} (not billed): ${JSON.stringify(job.error)}`);
  process.exit(1);
}

// Step 3: download with the same key
const video = await call("GET", `/videos/${requestId}/content`);
await writeFile("first-video.mp4", Buffer.from(await video.arrayBuffer()));
console.error("step 3  saved first-video.mp4");
console.log(JSON.stringify({ request_id: requestId, usage: job.usage }));
