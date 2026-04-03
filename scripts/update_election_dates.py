import yaml
import sys
from pathlib import Path

def update_dates(yaml_path: str):
    print(f"Reading {yaml_path}...")
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    stations = data.get("polling_stations", [])
    print(f"Updating {len(stations)} stations...")
    
    date_map = {
        "Tamil Nadu": "2026-04-23",
        "Kerala": "2026-04-09",
        "Puducherry": "2026-04-09",
        "Assam": "2026-04-09",
        "West Bengal": "2026-04-23 / 2026-04-29"
    }
    
    updated_count = 0
    for s in stations:
        state = s.get("state")
        if state in date_map:
            if "election_details" not in s:
                s["election_details"] = {}
            s["election_details"]["voting_date"] = date_map[state]
            updated_count += 1
            
    # Add skeleton entries for Assam and West Bengal if they don't exist
    existing_states = {s.get("state") for s in stations}
    if "Assam" not in existing_states:
        print("Adding skeleton entry for Assam...")
        stations.append({
            "station_id": "AS_GHY_PLAN_001",
            "state": "Assam",
            "state_code": "AS",
            "district": "Kamrup Metropolitan",
            "name": "Planning - Guwahati Central Station",
            "address": "Guwahati, Assam",
            "election_details": {"voting_date": "2026-04-09", "voting_phase": "Single"},
            "metadata": {"needs_update": True, "data_source": "Plan_2026"},
            "accessibility": {"accessibility_rating": 0}
        })
    
    if "West Bengal" not in existing_states:
        print("Adding skeleton entry for West Bengal...")
        stations.append({
            "station_id": "WB_KOL_PLAN_001",
            "state": "West Bengal",
            "state_code": "WB",
            "district": "Kolkata",
            "name": "Planning - Kolkata North Station",
            "address": "Kolkata, West Bengal",
            "election_details": {"voting_date": "2026-04-23 / 2026-04-29", "voting_phase": "Multi"},
            "metadata": {"needs_update": True, "data_source": "Plan_2026"},
            "accessibility": {"accessibility_rating": 0}
        })

    print(f"Saving {len(stations)} stations...")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump({"polling_stations": stations}, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"Successfully updated {updated_count} existing entries and added new state skeletons.")

if __name__ == "__main__":
    update_dates("data/polling_stations.yml")
