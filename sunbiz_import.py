#!/usr/bin/env python3
"""
Sunbiz Daily New-Business Importer for Pasco County News
--------------------------------------------------------
Downloads the latest Florida Division of Corporations (Sunbiz) daily
corporate + fictitious-name data files via SFTP, filters for Pasco-area
cities, and posts new filings to the WordPress import endpoint.

Runs on GitHub Actions (free). No code editing needed once secrets are set.
"""

import os
import sys
import io
import json
import datetime
import requests
import paramiko

# ----- CONFIG (from GitHub Secrets / environment) -----
WP_ENDPOINT = os.environ.get("WP_ENDPOINT", "").strip()      # e.g. https://pascocountynews.com/wp-json/pcn-nb/v1/import
WP_KEY      = os.environ.get("WP_KEY", "").strip()           # the import key from the plugin
SFTP_HOST   = "sftp.floridados.gov"
SFTP_USER   = "Public"
SFTP_PASS   = "PubAccess1845!"

# Pasco-area cities to keep (uppercased; Sunbiz stores city in caps)
PASCO_CITIES = {
    "NEW PORT RICHEY", "PORT RICHEY", "HUDSON", "LAND O LAKES", "LAND O' LAKES",
    "LAND O'LAKES", "WESLEY CHAPEL", "ZEPHYRHILLS", "DADE CITY", "TRINITY",
    "HOLIDAY", "LUTZ", "ODESSA", "SAN ANTONIO", "SHADY HILLS", "BAYONET POINT",
    "ELFERS", "ARIPEKA", "CRYSTAL SPRINGS", "SAINT LEO", "ST LEO",
}

# Filing type code -> friendly label
TYPE_MAP = {
    "DOMP": "FL Corporation", "DOMNP": "FL Non-Profit",
    "FORP": "Foreign Corporation", "FORNP": "Foreign Non-Profit",
    "DOMLP": "FL Limited Partnership", "FORLP": "Foreign Limited Partnership",
    "FLAL": "Florida LLC", "FORL": "Foreign LLC",
    "NPREG": "Non-Profit Registration", "TRUST": "Declaration of Trust",
    "AGENT": "Registered Agent",
}

# ----- Fixed-width field slices (start position is 1-based in the chart;
#       Python slicing is 0-based, so we subtract 1 from each start). -----
def field(line, start, length):
    return line[start - 1 : start - 1 + length].strip()

def parse_corporate_line(line):
    if len(line) < 480:
        return None
    status = field(line, 205, 1)
    state  = field(line, 333, 2)
    city   = field(line, 305, 28).upper()
    if status != "A":
        return None
    if state != "FL":
        return None
    if city not in PASCO_CITIES:
        return None
    raw_date = field(line, 473, 8)   # CCYYMMDD
    filing_date = ""
    if len(raw_date) == 8 and raw_date.isdigit():
        filing_date = f"{raw_date[0:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
    code = field(line, 206, 15).strip()
    return {
        "doc_number": field(line, 1, 12),
        "name": field(line, 13, 192),
        "entity_type": TYPE_MAP.get(code, code or "Business Filing"),
        "filing_date": filing_date,
        "city": field(line, 305, 28).title(),
        "county": "PASCO",
        "address": field(line, 221, 42).title(),
        "registered_agent": field(line, 545, 42).title(),
        "owner": "",
    }

def latest_filename(prefix_dir, sftp):
    """Find the most recent CCYYMMDDx.txt file in a directory."""
    try:
        files = sftp.listdir(prefix_dir)
    except Exception as e:
        print(f"  Could not list {prefix_dir}: {e}")
        return None
    txt = sorted([f for f in files if f.lower().endswith(".txt")])
    return (prefix_dir.rstrip("/") + "/" + txt[-1]) if txt else None

def main():
    if not WP_ENDPOINT or not WP_KEY:
        print("ERROR: WP_ENDPOINT and WP_KEY must be set as GitHub Secrets.")
        sys.exit(1)

    print("Connecting to Sunbiz SFTP...")
    transport = paramiko.Transport((SFTP_HOST, 22))
    transport.connect(username=SFTP_USER, password=SFTP_PASS)
    sftp = paramiko.SFTPClient.from_transport(transport)

    # List the public root so we can see folder names (printed for first-run discovery)
    print("Top-level directory listing:")
    try:
        for entry in sftp.listdir("."):
            print("   ", entry)
    except Exception as e:
        print("   (could not list root:", e, ")")

    # Common locations for the daily corporate file. We try several; the
    # printout above helps us confirm the real path on the first run.
    candidate_dirs = [
        "/Public/doc/cor", "/doc/cor", "/Public/Cor", "/cor",
        "/Public/CorporateData/Daily", "/CorporateData",
    ]

    all_records = []
    found_dir = None
    for d in candidate_dirs:
        path = latest_filename(d, sftp)
        if path:
            found_dir = d
            print(f"Found corporate file: {path}")
            buf = io.BytesIO()
            sftp.getfo(path, buf)
            text = buf.getvalue().decode("latin-1", errors="replace")
            for line in text.splitlines():
                rec = parse_corporate_line(line)
                if rec:
                    all_records.append(rec)
            break

    if not found_dir:
        print("Could not locate the corporate daily folder automatically.")
        print("Look at the directory listing above and tell Claude the correct path.")

    sftp.close()
    transport.close()

    print(f"Matched {len(all_records)} Pasco-area filings.")
    if not all_records:
        print("Nothing to send today.")
        return

    print("Posting to WordPress...")
    resp = requests.post(
        WP_ENDPOINT,
        headers={"x-pcn-key": WP_KEY, "Content-Type": "application/json"},
        data=json.dumps(all_records),
        timeout=60,
    )
    print("WordPress response:", resp.status_code, resp.text[:300])

if __name__ == "__main__":
    main()
