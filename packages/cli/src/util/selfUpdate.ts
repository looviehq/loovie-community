import { log } from "./log.js";

const REGISTRY = "https://registry.npmjs.org/@loovie/mcp/latest";

/** Compare two dot-separated semver prerelease tails per SemVer §11: numeric
 *  identifiers compare numerically (so `beta.10` > `beta.9`), numeric ranks
 *  below non-numeric, and a shorter set ranks below a longer one with the same
 *  prefix. Returns -1, 0, or 1. An empty tail (a stable release) is handled by
 *  the caller, not here. */
function comparePre(a: string, b: string): number {
  const ai = a.split(".");
  const bi = b.split(".");
  const len = Math.max(ai.length, bi.length);
  for (let i = 0; i < len; i++) {
    const x = ai[i];
    const y = bi[i];
    if (x === undefined) return -1; // a ran out first → lower precedence
    if (y === undefined) return 1;
    const xn = /^\d+$/.test(x);
    const yn = /^\d+$/.test(y);
    if (xn && yn) {
      const d = parseInt(x, 10) - parseInt(y, 10);
      if (d !== 0) return d < 0 ? -1 : 1;
    } else if (xn !== yn) {
      return xn ? -1 : 1; // numeric identifiers rank below alphanumeric
    } else if (x !== y) {
      return x < y ? -1 : 1;
    }
  }
  return 0;
}

/** Compare two dotted semver-ish strings. Returns true if `latest` > `current`.
 *  Best-effort: the numeric core is compared field-by-field, then the
 *  prerelease tail per SemVer precedence rules. */
export function isNewer(latest: string, current: string): boolean {
  const split = (v: string) => {
    const [core = "", pre = ""] = v.replace(/^v/, "").split("-", 2);
    return { nums: core.split(".").map((n) => parseInt(n, 10) || 0), pre };
  };
  const a = split(latest);
  const b = split(current);
  const len = Math.max(a.nums.length, b.nums.length);
  for (let i = 0; i < len; i++) {
    const x = a.nums[i] ?? 0;
    const y = b.nums[i] ?? 0;
    if (x !== y) return x > y;
  }
  // Equal numeric core: a release (no prerelease) outranks a prerelease.
  if (a.pre === b.pre) return false;
  if (!a.pre) return !!b.pre;
  if (!b.pre) return false;
  return comparePre(a.pre, b.pre) > 0;
}

/**
 * Best-effort check against the npm registry for a newer release. Never blocks:
 * a short timeout caps the wait and any failure (offline, registry hiccup) is
 * swallowed silently. Returns a notice string to print at the end of the run,
 * or null. Suppressed by LOOVIE_NO_UPDATE_CHECK to keep CI / scripts quiet.
 */
export async function checkForUpdate(current: string, timeoutMs = 1500): Promise<string | null> {
  if (process.env.LOOVIE_NO_UPDATE_CHECK) return null;
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    const res = await fetch(REGISTRY, {
      signal: ctrl.signal,
      headers: { accept: "application/vnd.npm.install-v1+json" },
    });
    clearTimeout(timer);
    if (!res.ok) return null;
    const body = (await res.json()) as { version?: unknown };
    const latest = typeof body.version === "string" ? body.version : null;
    if (latest && isNewer(latest, current)) {
      return `A new version of @loovie/mcp is available (${current} → ${latest}). Run \`npx -y @loovie/mcp@latest update\` to refresh.`;
    }
  } catch {
    /* offline / timeout / parse error — stay silent */
  }
  return null;
}

/** Run the check in the background and print a dim one-liner at the very end. */
export async function printUpdateNoticeIfAny(current: string): Promise<void> {
  const notice = await checkForUpdate(current);
  if (notice) log.dim(notice);
}
