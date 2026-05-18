from pathlib import Path
import json
import pandas as pd

SOURCE_DIR = Path("dashboard_source")
DOCS_DIR = Path("docs")
DOCS_DIR.mkdir(exist_ok=True)

OUTPUT_HTML = DOCS_DIR / "index.html"

GEOGRAPHIES = {
    "county": {
        "label": "County",
        "party_file": "county_party_counts.csv",
        "turnout_file": "county_turnout_2025.csv",
        "switcher_file": "county_party_switchers_enriched.csv",
        "key": "county",
        "display": "county",
    },
    "municipality": {
        "label": "Municipality",
        "party_file": "municipality_party_counts.csv",
        "turnout_file": "municipality_turnout_2025.csv",
        "switcher_file": "municipality_party_switchers_enriched.csv",
        "key": "municipality",
        "display": "municipality",
    },
    "polling_place": {
        "label": "Polling Place",
        "party_file": "polling_place_party_counts.csv",
        "turnout_file": "polling_place_turnout_2025.csv",
        "switcher_file": "polling_place_party_switchers_enriched.csv",
        "key": "polling_place_key",
        "display": "polling_place",
    },
    "precinct": {
        "label": "Precinct",
        "party_file": "precinct_split_party_counts.csv",
        "turnout_file": "precinct_split_turnout_2025.csv",
        "switcher_file": None,
        "key": "precinct_split_id",
        "display": "precinct_split_id",
    },
    "state_house": {
        "label": "State House",
        "party_file": "state_house_party_counts.csv",
        "turnout_file": "state_house_turnout_2025.csv",
        "switcher_file": "state_house_party_switchers_enriched.csv",
        "key": "state_house",
        "display": "state_house",
    },
    "state_senate": {
        "label": "State Senate",
        "party_file": "state_senate_party_counts.csv",
        "turnout_file": "state_senate_turnout_2025.csv",
        "switcher_file": "state_senate_party_switchers_enriched.csv",
        "key": "state_senate",
        "display": "state_senate",
    },
}


def read_csv_required(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return pd.read_csv(path, low_memory=False)


def clean_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    return value


def row_to_dict(row):
    return {k: clean_value(v) for k, v in row.items()}


def fmt_int(value):
    if value is None or pd.isna(value):
        return "not available"
    return f"{int(round(float(value))):,}"


def fmt_pct(value):
    if value is None or pd.isna(value):
        return "not available"
    return f"{float(value):.2f}%"


def fmt_signed_int(value):
    if value is None or pd.isna(value):
        return "not available"
    value = int(round(float(value)))
    if value > 0:
        return f"+{value:,}"
    return f"{value:,}"


def fmt_signed_pct(value):
    if value is None or pd.isna(value):
        return "not available"
    value = float(value)
    if value > 0:
        return f"+{value:.2f}"
    return f"{value:.2f}"


def party_leader(row):
    d = row.get("D") or 0
    r = row.get("R") or 0
    if d > r:
        return "Democrats"
    if r > d:
        return "Republicans"
    return "Democrats and Republicans are tied"


def build_summary(geo_label, party_row, turnout_row=None, switcher_row=None):
    name = party_row.get("_display_name") or party_row.get("_key_value") or "This geography"

    total = fmt_int(party_row.get("total_voters"))
    d_count = fmt_int(party_row.get("D"))
    r_count = fmt_int(party_row.get("R"))
    oth_count = fmt_int(party_row.get("Oth"))

    d_pct = fmt_pct(party_row.get("D_pct"))
    r_pct = fmt_pct(party_row.get("R_pct"))
    oth_pct = fmt_pct(party_row.get("Oth_pct"))

    dvr = party_row.get("DvR")
    dvr_pct = party_row.get("DvR_pct")

    leader = party_leader(party_row)

    if leader == "Democrats and Republicans are tied":
        margin_sentence = (
            f"Democrats and Republicans are tied in registration here, "
            f"with a D-vs.-R margin of {fmt_signed_int(dvr)} voters."
        )
    elif leader == "Democrats":
        margin_sentence = (
            f"Democrats have a registration advantage of {fmt_int(abs(dvr))} voters over Republicans, "
            f"equal to {fmt_signed_pct(dvr_pct)} percentage points of the electorate."
        )
    else:
        margin_sentence = (
            f"Republicans have a registration advantage of {fmt_int(abs(dvr))} voters over Democrats, "
            f"equal to {fmt_signed_pct(abs(dvr_pct))} percentage points of the electorate."
        )

    lines = []

    lines.append(
        f"{name} is a {geo_label.lower()} with {total} registered voters. "
        f"That includes {d_count} Democrats ({d_pct}), {r_count} Republicans ({r_pct}) "
        f"and {oth_count} voters registered with another party or no major-party affiliation ({oth_pct})."
    )

    lines.append(margin_sentence)

    if turnout_row:
        lines.append(
            f"In the 2025 municipal election, {fmt_int(turnout_row.get('voted_total'))} voters from this geography cast ballots, "
            f"for an overall turnout rate of {fmt_pct(turnout_row.get('turnout_pct'))}. "
            f"Democratic turnout was {fmt_pct(turnout_row.get('D_turnout_pct'))}, "
            f"Republican turnout was {fmt_pct(turnout_row.get('R_turnout_pct'))}, "
            f"and turnout among other voters was {fmt_pct(turnout_row.get('Oth_turnout_pct'))}."
        )

    if switcher_row:
        lines.append(
            f"Party-switching data shows a net change of {fmt_signed_int(switcher_row.get('D_net'))} for Democrats, "
            f"{fmt_signed_int(switcher_row.get('R_net'))} for Republicans and "
            f"{fmt_signed_int(switcher_row.get('Oth_net'))} for other or unaffiliated voters."
        )

    return "\n\n".join(lines)


def build_dashboard_data():
    dashboard = {}

    for geo_type, config in GEOGRAPHIES.items():
        key = config["key"]
        display_col = config["display"]

        party_df = read_csv_required(SOURCE_DIR / config["party_file"])

        turnout_df = None
        if config["turnout_file"]:
            turnout_path = SOURCE_DIR / config["turnout_file"]
            if turnout_path.exists():
                turnout_df = pd.read_csv(turnout_path, low_memory=False)

        switcher_df = None
        if config["switcher_file"]:
            switcher_path = SOURCE_DIR / config["switcher_file"]
            if switcher_path.exists():
                switcher_df = pd.read_csv(switcher_path, low_memory=False)

        records = []

        for _, party_series in party_df.iterrows():
            party_row = row_to_dict(party_series)

            key_value = party_row.get(key)
            if key_value is None:
                continue

            display_name = party_row.get(display_col) or key_value

            if geo_type == "polling_place":
                address = party_row.get("full_address")
                post_office = party_row.get("post_office")
                if address and post_office:
                    display_name = f"{display_name}, {address}, {post_office}"

            if geo_type == "state_house":
                display_name = f"State House District {display_name}"

            if geo_type == "state_senate":
                display_name = f"State Senate District {display_name}"

            if geo_type == "precinct":
                muni = party_row.get("municipality")
                if muni:
                    display_name = f"{display_name} ({muni})"

            party_row["_key_value"] = str(key_value)
            party_row["_display_name"] = str(display_name)

            turnout_row = None
            if turnout_df is not None and key in turnout_df.columns:
                match = turnout_df[turnout_df[key].astype(str) == str(key_value)]
                if not match.empty:
                    turnout_row = row_to_dict(match.iloc[0])

            switcher_row = None
            if switcher_df is not None and key in switcher_df.columns:
                match = switcher_df[switcher_df[key].astype(str) == str(key_value)]
                if not match.empty:
                    switcher_row = row_to_dict(match.iloc[0])

            summary = build_summary(
                geo_label=config["label"],
                party_row=party_row,
                turnout_row=turnout_row,
                switcher_row=switcher_row,
            )

            records.append({
                "key": str(key_value),
                "display": str(display_name),
                "party": party_row,
                "turnout": turnout_row,
                "switcher": switcher_row,
                "summary": summary,
            })

        records = sorted(records, key=lambda x: x["display"])

        dashboard[geo_type] = {
            "label": config["label"],
            "records": records,
        }

    return dashboard


def write_html(data):
    data_json = json.dumps(data, ensure_ascii=False)

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Bucks Primary XCopy Summary Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 0;
      background: #f5f5f5;
      color: #222;
    }}
    header {{
      background: #111827;
      color: white;
      padding: 20px;
    }}
    main {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 20px;
    }}
    .controls, .card {{
      background: white;
      border-radius: 12px;
      padding: 18px;
      margin-bottom: 16px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.08);
    }}
    label {{
      display: block;
      font-weight: bold;
      margin-bottom: 6px;
    }}
    select, textarea, button {{
      width: 100%;
      box-sizing: border-box;
      font-size: 16px;
    }}
    select {{
      padding: 10px;
      margin-bottom: 14px;
    }}
    textarea {{
      min-height: 290px;
      padding: 14px;
      line-height: 1.45;
      font-family: Georgia, serif;
    }}
    button {{
      padding: 12px;
      margin-top: 10px;
      border: 0;
      border-radius: 8px;
      background: #2563eb;
      color: white;
      cursor: pointer;
      font-weight: bold;
    }}
    button:hover {{
      background: #1d4ed8;
    }}
    .stats-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
    }}
    .stat {{
      background: #f9fafb;
      border: 1px solid #e5e7eb;
      border-radius: 10px;
      padding: 12px;
    }}
    .stat-label {{
      color: #6b7280;
      font-size: 13px;
      margin-bottom: 4px;
    }}
    .stat-value {{
      font-size: 22px;
      font-weight: bold;
    }}
    .note {{
      color: #6b7280;
      font-size: 14px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>Bucks Primary XCopy Summary Dashboard</h1>
    <p>Reporter-facing summary generator for voter registration, turnout and party-switching stats.</p>
  </header>

  <main>
    <section class="controls">
      <label for="geoType">Geography type</label>
      <select id="geoType"></select>

      <label for="geoRecord">Geography</label>
      <select id="geoRecord"></select>

      <p class="note">Select a geography and copy the generated summary block below.</p>
    </section>

    <section class="card">
      <h2>Quick stats</h2>
      <div class="stats-grid" id="statsGrid"></div>
    </section>

    <section class="card">
      <h2>Copy-ready draft summary</h2>
      <textarea id="summaryBox"></textarea>
      <button id="copyButton">Copy summary</button>
    </section>
  </main>

  <script>
    const DASHBOARD_DATA = {data_json};

    const geoTypeSelect = document.getElementById("geoType");
    const geoRecordSelect = document.getElementById("geoRecord");
    const summaryBox = document.getElementById("summaryBox");
    const statsGrid = document.getElementById("statsGrid");
    const copyButton = document.getElementById("copyButton");

    function fmtInt(value) {{
      if (value === null || value === undefined || Number.isNaN(Number(value))) return "N/A";
      return Math.round(Number(value)).toLocaleString();
    }}

    function fmtPct(value) {{
      if (value === null || value === undefined || Number.isNaN(Number(value))) return "N/A";
      return Number(value).toFixed(2) + "%";
    }}

    function fillGeoTypes() {{
      geoTypeSelect.innerHTML = "";
      Object.entries(DASHBOARD_DATA).forEach(([key, geo]) => {{
        const option = document.createElement("option");
        option.value = key;
        option.textContent = geo.label;
        geoTypeSelect.appendChild(option);
      }});
    }}

    function fillGeoRecords() {{
      const geoType = geoTypeSelect.value;
      const records = DASHBOARD_DATA[geoType].records;

      geoRecordSelect.innerHTML = "";

      records.forEach((record, index) => {{
        const option = document.createElement("option");
        option.value = index;
        option.textContent = record.display;
        geoRecordSelect.appendChild(option);
      }});

      updateSummary();
    }}

    function addStat(label, value) {{
      const div = document.createElement("div");
      div.className = "stat";
      div.innerHTML = `
        <div class="stat-label">${{label}}</div>
        <div class="stat-value">${{value}}</div>
      `;
      statsGrid.appendChild(div);
    }}

    function updateSummary() {{
      const geoType = geoTypeSelect.value;
      const index = Number(geoRecordSelect.value || 0);
      const record = DASHBOARD_DATA[geoType].records[index];

      if (!record) {{
        summaryBox.value = "";
        statsGrid.innerHTML = "";
        return;
      }}

      summaryBox.value = record.summary;

      const party = record.party || {{}};
      const turnout = record.turnout || {{}};

      statsGrid.innerHTML = "";
      addStat("Total voters", fmtInt(party.total_voters));
      addStat("Democrats", fmtInt(party.D));
      addStat("Republicans", fmtInt(party.R));
      addStat("Other", fmtInt(party.Oth));
      addStat("D share", fmtPct(party.D_pct));
      addStat("R share", fmtPct(party.R_pct));
      addStat("D vs. R margin", fmtInt(party.DvR));
      addStat("Turnout", fmtPct(turnout.turnout_pct));
    }}

    copyButton.addEventListener("click", async () => {{
      await navigator.clipboard.writeText(summaryBox.value);
      copyButton.textContent = "Copied!";
      setTimeout(() => copyButton.textContent = "Copy summary", 1200);
    }});

    geoTypeSelect.addEventListener("change", fillGeoRecords);
    geoRecordSelect.addEventListener("change", updateSummary);

    fillGeoTypes();
    fillGeoRecords();
  </script>
</body>
</html>
"""

    OUTPUT_HTML.write_text(html, encoding="utf-8")


def main():
    data = build_dashboard_data()
    write_html(data)
    print(f"Wrote {OUTPUT_HTML.resolve()}")


if __name__ == "__main__":
    main()