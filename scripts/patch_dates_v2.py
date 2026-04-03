import os

date_map = {
    "Tamil Nadu": "2026-04-23",
    "Kerala": "2026-04-09",
    "Puducherry": "2026-04-09",
    "Assam": "2026-04-09",
    "West Bengal": "2026-04-23 / 2026-04-29"
}

def patch_dates_v2(input_file, output_file):
    print(f"Patching {input_file} (v2 buffering block)...")
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        
        has_assam = False
        has_wb = False
        
        block = []
        for line in f_in:
            if line.startswith("- ") or (line.startswith("polling_stations:") and not block):
                if block:
                    # process the previous block
                    _process_block(block, f_out, date_map)
                    block = []
                if line.startswith("polling_stations:"):
                    f_out.write(line)
                    continue
                block.append(line)
            else:
                block.append(line)
        
        if block:
            _process_block(block, f_out, date_map)

        # Append skeleton entries if missing
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

def _process_block(block, f_out, date_map):
    current_state = None
    for line in block:
        if "state:" in line:
            for state in date_map:
                if f": {state}" in line or f": '{state}'" in line or f": \"{state}\"" in line:
                    current_state = state
                    break
    
    for line in block:
        if "election_details: {}" in line and current_state:
            f_out.write("  election_details:\n")
            f_out.write(f"    voting_date: '{date_map[current_state]}'\n")
        elif "voting_date:" in line and current_state:
            f_out.write(f"    voting_date: '{date_map[current_state]}'\n")
        else:
            f_out.write(line)

if __name__ == "__main__":
    patch_dates_v2("data/polling_stations.yml", "data/polling_stations.yml.v2.tmp")
