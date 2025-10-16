import MetaTrader5 as mt5

mt5.initialize()
tick = mt5.symbol_info_tick('GOLD')
print(f'Current live Gold price:')
print(f'  Bid: ${tick.bid:.2f}')
print(f'  Ask: ${tick.ask:.2f}')
mt5.shutdown()
