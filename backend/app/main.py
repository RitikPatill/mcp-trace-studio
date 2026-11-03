from fastapi import FastAPI

app = FastAPI(title="MCP Trace Studio", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "mcp-trace-studio"}
