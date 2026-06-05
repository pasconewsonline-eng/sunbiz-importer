#!/usr/bin/env python3
"""Sunbiz Daily New-Business Importer for Pasco County News"""
import os, sys, io, json, re, requests, paramiko

WP_ENDPOINT = os.environ.get("WP_ENDPOINT", "").strip()
WP_KEY      = os.environ.get("WP_KEY", "").strip()
SFTP_HOST, SFTP_USER, SFTP_PASS = "sftp.floridados.gov", "Public", "PubAccess1845!"

PASCO_CITIES = {
    "NEW PORT RICHEY","PORT RICHEY","HUDSON","LAND O LAKES","LAND O' LAKES",
    "LAND O'LAKES","WESLEY CHAPEL","ZEPHYRHILLS","DADE CITY","TRINITY",
    "HOLIDAY","LUTZ","ODESSA","SAN ANTONIO","SHADY HILLS","BAYONET POINT",
    "ELFERS","ARIPEKA","CRYSTAL SPRINGS","SAINT LEO","ST LEO","ST. LEO",
}
TYPE_MAP = {
    "DOMP":"FL Corporation","DOMNP":"FL Non-Profit","FORP":"Foreign Corporation",
    "FORNP":"Foreign Non-Profit","DOMLP":"FL Limited Partnership",
    "FORLP":"Foreign Limited Partnership","FLAL":"Florida LLC","FORL":"Foreign LLC",
    "NPREG":"Non-Profit Registration","TRUST":"Declaration of Trust","AGENT":"Registered Agent",
}

def field(line, start, length):
    return line[start-1:start-1+length].strip()

def norm_city(c):
    return re.sub(r"\s+", " ", c.upper().replace(".", "")).strip()

PASCO_NORM = { norm_city(c) for c in PASCO_CITIES }

def parse_date(rd):
    # Sunbiz file date is MMDDYYYY (e.g. 05272026 -> 2026-05-27)
    if len(rd) == 8 and rd.isdigit():
        mm, dd, yyyy = rd[0:2], rd[2:4], rd[4:8]
        return f"{yyyy}-{mm}-{dd}"
    return ""

def parse_corporate_line(line):
    if len(line) < 480: return None
    if field(line,205,1) != "A": return None
    city_raw = field(line,305,28)
    if norm_city(city_raw) not in PASCO_NORM: return None
    code = field(line,206,15).strip()
    return {
        "doc_number": field(line,1,12), "name": field(line,13,192),
        "entity_type": TYPE_MAP.get(code, code or "Business Filing"),
        "filing_date": parse_date(field(line,473,8)),
        "city": city_raw.title(), "county":"PASCO",
        "address": field(line,221,42).title(),
        "registered_agent": field(line,545,42).title(), "owner":"",
    }

def main():
    if not WP_ENDPOINT or not WP_KEY:
        print("ERROR: secrets missing."); sys.exit(1)
    print("Connecting to Sunbiz SFTP...")
    tr = paramiko.Transport((SFTP_HOST,22)); tr.connect(username=SFTP_USER,password=SFTP_PASS)
    sftp = paramiko.SFTPClient.from_transport(tr)
    def list_dir(p):
        try: return sftp.listdir(p)
        except Exception: return []
    cor_path = None
    for base in ["doc/cor","./doc/cor","Public/doc/cor","/Public/doc/cor"]:
        if list_dir(base): cor_path = base; break
    cor_files = list_dir(cor_path) if cor_path else []
    dated = sorted([f for f in cor_files if re.match(r"^\d{8}[a-zA-Z]?\.txt$", f, re.I)])
    all_records = []
    if dated:
        target = cor_path.rstrip("/") + "/" + dated[-1]
        print(f"Using newest corporate data file: {target}")
        buf = io.BytesIO(); sftp.getfo(target, buf)
        text = buf.getvalue().decode("latin-1", errors="replace")
        for line in text.splitlines():
            rec = parse_corporate_line(line)
            if rec: all_records.append(rec)
    sftp.close(); tr.close()
    print(f"Matched {len(all_records)} Pasco-area filings.")
    for r in all_records[:10]:
        print(f"   {r['name']} — {r['city']} — {r['entity_type']} — {r['filing_date']}")
    if not all_records:
        print("Nothing to send today."); return
    print("Posting to WordPress...")
    headers = {
        "x-pcn-key": WP_KEY,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; PascoCountyNewsBot/1.0)",
        "Accept": "application/json",
    }
    resp = requests.post(WP_ENDPOINT, headers=headers,
                         data=json.dumps(all_records), timeout=60)
    print("WordPress response:", resp.status_code, resp.text[:200])
    if "sgcaptcha" in resp.text or resp.status_code in (401,403):
        print("\n*** SiteGround bot-protection blocked the request. ***")
        print("Fix: in SiteGround Site Tools -> Security -> Bot Defense / WAF,")
        print("allowlist the path /wp-json/pcn-nb/v1/import (or disable challenge for it).")

if __name__ == "__main__":
    main()
