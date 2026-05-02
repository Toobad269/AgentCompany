const baseUrl = process.env.SMOKE_BASE_URL || "http://127.0.0.1:3000";

const checks = [
  { path: "/api/health", expect: 200 },
  { path: "/legacy/index.html", expect: 200 },
  { path: "/api/overview", expect: 200 },
  { path: "/api/chat", expect: 200 }
];

let failed = false;

for (const check of checks) {
  const url = new URL(check.path, baseUrl);
  const response = await fetch(url);
  const ok = response.status === check.expect;
  console.log(`${ok ? "OK" : "FAIL"} ${response.status} ${url}`);

  if (!ok) {
    failed = true;
  }
}

if (failed) {
  process.exit(1);
}
