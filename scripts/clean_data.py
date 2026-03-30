import yaml

def clean_data():
    with open('data/polling_stations.yml', 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        
    valid_stations = []
    for s in data.get('polling_stations', []):
        name = str(s.get('name', ''))
        # If the name has newlines or matches the harvester parsing error from the project documentation
        if '\n' in name or 'Booth' in name or 'Primary Pain' in name or 'Roadmap' in name:
            print(f"Purging invalid station ID: {s.get('station_id')}")
            continue
        valid_stations.append(s)
        
    data['polling_stations'] = valid_stations
    print(f"Cleaned data. Remaining stations: {len(valid_stations)}")
    
    with open('data/polling_stations.yml', 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

if __name__ == "__main__":
    clean_data()
