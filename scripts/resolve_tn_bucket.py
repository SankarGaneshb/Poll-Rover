"""
Resolve the 'Tamil Nadu' catch-all bucket in data/states/tamil_nadu/tamil_nadu.yml.
This reads that file, maps each station to the correct district using an expanded
AC keyword lookup, appends to the appropriate district file, and deletes the bucket.
"""

import yaml
import re
from pathlib import Path

# Expanded keyword => district mapping (covers all known variance formats)
KEYWORD_DISTRICT = {
    # Thiruvallur
    "gummidipoondi": "Thiruvallur", "ponneri": "Thiruvallur", "tiruttani": "Thiruvallur",
    "thiruvallur": "Thiruvallur", "poonamallee": "Thiruvallur", "avadi": "Thiruvallur",
    # Chennai
    "madavaram": "Chennai", "madhavaram": "Chennai", "maduravoyal": "Chennai",
    "ambattur": "Chennai", "thiruvottiyur": "Chennai", "dr.radhakrishnan": "Chennai",
    "radhakrishnan": "Chennai", "perambur": "Chennai", "kolathur": "Chennai",
    "villivakkam": "Chennai", "thiru-vi-ka": "Chennai", "egmore": "Chennai",
    "harbour": "Chennai", "chepauk": "Chennai", "thousand lights": "Chennai",
    "anna nagar": "Chennai", "virugampakkam": "Chennai", "saidapet": "Chennai",
    "t.nagar": "Chennai", "mylapore": "Chennai", "velachery": "Chennai",
    "alandur": "Chennai",
    # Chengalpattu
    "sholinganallur": "Chengalpattu", "shozhinganallur": "Chengalpattu",
    "pallavaram": "Chengalpattu", "pallavam": "Chengalpattu",
    "tambaram": "Chengalpattu", "chengalpattu": "Chengalpattu",
    "thiruporur": "Chengalpattu", "cheyyur": "Chengalpattu",
    "maduranthakam": "Chengalpattu", "madurantakam": "Chengalpattu",
    # Kancheepuram
    "uthiramerur": "Kancheepuram", "kancheepuram": "Kancheepuram",
    "sriperumbudur": "Kancheepuram",
    # Ranipet
    "arakkonam": "Ranipet", "sholinghur": "Ranipet",
    # Vellore
    "katpadi": "Vellore", "vellore": "Vellore", "anaicut": "Vellore",
    "kilvaithinankuppam": "Vellore", "gudiyattam": "Vellore",
    # Tirupathur
    "vaniyambadi": "Tirupathur", "ambur": "Tirupathur",
    "jolarpet": "Tirupathur", "tirupathur": "Tirupathur",
    # Krishnagiri
    "uthangarai": "Krishnagiri", "bargur": "Krishnagiri",
    "krishnagiri": "Krishnagiri", "veppanahalli": "Krishnagiri",
    "hosur": "Krishnagiri", "thalli": "Krishnagiri",
    "denkanikottai": "Krishnagiri",
    # Dharmapuri
    "pappirettipatti": "Dharmapuri", "harur": "Dharmapuri",
    "dharmapuri": "Dharmapuri", "pennagaram": "Dharmapuri", "palaccode": "Dharmapuri",
    # Salem
    "mettur": "Salem", "edappadi": "Salem", "omalur": "Salem",
    "salem": "Salem", "veerapandi": "Salem", "attur": "Salem",
    "gangavalli": "Salem", "yerkcaud": "Salem", "yercaud": "Salem",
    "sankari": "Salem",
    # Namakkal
    "rasipuram": "Namakkal", "senthamangalam": "Namakkal",
    "namakkal": "Namakkal", "paramathi": "Namakkal",
    "tiruchengode": "Namakkal", "kumarapalayam": "Namakkal",
    # Erode
    "erode": "Erode", "modakkurichi": "Erode",
    # Tiruppur
    "dharapuram": "Tiruppur", "kangayam": "Tiruppur", "avinashi": "Tiruppur",
    "tiruppur": "Tiruppur", "tirupur": "Tiruppur", "palladam": "Tiruppur",
    "udumalpet": "Tiruppur", "udumalaipettai": "Tiruppur",
    "madathukulam": "Tiruppur",
    # Coimbatore
    "pollachi": "Coimbatore", "valparai": "Coimbatore",
    "mettupalayam": "Coimbatore", "sulur": "Coimbatore",
    "kavundampalayam": "Coimbatore", "coimbatore": "Coimbatore",
    "singanallur": "Coimbatore", "kinathukadavu": "Coimbatore",
    "thondamuthur": "Coimbatore",
    # Nilgiris
    "nilgiris": "Nilgiris", "ooty": "Nilgiris", "gudalur": "Nilgiris",
    "coonoor": "Nilgiris", "udhagamandalam": "Nilgiris",
    # Dindigul
    "dindigul": "Dindigul", "palani": "Dindigul",
    "oddanchatram": "Dindigul", "nilakottai": "Dindigul",
    # Karur
    "karur": "Karur", "manapparai": "Karur", "kulithalai": "Karur", "aravakurichi": "Karur",
    # Tiruchirappalli (Trichy)
    "tiruchirappalli": "Tiruchirappalli", "trichy": "Tiruchirappalli",
    "srirangam": "Tiruchirappalli", "thiruverumbur": "Tiruchirappalli",
    "lalgudi": "Tiruchirappalli", "manachanallur": "Tiruchirappalli",
    "musiri": "Tiruchirappalli",
    # Perambalur
    "perambalur": "Perambalur", "jayankondam": "Perambalur",
    "ariyalur": "Ariyalur",
    # Cuddalore
    "cuddalore": "Cuddalore", "kurinjipadi": "Cuddalore", "bhuvanagiri": "Cuddalore",
    "chidambaram": "Cuddalore", "kattumannarkoil": "Cuddalore", "virudhachalam": "Cuddalore",
    "panruti": "Cuddalore",
    # Mayiladuthurai
    "mayiladuthurai": "Mayiladuthurai", "sirkazhi": "Mayiladuthurai",
    "poompuhar": "Mayiladuthurai", "nagapattinam": "Nagapattinam",
    "vedaranyam": "Nagapattinam", "kilvelur": "Nagapattinam",
    # Tiruvarur
    "tiruvarur": "Tiruvarur", "papanasam": "Tiruvarur",
    # Thanjavur
    "thanjavur": "Thanjavur", "orathanadu": "Thanjavur",
    "cumbum": "Theni", "andipatti": "Theni", "theni": "Theni", "periyakulam": "Theni",
    # Pudukkottai
    "pudukkottai": "Pudukkottai", "gandarvakottai": "Pudukkottai",
    "alangudi": "Pudukkottai", "aranthangi": "Pudukkottai",
    # Sivaganga
    "sivaganga": "Sivaganga", "manamadurai": "Sivaganga",
    "tiruppuvanam": "Sivaganga",
    # Madurai
    "madurai": "Madurai",
    # Ramanathapuram
    "ramanathapuram": "Ramanathapuram", "mudukulathur": "Ramanathapuram",
    "paramakudi": "Ramanathapuram",
    # Virdudhunagar
    "virudhunagar": "Virudhunagar", "sivakasi": "Virudhunagar",
    "sattur": "Virudhunagar", "rajapalayam": "Virudhunagar",
    "srivilliputhur": "Virudhunagar", "tiruchuli": "Virudhunagar",
    # Tirunelveli
    "tirunelveli": "Tirunelveli", "nanguneri": "Tirunelveli",
    "palayamkottai": "Tirunelveli", "ambasamudram": "Tirunelveli",
    # Tenkasi
    "tenkasi": "Tenkasi", "alangulam": "Tenkasi", "vasudevanallur": "Tenkasi",
    "sen thenkasi": "Tenkasi", "shenkottai": "Tenkasi",
    # Kanyakumari
    "colachel": "Kanyakumari", "padmanabhapuram": "Kanyakumari",
    "vilavancode": "Kanyakumari", "killiyoor": "Kanyakumari",
    "nagercoil": "Kanyakumari", "thiruvattar": "Kanyakumari",
}

def slug(name):
    return name.strip().lower().replace(" ", "_").replace(".", "").replace("-", "_")

def map_to_district(ac_str):
    ac_lower = ac_str.lower()
    for keyword, district in KEYWORD_DISTRICT.items():
        if keyword in ac_lower:
            return district
    return None

def resolve_bucket():
    bucket_path = Path("data/states/tamil_nadu/tamil_nadu.yml")
    if not bucket_path.exists():
        print("No bucket file found - already resolved!")
        return

    print(f"Loading bucket file ({bucket_path.stat().st_size / 1e6:.1f} MB)...")
    with open(bucket_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    stations = data.get("polling_stations", [])
    print(f"  Bucket has {len(stations)} stations")

    # Build a dict of existing district files
    dist_dir = Path("data/states/tamil_nadu")
    district_data = {}

    resolved = 0
    still_unknown = []

    for s in stations:
        ac = s.get("assembly_constituency", "")
        district = map_to_district(ac)

        if district:
            d_slug = slug(district)
            s["district"] = district
            if d_slug not in district_data:
                district_data[d_slug] = {"district": district, "stations": []}
            district_data[d_slug]["stations"].append(s)
            resolved += 1
        else:
            still_unknown.append(s)

    print(f"  Resolved: {resolved}, Still unknown: {len(still_unknown)}")

    # Append to existing district files
    for d_slug, info in district_data.items():
        file_path = dist_dir / f"{d_slug}.yml"
        existing = []
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                existing_data = yaml.safe_load(f)
                existing = existing_data.get("polling_stations", [])
        merged = existing + info["stations"]
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump({"polling_stations": merged}, f, allow_unicode=True, sort_keys=False)
        print(f"    Appended {len(info['stations'])} -> {file_path.name} (total: {len(merged)})")

    # Overwrite the bucket with only still-unknown
    if still_unknown:
        print(f"\n  Writing {len(still_unknown)} unresolved back to bucket...")
        with open(bucket_path, "w", encoding="utf-8") as f:
            yaml.dump({"polling_stations": still_unknown}, f, allow_unicode=True, sort_keys=False)
    else:
        print("\n  All resolved! Deleting bucket file.")
        bucket_path.unlink()

    print("Done.")

if __name__ == "__main__":
    resolve_bucket()
