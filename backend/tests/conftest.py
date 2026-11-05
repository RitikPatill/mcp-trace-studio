"""pytest configuration for the backend test suite."""
from __future__ import annotations

import pytest


# mcp's jsonrpc_dispatcher calls CancelScope.cancel(reason) which trio does not
# accept (TypeError: takes 1 positional argument but 2 were given).  Restrict
# all anyio tests to the asyncio backend until mcp ships a compatible release.
@pytest.fixture(params=["asyncio"])
def anyio_backend(request: pytest.FixtureRequest) -> str:
    return request.param  # type: ignore[return-value]
