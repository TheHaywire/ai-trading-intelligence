"""Simple FastAPI dashboard for monitoring."""

import logging
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Instant Bot Dashboard",
    description="Monitoring API for MT5 trading system",
    version="0.1.0",
)

# Global state (in production, use proper state management)
_state: Dict = {
    "initialized": False,
    "broker_connected": False,
    "positions": [],
    "account": {},
    "dd_tracker": {},
    "risk_engine": {},
    "compliance": {},
}


def update_state(state: Dict) -> None:
    """Update global state."""
    global _state
    _state.update(state)


@app.get("/")
async def root() -> Dict:
    """Root endpoint."""
    return {
        "service": "Instant Bot Dashboard",
        "version": "0.1.0",
        "status": "running" if _state["initialized"] else "initializing",
    }


@app.get("/health")
async def health() -> Dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "broker_connected": _state.get("broker_connected", False),
        "initialized": _state.get("initialized", False),
    }


@app.get("/account")
async def get_account() -> Dict:
    """Get account information."""
    if not _state.get("account"):
        raise HTTPException(status_code=503, detail="Account data not available")

    return _state["account"]


@app.get("/positions")
async def get_positions() -> Dict:
    """Get open positions."""
    return {
        "count": len(_state.get("positions", [])),
        "positions": _state.get("positions", []),
    }


@app.get("/drawdown")
async def get_drawdown() -> Dict:
    """Get drawdown tracker state."""
    if not _state.get("dd_tracker"):
        raise HTTPException(status_code=503, detail="Drawdown data not available")

    return _state["dd_tracker"]


@app.get("/risk")
async def get_risk() -> Dict:
    """Get risk engine state."""
    if not _state.get("risk_engine"):
        raise HTTPException(status_code=503, detail="Risk data not available")

    return _state["risk_engine"]


@app.get("/compliance")
async def get_compliance() -> Dict:
    """Get compliance guard state."""
    if not _state.get("compliance"):
        raise HTTPException(status_code=503, detail="Compliance data not available")

    return _state["compliance"]


@app.get("/summary")
async def get_summary() -> Dict:
    """Get complete system summary."""
    return {
        "account": _state.get("account", {}),
        "positions_count": len(_state.get("positions", [])),
        "drawdown": _state.get("dd_tracker", {}),
        "risk": _state.get("risk_engine", {}),
        "compliance": _state.get("compliance", {}),
        "broker_connected": _state.get("broker_connected", False),
    }


def run_dashboard(host: str = "0.0.0.0", port: int = 8000) -> None:
    """
    Run the dashboard API server.

    Args:
        host: Host to bind to
        port: Port to bind to
    """
    import uvicorn

    logger.info(f"Starting dashboard on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_dashboard()
