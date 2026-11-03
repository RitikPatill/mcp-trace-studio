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
