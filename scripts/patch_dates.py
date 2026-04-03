import os

date_map = {
    "Tamil Nadu": "2026-04-23",
    "Kerala": "2026-04-09",
    "Puducherry": "2026-04-09",
    "Assam": "2026-04-09",
    "West Bengal": "2026-04-23 / 2026-04-29"
}

def patch_dates(input_file, output_file):
    print(f"Patching {input_file} (streaming)...")
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        
        has_assam = False
        has_wb = False
        
        current_state = None
        for line in f_in:
            if "state:" in line:
                for state in date_map:
                    if f": {state}" in line or f": '{state}'" in line or f": \"{state}\"" in line:
                        current_state = state
                        if state == "Assam": has_assam = True
                        if state == "West Bengal": has_wb = True
                        break
            
            # Efficiently replace empty details or existing date
            if "election_details: {}" in line and current_state:
                f_out.write("  election_details:\n")
                f_out.write(f"    voting_date: '{date_map[current_state]}'\n")
            elif "voting_date:" in line and current_state:
                f_out.write(f"    voting_date: '{date_map[current_state]}'\n")
            else:
                f_out.write(line)

        # Append skeleton entries if missing
        if not has_assam:
            f_out.write("- station_id: AS_GHY_PLAN_001\n")
            f_out.write("  state: Assam\n")
            f_out.write("  state_code: AS\n")
            f_out.write("  district: Kamrup Metropolitan\n")
            f_out.write("  name: Planning - Guwahati Central Station\n")
            f_out.write("  address: Guwahati, Assam\n")
            f_out.write("  election_details:\n")
            f_out.write("    voting_date: '2026-04-09'\n")
            f_out.write("  metadata:\n")
            f_out.write("    needs_update: true\n")
            f_out.write("    data_source: Plan_2026\n")

        if not has_wb:
            f_out.write("- station_id: WB_KOL_PLAN_001\n")
            f_out.write("  state: West Bengal\n")
            f_out.write("  state_code: WB\n")
            f_out.write("  district: Kolkata\n")
            f_out.write("  name: Planning - Kolkata North Station\n")
            f_out.write("  address: Kolkata, West Bengal\n")
            f_out.write("  election_details:\n")
            f_out.write("    voting_date: '2026-04-23 / 2026-04-29'\n")
            f_out.write("  metadata:\n")
            f_out.write("    needs_update: true\n")
            f_out.write("    data_source: Plan_2026\n")

    print("Success. Renaming temp file...")
    os.replace(output_file, input_file)

if __name__ == "__main__":
    patch_dates("data/polling_stations.yml", "data/polling_stations.yml.tmp")
