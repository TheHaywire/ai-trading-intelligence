"""Real-time trading dashboard with WebSocket streaming."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DashboardState(BaseModel):
    """Current dashboard state."""

    timestamp: datetime
    equity: float
    balance: float
    dd_floor: float
    dd_utilization: float
    margin_used: float
    free_margin: float
    open_positions: int
    daily_pnl: float
    signals_today: int
    trades_today: int


class DashboardServer:
    """
    Real-time dashboard server with WebSocket streaming.

    Features:
    - WebSocket streaming of equity, DD%, positions
    - REST API for historical data
    - Multi-client support
    - Auto-reconnect handling
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        """
        Initialize dashboard server.

        Args:
            host: Server host
            port: Server port
        """
        self.app = FastAPI(title="PropShop IF Dashboard", version="1.0.0")
        self.host = host
        self.port = port

        # WebSocket clients
        self.active_connections: List[WebSocket] = []

        # Current state
        self.current_state: Optional[DashboardState] = None

        # Setup routes
        self._setup_routes()
        self._setup_middleware()

    def _setup_middleware(self):
        """Setup CORS middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routes(self):
        """Setup API routes."""

        @self.app.get("/")
        async def root():
            """Root endpoint."""
            return {
                "name": "PropShop IF Dashboard",
                "version": "1.0.0",
                "status": "operational",
                "websocket": f"ws://{self.host}:{self.port}/ws",
            }

        @self.app.get("/status")
        async def status():
            """Get current system status."""
            if not self.current_state:
                return {"error": "No data available"}

            return {
                "timestamp": self.current_state.timestamp.isoformat(),
                "equity": self.current_state.equity,
                "balance": self.current_state.balance,
                "dd_floor": self.current_state.dd_floor,
                "dd_utilization": self.current_state.dd_utilization,
                "margin_used": self.current_state.margin_used,
                "free_margin": self.current_state.free_margin,
                "open_positions": self.current_state.open_positions,
                "daily_pnl": self.current_state.daily_pnl,
                "signals_today": self.current_state.signals_today,
                "trades_today": self.current_state.trades_today,
            }

        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "clients_connected": len(self.active_connections),
                "last_update": self.current_state.timestamp.isoformat()
                if self.current_state
                else None,
            }

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates."""
            await self.connect(websocket)
            try:
                # Send initial state
                if self.current_state:
                    await websocket.send_json(self.current_state.dict())

                # Keep connection alive
                while True:
                    # Wait for client messages (ping/pong)
                    data = await websocket.receive_text()
                    if data == "ping":
                        await websocket.send_text("pong")

            except WebSocketDisconnect:
                self.disconnect(websocket)
                logger.info(f"Client disconnected")

    async def connect(self, websocket: WebSocket):
        """Connect a new WebSocket client."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected, total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket client."""
        self.active_connections.remove(websocket)
        logger.info(f"Client disconnected, remaining: {len(self.active_connections)}")

    async def broadcast_update(self, state: DashboardState):
        """
        Broadcast update to all connected clients.

        Args:
            state: Current dashboard state
        """
        self.current_state = state

        # Send to all connected clients
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(state.dict())
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    def update_state(
        self,
        equity: float,
        balance: float,
        dd_floor: float,
        dd_utilization: float,
        margin_used: float,
        free_margin: float,
        open_positions: int,
        daily_pnl: float = 0.0,
        signals_today: int = 0,
        trades_today: int = 0,
    ):
        """
        Update dashboard state (synchronous wrapper).

        Args:
            equity: Current equity
            balance: Current balance
            dd_floor: DD floor level
            dd_utilization: DD utilization %
            margin_used: Margin used
            free_margin: Free margin
            open_positions: Number of open positions
            daily_pnl: Daily P&L
            signals_today: Signals generated today
            trades_today: Trades executed today
        """
        state = DashboardState(
            timestamp=datetime.utcnow(),
            equity=equity,
            balance=balance,
            dd_floor=dd_floor,
            dd_utilization=dd_utilization,
            margin_used=margin_used,
            free_margin=free_margin,
            open_positions=open_positions,
            daily_pnl=daily_pnl,
            signals_today=signals_today,
            trades_today=trades_today,
        )

        # Schedule broadcast
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.broadcast_update(state))
        except RuntimeError:
            # No event loop running yet
            pass

    async def start(self):
        """Start the dashboard server."""
        import uvicorn

        config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()


# Global dashboard instance
_dashboard: Optional[DashboardServer] = None


def get_dashboard() -> DashboardServer:
    """Get or create global dashboard instance."""
    global _dashboard
    if _dashboard is None:
        _dashboard = DashboardServer()
    return _dashboard


def start_dashboard_server(host: str = "0.0.0.0", port: int = 8000):
    """
    Start dashboard server in background thread.

    Args:
        host: Server host
        port: Server port
    """
    import threading

    dashboard = get_dashboard()

    def run():
        asyncio.run(dashboard.start())

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    logger.info(f"Dashboard server started at http://{host}:{port}")
    return dashboard
