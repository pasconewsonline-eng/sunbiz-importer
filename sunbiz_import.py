#!/usr/bin/env python3
"""
Sunbiz Daily New-Business Importer for Pasco County News
Writes matched Pasco filings to data/latest.json in the repo.
WordPress then PULLS that file (avoids SiteGround's inbound firewall).
"""
import os, sys, io, json, re, datetime, paramiko

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
    if len(rd) == 8 and rd.isdigit():
        return f"{rd[4:8]}-{rd[0:2]}-{rd[2:4]}"
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

    # Write results to data/latest.json (WordPress will pull this)
    os.makedirs("data", exist_ok=True)
    payload = {
        "generated": datetime.datetime.utcnow().isoformat() + "Z",
        "source_file": dated[-1] if dated else "",
        "count": len(all_records),
        "filings": all_records,
    }
    with open("data/latest.json", "w") as f:
        json.dump(payload, f, indent=2)
    print("Wrote data/latest.json")

if __name__ == "__main__":
    main()
