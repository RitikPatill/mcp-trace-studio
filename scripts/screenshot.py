"""
Capture a 1280×800 screenshot of the MCP Trace Studio waterfall timeline.

Requirements:
    uv run --with playwright python scripts/screenshot.py
    # Or, if playwright is already in the backend venv:
    cd backend && uv run python ../scripts/screenshot.py

The backend (port 8000) and frontend (port 3000) must already be running,
and the DB must have at least one completed run (run `just demo` first).

Standalone — no imports from backend/app/.
"""

import asyncio
import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).parent.parent
_DEFAULT_OUT = _REPO_ROOT / "docs" / "screenshot.png"


async def main(out: Path = _DEFAULT_OUT) -> None:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print(
            "ERROR: playwright is not installed.\n"
            "  Run: cd backend && uv sync && uv run playwright install chromium",
            file=sys.stderr,
        )
        sys.exit(1)

    out.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        # ------------------------------------------------------------------ #
        # 1. Runs list page — wait for at least one run row
        # ------------------------------------------------------------------ #
        print("Opening http://localhost:3000/runs …")
        await page.goto("http://localhost:3000/runs", wait_until="networkidle")

        try:
            await page.wait_for_selector('[data-testid="run-row"]', timeout=15_000)
        except Exception:
            print(
                "WARNING: no run rows found within 15 s — "
                "make sure `just demo` has been run and the backend is healthy.",
                file=sys.stderr,
            )
            await browser.close()
            sys.exit(1)

        # ------------------------------------------------------------------ #
        # 2. Click the first run row to open the detail / waterfall page
        # ------------------------------------------------------------------ #
        print("Clicking first run row…")
        first_row = page.locator('[data-testid="run-row"]').first
        await first_row.click()

        # ------------------------------------------------------------------ #
        # 3. Wait for the waterfall timeline to render
        # ------------------------------------------------------------------ #
        print("Waiting for waterfall timeline…")
        try:
            await page.wait_for_selector(
                '[data-testid="waterfall-timeline"]', timeout=15_000
            )
        except Exception:
            print(
                "WARNING: waterfall-timeline not found — "
                "screenshot will show whatever is currently visible.",
                file=sys.stderr,
            )

        # Small extra wait for animations / data fetches to settle
        await asyncio.sleep(1)

        # ------------------------------------------------------------------ #
        # 4. Take the screenshot
        # ------------------------------------------------------------------ #
        await page.screenshot(path=str(out), full_page=False)
        await browser.close()

    # Sanity check
    assert out.exists() and out.stat().st_size > 10_000, (
        f"Screenshot at {out} looks corrupt or too small "
        f"({out.stat().st_size if out.exists() else 0} bytes)."
    )
    print(f"Screenshot saved: {out}  ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
