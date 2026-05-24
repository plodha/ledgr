// apps/web/src/app/page.tsx
// Server Component (default in App Router). Async function signature is the
// Next 16 idiom — `params`, `cookies()`, `headers()` are all async, but this
// placeholder uses none of them.

interface Health {
  status: string;
  version: string;
  environment: string;
  db_connected: boolean;
}

async function getHealth(): Promise<Health | null> {
  // In Docker, the web container reaches the api by service name (API_URL_INTERNAL).
  // For local dev outside Docker, fall back to NEXT_PUBLIC_API_URL (set to
  // http://localhost:8000 in .env.example).
  const base =
    process.env.API_URL_INTERNAL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "http://localhost:8000";
  const url = `${base}/health`;
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as Health;
  } catch {
    // CLAUDE.md line 147: "If API is unreachable, show 'API unavailable' gracefully — no crash."
    return null;
  }
}

export default async function Page() {
  const health = await getHealth();
  return (
    <main className="min-h-screen flex items-center justify-center p-8">
      <div className="max-w-md w-full text-center space-y-4">
        <h1 className="text-3xl font-bold">
          Personal Resource &amp; Asset Navigator for Abundant Value
        </h1>
        <p className="text-sm opacity-70">Coming soon.</p>
        <div className="mt-8 p-4 border rounded text-left text-sm font-mono">
          {health ? (
            <pre>{JSON.stringify(health, null, 2)}</pre>
          ) : (
            <span className="opacity-70">API unavailable</span>
          )}
        </div>
      </div>
    </main>
  );
}
