#!/usr/bin/env python3
"""
LIVE GOLD TRADER - Actually trades, no BS.
"""

import sys
import time
import logging
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from src.core.broker_mt5 import MT5Broker, OrderRequest
from src.core.symbols import SymbolInfo, AssetClass
from src.strategy.gold_simple import GoldSimpleStrategy
from src.strategy.loader import MarketState
from src.ui.cli import CLI

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gold_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_gold_trader():
    """Run live Gold trader with simple strategy."""
    print("🚀 LIVE GOLD TRADER")
    print("=" * 50)
    print("Strategy: Simple momentum (MA20)")
    print("Symbol: GOLD")
    print("Frame: H1")
    print("Risk: 0.8% per trade")
    print("Target: 2:1 RR")
    print("-" * 50)
    
    # Connect to broker
    broker = MT5Broker(
        login="165835373", 
        password="Manan@123!!",
        server="XMGlobal-MT5 2",
        paper_mode=False  # LIVE TRADING!
    )
    
    try:
        broker.connect()
        logger.info("✅ Connected to MT5 - LIVE MODE")
        
        # Initialize strategy
        gold_info = SymbolInfo(
            symbol="GOLD",
            asset_class=AssetClass.COMMODITIES,
            contract_size=100.0,
            pip_size=0.01,
            min_lot=0.01,
            max_lot=50.0,
            lot_step=0.01,
            base_currency="XAU",
            quote_currency="USD", 
            margin_currency="USD",
            description="Gold vs USD",
        )
        
        strategy = GoldSimpleStrategy()
        
        logger.info(f"📊 Strategy {strategy.name} ready")
        
        # Trading loop
        trade_count = 0
        signal_count = 0
        
        while True:
            try:
                # Get current data
                bars_h1 = broker.get_bars("GOLD", "H1", count=50) or []
                tick = broker.get_tick("GOLD")
                
                if not bars_h1 or not tick:
                    logger.warning("No data available, waiting...")
                    time.sleep(30)
                    continue
                
                # Create market state
                market_state = MarketState(
                    symbol="GOLD",
                    timestamp=tick.time,
                    bid=tick.bid,
                    ask=tick.ask,
                    bars_h1=bars_h1,
                    bars_h4=[],
                    bars_d1=[],
                    symbol_info=gold_info,
                )
                
                # Generate signal
                signal = strategy.analyze(market_state)
                
                if signal:
                    signal_count += 1
                    logger.info(f"🎯 SIGNAL #{signal_count}: {signal.direction} GOLD at ${signal.entry_price:.2f}")
                    logger.info(f"    SL: ${signal.stop_loss:.2f}, TP: ${signal.take_profit:.2f}")
                    logger.info(f"    Reason: {signal.reason}")
                    
                    # Calculate position size (1% risk)
                    account_info = broker.get_account_info()
                    risk_amount = account_info.equity * 0.01  # 1% risk
                    
                    lots = strategy.calculate_position_size(
                        signal.entry_price,
                        signal.stop_loss,
                        risk_amount,
                        gold_info
                    )
                    
                    logger.info(f"    Position: {lots:.2f} lots (Risk: ${risk_amount:.2f})")
                    
                    # Execute trade
                    trade_type = "buy" if signal.direction == "buy" else "sell"
                    
                    order_request = OrderRequest(
                        symbol="GOLD",
                        volume=lots,
                        order_type=signal.direction,
                        price=signal.entry_price,
                        stop_loss=signal.stop_loss,
                        take_profit=signal.take_profit,
                        comment=f"{strategy.name}-{signal_count}"
                    )
                    
                    success, message, ticket = broker.place_order(order_request)
                    
                    if success and ticket:
                        trade_count += 1
                        logger.info(f"✅ TRADE #{trade_count} EXECUTED!")
                        logger.info(f"    Ticket: {ticket}")
                        logger.info(f"    Order: {message}")
                        logger.info(f"    Price: ${signal.entry_price:.2f}")
                        logger.info(f"    Size: {lots:.2f} lots")
                    else:
                        logger.error(f"❌ Trade failed: {message}")
                    
                    # Wait after signal to avoid spamming
                    time.sleep(300)  # 5 minutes
                
                else:
                    # Log market state
                    current_price = bars_h1[-1]["close"]
                    ma = strategy._calculate_ma([b["close"] for b in bars_h1], 20)
                    momentum = (current_price - ma) / ma * 100 if ma else 0
                    
                    logger.debug(f"📊 GOLD ${current_price:.2f}, MA20 ${ma:.2f}, Momentum {momentum:.1f}%")
                
                # Wait for next iteration
                time.sleep(60)  # Check every minute
                
            except KeyboardInterrupt:
                logger.info("👋 Stopping trader...")
                break
            except Exception as e:
                logger.error(f"❌ Error in trading loop: {e}")
                time.sleep(60)
        
        logger.info(f"📈 Trading session complete:")
        logger.info(f"    Signals generated: {signal_count}")
        logger.info(f"    Trades executed: {trade_count}")
        
    except Exception as e:
        logger.error(f"❌ Trader failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        broker.disconnect()
        logger.info("🔌 Disconnected from MT5")


if __name__ == "__main__":
    run_gold_trader()
