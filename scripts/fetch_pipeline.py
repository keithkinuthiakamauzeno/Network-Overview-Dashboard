"""
Fetches the Pipeline sheet from Google Sheets.
Selects only the wanted columns by HEADER NAME (position-independent).
Writes to data/pipeline.csv.
Run by GitHub Actions every hour.
"""
import os, json, csv
import gspread
from google.oauth2.service_account import Credentials

SHEET_ID   = "1f62GuO3lSUTYCVALnC_yGiXD58upbpj_JPLJFsG7oUs"
SHEET_NAME = "Pipeline"
OUTPUT     = "data/pipeline.csv"

# Columns to keep — by header name, order-independent
WANTED_COLS = [
    "Issue Type", "Key", "Summary", "Assignee", "Reporter", "Priority",
    "Technical Survey Completion Date", "Lease Signed Date", "Go Live Date",
    "Deployment Lead", "Development Lead", "Fast Chargers", "Swap Stations",
    "Site partner name", "Site partner contact type", "Site partner phone number",
    "Comment", "Construction cost total estimate (KES)", "Scouting report",
    "Technical Assessment Report Link", "Total rent (KES)",
    "Latitude", "Longitude",
    # Keep these for status/filtering on left sidebar
    "Status", "Resolution", "Created", "Updated", "Due date",
    "Billed on EV Tariff",
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Load credentials from GitHub Secret (JSON string)
creds_json = os.environ.get("GSHEETS_CREDS", "")
if not creds_json:
    raise ValueError("GSHEETS_CREDS secret not set")

creds_info = json.loads(creds_json)
creds      = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
client     = gspread.authorize(creds)

print(f"Fetching '{SHEET_NAME}' from sheet {SHEET_ID}...")
ws   = client.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
rows = ws.get_all_values()

if not rows:
    raise ValueError("Sheet is empty")

headers = [h.strip() for h in rows[0]]
print(f"  Sheet headers ({len(headers)}): {headers[:10]}...")

# Map wanted column names to their actual positions
col_idx = {}
for wanted in WANTED_COLS:
    for i, h in enumerate(headers):
        if h.strip() == wanted:
            col_idx[wanted] = i
            break
    # Fuzzy match for trailing spaces or case
    if wanted not in col_idx:
        for i, h in enumerate(headers):
            if h.strip().lower() == wanted.lower():
                col_idx[wanted] = i
                break

found   = [c for c in WANTED_COLS if c in col_idx]
missing = [c for c in WANTED_COLS if c not in col_idx]
print(f"  Found {len(found)} / {len(WANTED_COLS)} columns")
if missing:
    print(f"  Missing (will be blank): {missing}")

# Write CSV with only the wanted columns in our defined order
os.makedirs("data", exist_ok=True)
# Find last non-empty row — stops at first fully blank row after data
last_data_row = 1  # start after header
for i, row in enumerate(rows[1:], start=1):
    if any(cell.strip() for cell in row):
        last_data_row = i
data_rows = rows[1:last_data_row + 1]
print(f"  Data rows (non-blank): {len(data_rows)}")

with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(found)  # header — only columns we found
    written = 0
    for row in data_rows:
        # Skip rows where Status is blank
        status_idx = col_idx.get("Status")
        status_val = row[status_idx].strip() if status_idx is not None and status_idx < len(row) else ""
        if not status_val:
            continue
        out_row = []
        for col in found:
            idx = col_idx[col]
            val = row[idx].strip() if idx < len(row) else ""
            out_row.append(val)
        writer.writerow(out_row)
        written += 1
    print(f"  Rows written (with Status): {written}")

print(f"  Written {OUTPUT}")
