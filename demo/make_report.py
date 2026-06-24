import json
from html import escape
from pathlib import Path

data = json.loads(Path("demo/bountyops_output.json").read_text())
pack = data["submission_pack"]
orders = data["specialist_orders"]
ledger = data["ledger"]

def rows(items):
    return "\n".join(items)

agent_cards = rows([
    f"""
    <div class="card">
      <h3>{escape(o['agent_name'])}</h3>
      <p><b>Service:</b> {escape(o['service'])}</p>
      <p><b>Wallet:</b> <code>{escape(o['agent_wallet'])}</code></p>
      <p><b>Price:</b> {o['price_usdc']} USDC</p>
      <p><b>Status:</b> {escape(o['status'])}</p>
    </div>
    """
    for o in orders
])

ledger_rows = rows([
    f"""
    <tr>
      <td>{escape(e['timestamp'])}</td>
      <td>{escape(e['actor'])}</td>
      <td>{escape(e['action'])}</td>
      <td>{escape(str(e.get('counterparty') or '—'))}</td>
      <td>{escape(str(e.get('amount_usdc') or '—'))}</td>
    </tr>
    """
    for e in ledger
])

rationale = rows([f"<li>{escape(x)}</li>" for x in pack["rationale"]])
checklist = rows([f"<li>{escape(x)}</li>" for x in pack["submission_checklist"]])
next_actions = rows([f"<li>{escape(x)}</li>" for x in pack["next_actions"]])

html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>BountyOps CROO Demo Report</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      background: #0b1020;
      color: #eef2ff;
    }}
    header {{
      padding: 48px;
      background: linear-gradient(135deg, #111827, #312e81);
      border-bottom: 1px solid rgba(255,255,255,.12);
    }}
    h1 {{ font-size: 44px; margin: 0 0 12px; }}
    h2 {{ margin-top: 40px; }}
    .tagline {{ font-size: 20px; color: #c7d2fe; }}
    .wrap {{ max-width: 1120px; margin: 0 auto; padding: 32px; }}
    .hero {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
      margin-top: 24px;
    }}
    .metric, .card {{
      background: rgba(255,255,255,.07);
      border: 1px solid rgba(255,255,255,.12);
      border-radius: 16px;
      padding: 18px;
      box-shadow: 0 20px 50px rgba(0,0,0,.25);
    }}
    .metric strong {{ display: block; font-size: 28px; color: #a7f3d0; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
    code {{
      background: rgba(255,255,255,.1);
      padding: 2px 6px;
      border-radius: 6px;
      color: #bfdbfe;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: rgba(255,255,255,.06);
      border-radius: 14px;
      overflow: hidden;
    }}
    th, td {{
      padding: 12px;
      border-bottom: 1px solid rgba(255,255,255,.1);
      text-align: left;
      font-size: 14px;
    }}
    th {{ color: #c7d2fe; }}
    .proof {{
      word-break: break-all;
      background: rgba(16,185,129,.12);
      border: 1px solid rgba(16,185,129,.35);
      padding: 16px;
      border-radius: 14px;
    }}
    .box {{
      background: rgba(255,255,255,.06);
      border: 1px solid rgba(255,255,255,.10);
      border-radius: 16px;
      padding: 20px;
      margin: 16px 0;
      white-space: pre-wrap;
    }}
  </style>
</head>
<body>
  <header>
    <h1>BountyOps</h1>
    <div class="tagline">Autonomous Opportunity-to-Submission Agent for CROO CAP commerce</div>
  </header>

  <main class="wrap">
    <section class="hero">
      <div class="metric"><span>Decision</span><strong>{escape(pack['go_no_go'])}</strong></div>
      <div class="metric"><span>EV Score</span><strong>{pack['expected_value_score']}/100</strong></div>
      <div class="metric"><span>Specialist Agents</span><strong>{len(orders)}</strong></div>
      <div class="metric"><span>Total Order</span><strong>{data['ledger'][0]['amount_usdc']} USDC</strong></div>
    </section>

    <h2>Recommended Project</h2>
    <div class="box"><b>{escape(pack['recommended_project'])}</b><br>{escape(pack['tagline'])}</div>

    <h2>Tracks</h2>
    <div class="box">Primary: {escape(pack['primary_track'])}<br>Secondary: {escape(pack['secondary_track'])}</div>

    <h2>A2A Specialist Orders</h2>
    <div class="grid">{agent_cards}</div>

    <h2>Why GO?</h2>
    <ul>{rationale}</ul>

    <h2>CAP-style Ledger</h2>
    <table>
      <tr><th>Timestamp</th><th>Actor</th><th>Action</th><th>Counterparty</th><th>USDC</th></tr>
      {ledger_rows}
    </table>

    <h2>Submission Checklist</h2>
    <ul>{checklist}</ul>

    <h2>DoraHacks Writeup Draft</h2>
    <div class="box">{escape(pack['dorahacks_writeup'])}</div>

    <h2>Demo Script</h2>
    <div class="box">{escape(pack['demo_script'])}</div>

    <h2>Verification Proof</h2>
    <div class="proof">{escape(data['proof_hash'])}</div>

    <h2>Next Actions</h2>
    <ul>{next_actions}</ul>
  </main>
</body>
</html>
"""

Path("demo/bountyops_report.html").write_text(html)
print("✅ wrote demo/bountyops_report.html")
