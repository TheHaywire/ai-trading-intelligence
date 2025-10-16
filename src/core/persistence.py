"""State persistence for trading system."""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class SystemState:
    """Serializable system state."""

    timestamp: str
    starting_balance: float
    current_equity: float
    dd_state: Dict[str, Any]
    positions_summary: Dict[str, Any]
    scaling_events: list
    payout_periods: list
    first_trade_date: Optional[str]
    last_payout_date: Optional[str]


class StatePersistence:
    """
    Persists and restores system state.

    Allows resuming trading sessions without losing critical state.
    """

    def __init__(self, state_dir: str = "runs/state"):
        """
        Initialize state persistence.

        Args:
            state_dir: Directory for state files
        """
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def save_state(
        self,
        dd_tracker,
        position_manager,
        scaling_manager,
        payout_scheduler,
        filename: str = "system_state.json",
    ) -> Path:
        """
        Save system state to JSON file.

        Args:
            dd_tracker: DrawdownTracker instance
            position_manager: PositionManager instance
            scaling_manager: ScalingManager instance
            payout_scheduler: PayoutScheduler instance
            filename: Output filename

        Returns:
            Path to saved file
        """
        state = SystemState(
            timestamp=datetime.utcnow().isoformat(),
            starting_balance=dd_tracker.starting_balance,
            current_equity=dd_tracker.current_equity,
            dd_state=dd_tracker.get_summary(),
            positions_summary=position_manager.get_summary(),
            scaling_events=[asdict(e) for e in scaling_manager.scaling_events],
            payout_periods=[asdict(p) for p in payout_scheduler.periods],
            first_trade_date=payout_scheduler.first_trade_date.isoformat()
            if payout_scheduler.first_trade_date
            else None,
            last_payout_date=payout_scheduler.last_payout_date.isoformat()
            if payout_scheduler.last_payout_date
            else None,
        )

        filepath = self.state_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(state), f, indent=2)

        logger.info(f"Saved system state to {filepath}")
        return filepath

    def load_state(self, filename: str = "system_state.json") -> Optional[SystemState]:
        """
        Load system state from JSON file.

        Args:
            filename: State file to load

        Returns:
            SystemState or None if not found
        """
        filepath = self.state_dir / filename

        if not filepath.exists():
            logger.warning(f"State file not found: {filepath}")
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            state = SystemState(**data)
            logger.info(f"Loaded system state from {filepath}")
            return state

        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return None

    def backup_state(self, filename: str = "system_state.json") -> Optional[Path]:
        """
        Create a timestamped backup of current state.

        Args:
            filename: Source state file

        Returns:
            Path to backup file
        """
        source = self.state_dir / filename

        if not source.exists():
            return None

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = self.state_dir / f"system_state_backup_{timestamp}.json"

        try:
            import shutil

            shutil.copy(source, backup_file)
            logger.info(f"Created state backup: {backup_file}")
            return backup_file

        except Exception as e:
            logger.error(f"Failed to backup state: {e}")
            return None
