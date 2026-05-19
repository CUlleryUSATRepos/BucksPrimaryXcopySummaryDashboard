from pathlib import Path
import json
import re
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
        "participation_file": "county_participation_since_2020.csv",
        "key": "county",
        "display": "county",
    },
    "municipality": {
        "label": "Municipality",
        "party_file": "municipality_party_counts.csv",
        "turnout_file": "municipality_turnout_2025.csv",
        "switcher_file": "municipality_party_switchers_enriched.csv",
        "participation_file": "municipality_participation_since_2020.csv",
        "key": "municipality",
        "display": "municipality",
    },
    "polling_place": {
        "label": "Polling Place",
        "party_file": "polling_place_party_counts.csv",
        "turnout_file": "polling_place_turnout_2025.csv",
        "switcher_file": "polling_place_party_switchers_enriched.csv",
        "participation_file": "polling_place_participation_since_2020.csv",
        "key": "polling_place_key",
        "display": "polling_place",
    },
    "precinct": {
        "label": "Precinct",
        "party_file": "precinct_split_party_counts.csv",
        "turnout_file": "precinct_split_turnout_2025.csv",
        "switcher_file": None,
        "participation_file": "precinct_split_participation_since_2020.csv",
        "key": "precinct_split_id",
        "display": "precinct_split_id",
    },
    "state_house": {
        "label": "State House",
        "party_file": "state_house_party_counts.csv",
        "turnout_file": "state_house_turnout_2025.csv",
        "switcher_file": "state_house_party_switchers_enriched.csv",
        "participation_file": "state_house_participation_since_2020.csv",
        "key": "state_house",
        "display": "state_house",
    },
    "state_senate": {
        "label": "State Senate",
        "party_file": "state_senate_party_counts.csv",
        "turnout_file": "state_senate_turnout_2025.csv",
        "switcher_file": "state_senate_party_switchers_enriched.csv",
        "participation_file": "state_senate_participation_since_2020.csv",
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


def clean_legislative_district_id(value):
    if value is None or pd.isna(value):
        return value

    text_value = str(value).strip().upper()

    # Handles values like STH029, STH018, STS010, STS006.
    match = re.search(r"(\d+)$", text_value)
    if match:
        return str(int(match.group(1)))

    return str(value).strip()


def normalize_match_value(value):
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().upper()


def find_matching_row(df, key, key_value):
    if df is None or key not in df.columns:
        return None

    target = normalize_match_value(key_value)
    matches = df[df[key].map(normalize_match_value) == target]

    if matches.empty:
        return None

    return row_to_dict(matches.iloc[0])


def fmt_int(value):
    if value is None or pd.isna(value):
        return "not available"
    return f"{int(round(float(value))):,}"


def fmt_pct(value):
    if value is None or pd.isna(value):
        return "not available"
    return f"{float(value):.2f}%"


def fmt_percent_text(value):
    if value is None or pd.isna(value):
        return "not available"
    return f"{float(value):.1f} percent"


def fmt_voter_word(value):
    try:
        value = int(round(float(value)))
    except Exception:
        return "voters"
    return "voter" if abs(value) == 1 else "voters"


def fmt_count_noun(value, noun):
    if value is None or pd.isna(value):
        return f"not available {noun}s"
    value = int(round(float(value)))
    word = noun if abs(value) == 1 else noun + "s"
    return f"{value:,} {word}"


def fmt_voters(value):
    return fmt_count_noun(value, "voter")


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


def geography_noun(geo_label):
    label = str(geo_label).strip().lower()

    if label == "county":
        return "county"
    if label == "municipality":
        return "municipality"
    if label == "polling place":
        return "polling place"
    if label == "precinct":
        return "precinct"
    if label == "state house":
        return "state House district"
    if label == "state senate":
        return "state Senate district"

    return label


def place_turnout_phrase(geo_label, name):
    noun = geography_noun(geo_label)

    if noun == "county":
        return f"{name} voters"
    if noun == "municipality":
        return f"voters in {name}"
    if noun == "polling place":
        return "voters assigned to this polling place"
    if noun == "precinct":
        return "voters in this precinct"
    if noun == "state House district":
        return "voters in this state House district"
    if noun == "state Senate district":
        return "voters in this state Senate district"

    return f"voters in {name}"


def place_registration_phrase(geo_label, name):
    noun = geography_noun(geo_label)

    if noun == "county":
        return "The county"
    if noun == "polling place":
        return "The polling place"
    if noun == "state House district":
        return "The state House district"
    if noun == "state Senate district":
        return "The state Senate district"
    if noun == "precinct":
        return "The precinct"
    if noun == "municipality":
        return "The municipality"

    return "The area"


def registered_voter_phrase(geo_label):
    noun = geography_noun(geo_label)

    if noun == "polling place":
        return "registered voters assigned to it"

    return "registered voters"


def margin_strength(abs_margin_pct):
    if abs_margin_pct is None or pd.isna(abs_margin_pct):
        return ""

    abs_margin_pct = abs(float(abs_margin_pct))

    if abs_margin_pct < 2:
        return "narrow "
    if abs_margin_pct < 5:
        return "modest "
    if abs_margin_pct < 10:
        return "clear "
    return "wide "


def switch_count(row, col):
    value = row.get(col)
    if value is None or pd.isna(value):
        return 0
    return int(round(float(value)))


def net_result_phrase(value):
    if value > 0:
        return f"net increase of {fmt_voters(value)}"
    if value < 0:
        return f"net loss of {fmt_voters(abs(value))}"
    return "no net change"


def category_label_for_net(label):
    if label == "Third-party and unaffiliated":
        return "The third-party and unaffiliated category"
    return label


def build_switcher_sentence(switcher_row):
    if not switcher_row:
        return None

    total_switch = switch_count(switcher_row, "total_switch")

    d_to_r = switch_count(switcher_row, "D_to_R")
    d_to_oth = switch_count(switcher_row, "D_to_Oth")

    r_to_d = switch_count(switcher_row, "R_to_D")
    r_to_oth = switch_count(switcher_row, "R_to_Oth")

    oth_to_d = switch_count(switcher_row, "Oth_to_D")
    oth_to_r = switch_count(switcher_row, "Oth_to_R")

    d_net = switch_count(switcher_row, "D_net")
    r_net = switch_count(switcher_row, "R_net")
    oth_net = switch_count(switcher_row, "Oth_net")

    if total_switch == 0:
        return (
            "Since the 2024 presidential election, no voters moved between the Democratic, "
            "Republican and third-party or unaffiliated registration categories."
        )

    rows = [
        {
            "label": "Republicans",
            "gain": d_to_r + oth_to_r,
            "loss": r_to_d + r_to_oth,
            "net": r_net,
        },
        {
            "label": "Democrats",
            "gain": r_to_d + oth_to_d,
            "loss": d_to_r + d_to_oth,
            "net": d_net,
        },
        {
            "label": "Third-party and unaffiliated",
            "gain": d_to_oth + r_to_oth,
            "loss": oth_to_d + oth_to_r,
            "net": oth_net,
        },
    ]

    gain_rows = [r for r in rows if r["net"] > 0]
    if gain_rows:
        lead = max(gain_rows, key=lambda r: r["net"])
        lead_sentence = (
            f"{category_label_for_net(lead['label'])} had the largest net gain, "
            f"adding {fmt_voters(lead['gain'])} from other categories while losing {lead['loss']:,}, "
            f"for a {net_result_phrase(lead['net'])}."
        )
        remaining = [r for r in rows if r["label"] != lead["label"]]
    else:
        lead_sentence = "No category posted a net gain."
        remaining = rows

    detail_sentences = []
    for row in remaining:
        label = category_label_for_net(row["label"])
        if row["label"] == "Third-party and unaffiliated":
            detail_sentences.append(
                f"{label} added {fmt_voters(row['gain'])} and lost {row['loss']:,}, "
                f"for a {net_result_phrase(row['net'])}."
            )
        else:
            detail_sentences.append(
                f"{label} added {fmt_voters(row['gain'])} but lost {row['loss']:,}, "
                f"for a {net_result_phrase(row['net'])}."
            )

    return (
        f"Since the 2024 presidential election, {total_switch:,} voters moved between Democratic, "
        f"Republican and third-party or unaffiliated registration categories. "
        + " ".join([lead_sentence] + detail_sentences)
    )


def first_registration_place_phrase(geo_label, name):
    noun = geography_noun(geo_label)

    if noun == "county":
        return "and are now registered in Bucks County"
    if noun == "municipality":
        return f"and are now registered in {name}"
    if noun == "polling place":
        return "and are assigned to this polling place"
    if noun == "precinct":
        return "and are now registered in this precinct"
    if noun == "state House district":
        return "and are now registered in this state House district"
    if noun == "state Senate district":
        return "and are now registered in this state Senate district"

    return "and are now registered here"


def participation_subject_phrase(geo_label, name):
    noun = geography_noun(geo_label)

    if noun == "county":
        return "currently registered Bucks County voters"
    if noun == "municipality":
        return f"currently registered voters in {name}"
    if noun == "polling place":
        return "currently registered voters assigned to this polling place"
    if noun == "precinct":
        return "currently registered voters in this precinct"
    if noun == "state House district":
        return "currently registered voters in this state House district"
    if noun == "state Senate district":
        return "currently registered voters in this state Senate district"

    return "currently registered voters here"


def build_participation_sentence(geo_label, name, participation_row=None):
    if not participation_row:
        return None

    reg_d = participation_row.get("registered_current_year_D")
    reg_r = participation_row.get("registered_current_year_R")
    reg_oth = participation_row.get("registered_current_year_Oth")
    reg_total = participation_row.get("registered_current_year_total")

    participation_pct = participation_row.get("participation_pct")
    primary_pct = participation_row.get("primary_participation_pct")
    general_pct = participation_row.get("general_participation_pct")
    midterm_primary_pct = participation_row.get("midterm_primary_participation_pct")

    registration_sentence = (
        f"Since Jan. 1, {fmt_voters(reg_total)} have registered for the first time in Pennsylvania "
        f"{first_registration_place_phrase(geo_label, name)}, including {fmt_int(reg_d)} Democrats, "
        f"{fmt_int(reg_r)} Republicans and {fmt_int(reg_oth)} third-party or unaffiliated voters."
    )

    subject = participation_subject_phrase(geo_label, name)

    participation_sentence = (
        f"According to voter-file history, {subject} participated in "
        f"{fmt_percent_text(midterm_primary_pct)} of the midterm primaries since 2020 for which they were registered early enough to vote. "
        f"Overall, those voters participated in {fmt_percent_text(participation_pct)} of eligible elections since 2020, "
        f"with higher participation in general elections at {fmt_percent_text(general_pct)} and lower participation "
        f"in primaries at {fmt_percent_text(primary_pct)}."
    )

    return registration_sentence + "\n\n" + participation_sentence


def build_summary(geo_label, party_row, turnout_row=None, switcher_row=None, participation_row=None):
    name = party_row.get("_display_name") or party_row.get("_key_value") or "This area"
    noun = geography_noun(geo_label)

    total = fmt_int(party_row.get("total_voters"))
    d_count = fmt_int(party_row.get("D"))
    r_count = fmt_int(party_row.get("R"))
    oth_count = fmt_int(party_row.get("Oth"))

    dvr = party_row.get("DvR")
    dvr_pct = party_row.get("DvR_pct")

    leader = party_leader(party_row)

    if leader == "Democrats and Republicans are tied":
        lead_sentence = (
            f"{name} has {total} {registered_voter_phrase(geo_label)}, "
            f"with Democrats and Republicans tied in registration, according to state voter registration data."
        )
        margin_sentence = (
            f"{place_registration_phrase(geo_label, name)} has {r_count} registered Republicans, "
            f"{d_count} Democrats and {oth_count} third-party or unaffiliated voters."
        )
    elif leader == "Democrats":
        strength = margin_strength(abs(dvr_pct))
        lead_sentence = (
            f"{name} has {total} {registered_voter_phrase(geo_label)}, "
            f"with Democrats holding a {strength}registration edge over Republicans, according to state voter registration data."
        )
        margin_sentence = (
            f"{place_registration_phrase(geo_label, name)} has {d_count} registered Democrats, "
            f"{r_count} Republicans and {oth_count} third-party or unaffiliated voters. "
            f"Democrats' advantage stands at {fmt_int(abs(dvr))} voters, or {float(abs(dvr_pct)):.1f} percentage points."
        )
    else:
        strength = margin_strength(abs(dvr_pct))
        lead_sentence = (
            f"{name} has {total} {registered_voter_phrase(geo_label)}, "
            f"with Republicans holding a {strength}registration edge over Democrats, according to state voter registration data."
        )
        margin_sentence = (
            f"{place_registration_phrase(geo_label, name)} has {r_count} registered Republicans, "
            f"{d_count} Democrats and {oth_count} third-party or unaffiliated voters. "
            f"Republicans' advantage stands at {fmt_int(abs(dvr))} voters, or {float(abs(dvr_pct)):.1f} percentage points."
        )

    lines = [
        lead_sentence,
        margin_sentence,
    ]

    if turnout_row:
        if geography_noun(geo_label) == "county":
            turnout_subject = "currently registered Bucks County voters"
        elif geography_noun(geo_label) == "polling place":
            turnout_subject = "currently registered voters assigned to this polling place"
        elif geography_noun(geo_label) == "precinct":
            turnout_subject = "currently registered voters in this precinct"
        elif geography_noun(geo_label) == "state House district":
            turnout_subject = "currently registered voters in this state House district"
        elif geography_noun(geo_label) == "state Senate district":
            turnout_subject = "currently registered voters in this state Senate district"
        elif geography_noun(geo_label) == "municipality":
            turnout_subject = f"currently registered voters in {name}"
        else:
            turnout_subject = "currently registered voters here"

        lines.append(
            f"About {fmt_percent_text(turnout_row.get('turnout_pct'))} of {turnout_subject} cast ballots "
            f"in the 2025 municipal election. That includes {fmt_percent_text(turnout_row.get('D_turnout_pct'))} "
            f"of currently registered Democrats, {fmt_percent_text(turnout_row.get('R_turnout_pct'))} of Republicans "
            f"and {fmt_percent_text(turnout_row.get('Oth_turnout_pct'))} of third-party and unaffiliated voters."
        )

    participation_sentence = build_participation_sentence(
        geo_label=geo_label,
        name=name,
        participation_row=participation_row,
    )
    if participation_sentence:
        lines.append(participation_sentence)

    switcher_sentence = build_switcher_sentence(switcher_row)
    if switcher_sentence:
        lines.append(switcher_sentence)

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

                # County party file uses "county"; turnout file uses "county_1".
                # Add a county alias so county summaries can attach turnout stats.
                if geo_type == "county" and "county" not in turnout_df.columns and "county_1" in turnout_df.columns:
                    turnout_df["county"] = turnout_df["county_1"]

        switcher_df = None
        if config["switcher_file"]:
            switcher_path = SOURCE_DIR / config["switcher_file"]
            if switcher_path.exists():
                switcher_df = pd.read_csv(switcher_path, low_memory=False)

                # County party file uses "county"; switcher file uses "county_1".
                # Add a county alias so county summaries can attach switcher stats.
                if geo_type == "county" and "county" not in switcher_df.columns and "county_1" in switcher_df.columns:
                    switcher_df["county"] = switcher_df["county_1"]

        participation_df = None
        if config.get("participation_file"):
            participation_path = SOURCE_DIR / config["participation_file"]
            if participation_path.exists():
                participation_df = pd.read_csv(participation_path, low_memory=False)

                # County party file uses "county"; participation file uses "county_1".
                if geo_type == "county" and "county" not in participation_df.columns and "county_1" in participation_df.columns:
                    participation_df["county"] = participation_df["county_1"]

        records = []

        for _, party_series in party_df.iterrows():
            party_row = row_to_dict(party_series)

            key_value = party_row.get(key)
            if key_value is None:
                continue

            display_name = party_row.get(display_col) or key_value

            if geo_type == "county" and str(display_name).strip().lower() == "bucks":
                display_name = "Bucks County"

            if geo_type == "polling_place":
                address = party_row.get("full_address")
                post_office = party_row.get("post_office")
                if address and post_office:
                    display_name = f"{display_name}, {address}, {post_office}"

            if geo_type == "state_house":
                display_name = f"State House District {clean_legislative_district_id(display_name)}"

            if geo_type == "state_senate":
                display_name = f"State Senate District {clean_legislative_district_id(display_name)}"

            if geo_type == "precinct":
                muni = party_row.get("municipality")
                if muni:
                    display_name = f"{display_name} ({muni})"

            party_row["_key_value"] = str(key_value)
            party_row["_display_name"] = str(display_name)

            turnout_row = find_matching_row(turnout_df, key, key_value)

            switcher_row = find_matching_row(switcher_df, key, key_value)

            participation_row = find_matching_row(participation_df, key, key_value)

            summary = build_summary(
                geo_label=config["label"],
                party_row=party_row,
                turnout_row=turnout_row,
                switcher_row=switcher_row,
                participation_row=participation_row,
            )

            records.append({
                "key": str(key_value),
                "display": str(display_name),
                "party": party_row,
                "turnout": turnout_row,
                "switcher": switcher_row,
                "participation": participation_row,
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