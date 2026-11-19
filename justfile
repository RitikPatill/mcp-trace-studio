# MCP Trace Studio – task runner
# Install just: https://just.systems/

# Print help when no recipe is specified
default:
    @echo "MCP Trace Studio"
    @echo ""
    @echo "Available recipes:"
    @echo "  just backend   Start the FastAPI backend (port 8000)"
    @echo "  just frontend  Start the Next.js frontend (port 3000)"
    @echo "  just dev       Print quickstart instructions"
    @echo "  just test      Run backend tests"
    @echo "  just lint      Lint and format backend code"
    @echo "  just demo      Populate DB with example traces"

# Start the FastAPI backend in reload mode
backend:
    cd backend && uv run uvicorn app.main:app --reload --port 8000

# Start the Next.js frontend dev server
frontend:
    cd frontend && pnpm dev

# Print two-terminal quickstart (Windows-safe parallelism)
dev:
    @echo "Run these in two separate terminals:"
    @echo ""
    @echo "  Terminal 1:  just backend"
    @echo "  Terminal 2:  just frontend"
    @echo ""
    @echo "Backend:   http://localhost:8000"
    @echo "Frontend:  http://localhost:3000"
    @echo "Health:    http://localhost:8000/health"

# Run backend smoke tests
test:
    cd backend && uv run pytest -v

# Lint + format backend
lint:
    cd backend && uv run ruff check . --fix
    cd backend && uv run ruff format .

# Run both example agents to populate the trace DB with realistic demo data.
# The backend does NOT need to be running — agents write directly to SQLite.
# After this completes, start the backend and open http://localhost:3000
demo:
    @echo "=== MCP Trace Studio — demo traces ==="
    @echo "Running filesystem research agent…"
    cd backend && uv run python ../examples/filesystem_agent.py ..
    @echo "Running web-search agent…"
    cd backend && uv run python ../examples/search_agent.py "MCP observability"
    @echo ""
    @echo "Done. Start the backend then open http://localhost:3000"
    @echo "  just backend"
