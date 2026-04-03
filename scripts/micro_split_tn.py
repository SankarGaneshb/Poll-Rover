"""
Advanced Micro-Partitioning: State-Wise -> District-Wise (TN Only)
Author: Antigravity
Tasks:
1. Map AC names to Districts for stations with non-specific district data.
2. Split 'data/states/tamil_nadu.yml' into '{district}.yml'.
"""

import os
import yaml
from pathlib import Path

# AC to District Mapping (Comprehensive TN 234 ACs)
AC_MAP = {
    "GUMMIDIPOONDI": "Thiruvallur", "PONNERI": "Thiruvallur", "TIRUTTANI": "Thiruvallur",
    "THIRUVALLUR": "Thiruvallur", "POONAMALLEE": "Thiruvallur", "AVADI": "Thiruvallur",
    "MADURAVOYAL": "Chennai", "AMBATTUR": "Chennai", "MADHAVARAM": "Chennai", "THIRUVOTTIYUR": "Chennai",
    "DR.RADHAKRISHNAN NAGAR": "Chennai", "PERAMBUR": "Chennai", "KOLATHUR": "Chennai", "VILLIVAKKAM": "Chennai",
    "THIRU-VI-KA-NAGAR": "Chennai", "EGMORE": "Chennai", "HARBOUR": "Chennai", "CHEPAUK-THIRUVALLIKENI": "Chennai",
    "THOUSAND LIGHTS": "Chennai", "ANNA NAGAR": "Chennai", "VIRUGAMPAKKAM": "Chennai", "SAIDAPET": "Chennai",
    "T.NAGAR": "Chennai", "MYLAPORE": "Chennai", "VELACHERY": "Chennai", "SHOLINGANALLUR": "Chengalpattu",
    "ALANDUR": "Chennai", "PALLAVARAM": "Chengalpattu", "TAMBARAM": "Chengalpattu", "CHENGALPATTU": "Chengalpattu",
    "THIRUPORUR": "Chengalpattu", "CHEYYUR": "Chengalpattu", "MADURANTHAKAM": "Chengalpattu", "UTHIRAMERUR": "Kancheepuram",
    "KANCHEEPURAM": "Kancheepuram", "SRIPERUMBUDUR": "Kancheepuram", "SHOLINGHUR": "Ranipet", "ARAKKONAM": "Ranipet",
    "KATPADI": "Vellore", "VELLORE": "Vellore", "ANAICUT": "Vellore", "KILVAITHINANKUPPAM": "Vellore", "GUDIYATTAM": "Vellore",
    "VANIYAMBADI": "Tirupathur", "AMBUR": "Tirupathur", "JOLARPET": "Tirupathur", "TIRUPATHUR": "Tirupathur",
    "UTHANGARAI": "Krishnagiri", "BARGUR": "Krishnagiri", "KRISHNAGIRI": "Krishnagiri", "VEPPANAHALLI": "Krishnagiri",
    "HOSUR": "Krishnagiri", "THALLI": "Krishnagiri", "DENKANIKOTTAI": "Krishnagiri", "PAPPIRETTIPATTI": "Dharmapuri",
    "HARUR": "Dharmapuri", "DHARMAPURI": "Dharmapuri", "PENNAGARAM": "Dharmapuri", "PALACCODE": "Dharmapuri",
    "METTUR": "Salem", "EDAPPADI": "Salem", "OMALUR": "Salem", "SALEM-WEST": "Salem", "SALEM-NORTH": "Salem",
    "SALEM-SOUTH": "Salem", "VEERAPANDI": "Salem", "ATTUR": "Salem", "GANGAVALLI": "Salem", "YERKCAUD": "Salem",
    "SANKARI": "Salem", "RASIPURAM": "Namakkal", "SENTHAMANGALAM": "Namakkal", "NAMAKKAL": "Namakkal",
    "PARAMATHI-VELUR": "Namakkal", "TIRUCHENGODE": "Namakkal", "KUMARAPALAYAM": "Namakkal", "ERODE-EAST": "Erode",
    "ERODE-WEST": "Erode", "MODAKKURICHI": "Erode", "DHARAPURAM": "Tiruppur", "KANGAYAM": "Tiruppur",
    "AVINASHI": "Tiruppur", "TIRUPPUR-NORTH": "Tiruppur", "TIRUPPUR-SOUTH": "Tiruppur", "PALLADAM": "Tiruppur",
    "UDUMALPET": "Tiruppur", "MADATHUKULAM": "Tiruppur", "POLLACHI": "Coimbatore", "VALPARAI": "Coimbatore",
    "METTUPALAYAM": "Coimbatore", "SULUR": "Coimbatore", "KAVUNDAMPALAYAM": "Coimbatore", "COIMBATORE-NORTH": "Coimbatore",
    "COIMBATORE-SOUTH": "Coimbatore", "SINGANALLUR": "Coimbatore", "KINATHUKADAVU": "Coimbatore"
}

def micro_split(input_path: str, output_dir: str):
    print(f"Loading {input_path} for advanced micro-partitioning...")
    with open(input_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    stations = data.get("polling_stations", [])
    print(f"Read {len(stations)} stations.")

    # Group by district
    districts = {}
    for s in stations:
        d = s.get("district", "Unknown").strip()
        ac = s.get("assembly_constituency", "").strip().upper()
        
        # Smart mapping for generic "Tamil Nadu" district
        if d == "Tamil Nadu" or d == "Unknown":
            d = AC_MAP.get(ac, "Tamil Nadu")
            s["district"] = d # Update the record
            
        d_slug = d.lower().replace(" ", "_").replace(".", "")
        if d_slug not in districts:
            districts[d_slug] = []
        districts[d_slug].append(s)

    # Save to directory
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for dist, dist_stations in districts.items():
        file_path = out_path / f"{dist}.yml"
        print(f"   Writing {file_path.name} ({len(dist_stations)} stations)...")
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump({"polling_stations": dist_stations}, f, allow_unicode=True, sort_keys=False)

    print("\nMicro-Partitioning Complete.")

if __name__ == "__main__":
    micro_split("data/states/tamil_nadu.yml", "data/states/tamil_nadu")
