#!/usr/bin/env bash
# BL-031: package single-EB bundle (Next.js static export served by FastAPI).
#
#   1. Builds the frontend with NEXT_PUBLIC_API_URL="" (same-origin /api/*).
#   2. Copies frontend/out/ -> backend/static_web/.
#   3. Guards against baked absolute localhost API URLs.
#   4. Zips backend (+static_web) into an EB application bundle, excluding
#      .venv / __pycache__ / node_modules / .next via an explicit allow-list.
#
# Usage:
#   ./scripts/package-eb.sh [APP_URL] [OUTPUT_ZIP]
#   APP_URL defaults to $APP_URL or https://EB_PLACEHOLDER.
#   Example:
#     ./scripts/package-eb.sh https://my-env.elasticbeanstalk.com eb-bundle.zip
set -euo pipefail

APP_URL="${1:-${APP_URL:-https://EB_PLACEHOLDER}}"
OUTPUT_ZIP="${2:-eb-bundle.zip}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$REPO_ROOT/frontend"
BACKEND_DIR="$REPO_ROOT/backend"
OUT_DIR="$FRONTEND_DIR/out"
STATIC_WEB_DIR="$BACKEND_DIR/static_web"

case "$OUTPUT_ZIP" in
  /*) ;; # absolute path
  *) OUTPUT_ZIP="$REPO_ROOT/$OUTPUT_ZIP" ;;
esac

echo "[package-eb] repo: $REPO_ROOT"
echo "[package-eb] app-url: $APP_URL"

# 1. Build frontend with same-origin API base (BL-031 D3).
(
  cd "$FRONTEND_DIR"
  NEXT_PUBLIC_API_URL="" NEXT_PUBLIC_APP_URL="$APP_URL" npm run build
)

# 2. Assert export output exists.
test -f "$OUT_DIR/index.html" || { echo "missing $OUT_DIR/index.html" >&2; exit 1; }
test -d "$OUT_DIR/_next" || { echo "missing $OUT_DIR/_next" >&2; exit 1; }
echo "[package-eb] export OK: index.html + _next/ present"

# 3. Leak guard: baked absolute localhost API calls must not ship.
# NOTE: the inert `DEFAULT_API = "http://127.0.0.1:8000"` fallback literal in
# lib/api.ts is intentionally still bundled (dead branch when built with
# NEXT_PUBLIC_API_URL=""), so the guard fails only on absolute *API calls*
# (`127.0.0.1:8000/api`), which prove a stale absolute base survived.
if grep -rE -q --include='*.js' --include='*.html' --include='*.json' \
    '127\.0\.0\.1:8000/api' "$OUT_DIR"; then
  grep -rE --include='*.js' --include='*.html' --include='*.json' \
    '127\.0\.0\.1:8000/api' "$OUT_DIR" | head -5
  echo "leak guard: absolute localhost API URL baked into frontend/out (rebuild with NEXT_PUBLIC_API_URL=\"\")" >&2
  exit 1
fi
INERT_COUNT=$(grep -rE --include='*.js' -c '127\.0\.0\.1:8000' "$OUT_DIR" 2>/dev/null | wc -l | tr -d ' ')
echo "[package-eb] leak guard OK (files mentioning inert DEFAULT_API literal: $INERT_COUNT)"

# 4. Clean + copy out/ -> backend/static_web/.
rm -rf "$STATIC_WEB_DIR"
mkdir -p "$STATIC_WEB_DIR"
cp -R "$OUT_DIR/." "$STATIC_WEB_DIR/"
test -f "$STATIC_WEB_DIR/index.html" || { echo "copy failed: static_web/index.html missing" >&2; exit 1; }
test -d "$STATIC_WEB_DIR/_next" || { echo "copy failed: static_web/_next missing" >&2; exit 1; }
echo "[package-eb] copied out/ -> backend/static_web/"

# 5-7. Stage allow-list, zip (zip root == EB application root), verify.
python3 - "$BACKEND_DIR" "$OUTPUT_ZIP" <<'EOF'
import sys, zipfile
from pathlib import Path

backend = Path(sys.argv[1])
out_zip = Path(sys.argv[2])
allow = ["app", "Procfile", "requirements.txt", ".ebextensions", "static_web"]
for name in allow:
    assert (backend / name).exists(), f"missing backend/{name} - cannot package"

out_zip.unlink(missing_ok=True)
excluded_dirs = {"__pycache__", ".pytest_cache", "node_modules", ".next"}
count = 0
with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
    for name in allow:
        src = backend / name
        if src.is_dir():
            for f in sorted(src.rglob("*")):
                if not f.is_file():
                    continue
                rel = f.relative_to(src)
                if any(part in excluded_dirs for part in rel.parts):
                    continue
                if f.suffix in {".pyc", ".pyo"}:
                    continue
                zf.write(f, (Path(name) / rel).as_posix())
                count += 1
        else:
            zf.write(src, name)
            count += 1

with zipfile.ZipFile(out_zip) as zf:
    entries = zf.namelist()
for required in ("static_web/index.html", "Procfile", "app/main.py"):
    assert required in entries, f"bundle missing required entry: {required}"
bad = [e for e in entries if (".venv/" in e or "__pycache__" in e
                              or "node_modules/" in e or "/.next/" in e
                              or e.endswith("/.next"))]
assert not bad, f"bundle contains excluded paths: {bad[:5]}"
assert any(e.startswith("static_web/_next/") for e in entries), \
    "bundle missing static_web/_next/ assets"
size_mb = out_zip.stat().st_size / (1024 * 1024)
print(f"[package-eb] contents OK: {len(entries)} entries "
      f"(static_web/index.html, _next assets, Procfile, app/)")
print(f"[package-eb] wrote {out_zip} ({size_mb:.2f} MB)")
EOF
