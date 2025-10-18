"""
Compact Report Generator - Creates email-friendly reports under 50KB
Keeps ALL information but uses minimal styling
"""

from datetime import datetime
from typing import Dict, List


def generate_compact_html_report(scan_results: Dict) -> str:
    """Generate compact HTML report that fits in email"""

    now = datetime.now()
    total_scanned = len(scan_results['all_scans'])
    total_setups = len(scan_results['high_probability_setups'])

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{{font-family:Arial,sans-serif;margin:0;padding:10px;background:#f5f5f5;font-size:13px}}
.c{{max-width:900px;margin:0 auto;background:#fff;border-radius:8px;padding:15px}}
h1{{color:#1e3c72;font-size:22px;margin:0 0 5px;text-align:center}}
.date{{text-align:center;color:#666;font-size:12px;margin-bottom:15px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin:15px 0;background:#f8f9fa;padding:10px;border-radius:6px}}
.stat{{text-align:center}}
.sv{{font-size:20px;font-weight:bold;color:#667eea}}
.sl{{font-size:10px;color:#666;text-transform:uppercase}}
h2{{color:#667eea;font-size:16px;margin:15px 0 8px;border-bottom:2px solid #667eea;padding-bottom:3px}}
.trade{{background:#f8f9fa;border-left:4px solid #667eea;padding:10px;margin:8px 0;border-radius:4px}}
.th{{font-size:16px;font-weight:bold;color:#1e3c72;margin-bottom:6px}}
.dir-b{{color:#10b981}}
.dir-s{{color:#ef4444}}
.conf{{background:linear-gradient(135deg,#f093fb,#f5576c);color:#fff;padding:4px 12px;border-radius:12px;font-size:12px;font-weight:bold;display:inline-block}}
.m{{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:6px;margin:8px 0}}
.mi{{background:#fff;padding:6px;border-radius:4px;border:1px solid #e0e0e0}}
.ml{{font-size:9px;color:#666;text-transform:uppercase}}
.mv{{font-weight:bold;color:#1e3c72;font-size:13px}}
.pos{{color:#10b981}}
.neg{{color:#ef4444}}
.sig{{margin:6px 0}}
.sb{{display:inline-block;background:#667eea;color:#fff;padding:3px 8px;border-radius:10px;font-size:10px;margin:2px}}
table{{width:100%;border-collapse:collapse;font-size:11px;margin:8px 0}}
th{{background:#667eea;color:#fff;padding:6px;text-align:left;font-size:10px}}
td{{padding:6px;border-bottom:1px solid #f0f0f0}}
.alert{{background:#fff3cd;border-left:3px solid #ffc107;padding:8px;margin:8px 0;font-size:11px}}
.footer{{background:#f8f9fa;padding:10px;margin-top:15px;border-top:1px solid #e0e0e0;text-align:center;font-size:10px;color:#666}}
</style></head><body><div class="c">
<h1>Daily Quantitative Trading Report</h1>
<div class="date">{now.strftime('%A, %B %d, %Y - %I:%M %p UTC')}</div>
<div class="stats">
<div class="stat"><div class="sv">{total_scanned}</div><div class="sl">Scanned</div></div>
<div class="stat"><div class="sv">{total_setups}</div><div class="sl">Setups</div></div>
<div class="stat"><div class="sv">{len(scan_results.get('top_movers', []))}</div><div class="sl">Movers</div></div>
</div>
"""

    # High Probability Setups
    setups = scan_results['high_probability_setups'][:10]
    if setups:
        html += "<h2>High-Probability Trade Setups</h2>"
        for s in setups:
            setup = s.get('setup')
            if not setup:
                continue

            dir_class = 'dir-b' if setup['direction'] == 'BULLISH' else 'dir-s'
            html += f"""<div class="trade">
<div class="th">{setup['symbol']} <span class="{dir_class}">{setup['direction']}</span> <span class="conf">{setup['confidence']:.0f}%</span></div>
<div class="m">
<div class="mi"><div class="ml">Entry</div><div class="mv">{setup['entry']:.5f}</div></div>
<div class="mi"><div class="ml">Stop</div><div class="mv neg">{setup['stop_loss']:.5f}</div></div>
<div class="mi"><div class="ml">Target 1</div><div class="mv pos">{setup['target_1']:.5f}</div></div>
<div class="mi"><div class="ml">Target 2</div><div class="mv pos">{setup['target_2']:.5f}</div></div>
<div class="mi"><div class="ml">R:R</div><div class="mv">1:{setup['risk_reward']:.1f}</div></div>
<div class="mi"><div class="ml">Size</div><div class="mv">{setup['lot_size']:.2f} lots</div></div>
</div>
<div class="sig">"""
            for sig in setup['signals'][:5]:  # Top 5 signals only
                html += f'<span class="sb">{sig["signal"]} (W:{sig["weight"]})</span>'
            html += "</div></div>"

    # Market Overview
    all_scans = scan_results['all_scans']
    if all_scans:
        bullish = sum(1 for s in all_scans if s['signal_data']['direction'] == 'BULLISH')
        bearish = sum(1 for s in all_scans if s['signal_data']['direction'] == 'BEARISH')

        html += f"""<h2>Market Overview</h2>
<div class="stats">
<div class="stat"><div class="sv pos">{bullish}</div><div class="sl">Bullish</div></div>
<div class="stat"><div class="sv neg">{bearish}</div><div class="sl">Bearish</div></div>
<div class="stat"><div class="sv">{len(all_scans) - bullish - bearish}</div><div class="sl">Neutral</div></div>
</div>"""

    # Top Movers
    movers = sorted(scan_results['all_scans'], key=lambda x: abs(x['change_24h']), reverse=True)[:10]
    if movers:
        html += "<h2>Top Market Movers (24H)</h2><table><tr><th>#</th><th>Symbol</th><th>Price</th><th>24H</th><th>Signal</th></tr>"
        for i, m in enumerate(movers, 1):
            ch_class = 'pos' if m['change_24h'] > 0 else 'neg'
            html += f"<tr><td>{i}</td><td><b>{m['symbol']}</b></td><td>{m['price']:.5f}</td><td class='{ch_class}'><b>{m['change_24h']:+.2f}%</b></td><td>{m['signal_data']['direction']}</td></tr>"
        html += "</table>"

    # Technical Analysis Summary
    if setups:
        html += "<h2>Technical Analysis (Top Setups)</h2><table><tr><th>Symbol</th><th>RSI</th><th>MACD</th><th>ADX</th><th>Vol%</th></tr>"
        for s in setups[:5]:
            rsi_class = 'neg' if s['rsi'] > 70 else ('pos' if s['rsi'] < 30 else '')
            macd_class = 'pos' if s['macd'] > 0 else 'neg'
            html += f"<tr><td><b>{s['symbol']}</b></td><td class='{rsi_class}'>{s['rsi']:.1f}</td><td class='{macd_class}'>{s['macd']:.4f}</td><td>{s['adx']:.1f}</td><td>{s['volatility']:.1f}%</td></tr>"
        html += "</table>"

    # Risk Calendar
    html += """<h2>Risk Management</h2>
<div class="alert"><b>Key Rules:</b> Max 2% risk/trade | Min 1:2 R:R | Max 5 positions | Use calculated lot sizes | Always set stop losses</div>"""

    # Footer
    html += f"""<div class="footer">
<p><b>Disclaimer:</b> For educational purposes only. Not financial advice.</p>
<p>Generated by PropShop Trading Intelligence | {now.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
</div></div></body></html>"""

    return html
