"""
Poll-Rover Site Generator (Dynamic Data Edition)
Generates Zola content and partitioned JSON data for polling stations.
Reduces file count from 70,000+ to under 1,000.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml


def generate_site(states_dir: str, content_dir: str, dry_run: bool = False) -> dict:
    """Generate Zola content and JSON data for polling stations."""
    print(f"Loading data from states directory: {states_dir}...")
    stations = []
    
    states_path = Path(states_dir)
    # Recursively find all YAML files in data/states/
    for state_file in states_path.rglob("*.yml"):
        print(f"   Reading {state_file.relative_to(states_path)}...")
        with open(state_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            stations.extend(data.get("polling_stations", []))
    content_path = Path(content_dir)
    data_dir = Path("static/data/stations")

    if not dry_run:
        content_path.mkdir(parents=True, exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)

    report = {"stations": len(stations), "json_files": 0}

    # 1. Generate JSON Chunks (Partitioned by State and District)
    if not dry_run:
        _generate_json_chunks(stations, data_dir)
        
        # 2. Generate a single dynamic detail page shell
        _generate_detail_shell(content_path)

    # 3. Generate Optimized Discovery and Search Index
    if not dry_run:
        _generate_index_page(stations, content_path)
        _generate_discovery_data(stations, Path("static/data"))
        _generate_search_index(stations, Path("static/data"))

    print(f"\n{'=' * 50}")
    print(f"Successfully processed {len(stations)} stations.")
    print(f"Data stored in partitioned JSON files inside static/data/stations/")
    print(f"Total files reduced by ~99%.")
    return report


def _generate_json_chunks(stations: list, data_dir: Path) -> None:
    """Group stations by state and district, and save as JSON files."""
    grouped = {}
    for s in stations:
        # Standardize state and district keys for filenames
        state = s.get("state", "Unknown").strip().lower().replace(" ", "_").replace(".", "")
        district = s.get("district", "Unknown").strip().lower().replace(" ", "_").replace(".", "")
        
        if state not in grouped:
            grouped[state] = {}
        if district not in grouped[state]:
            grouped[state][district] = []
            
        grouped[state][district].append(s)

    count = 0
    for state, districts in grouped.items():
        state_path = data_dir / state
        state_path.mkdir(parents=True, exist_ok=True)
        
        for district, district_stations in districts.items():
            file_path = state_path / f"{district}.json"
            # Optimization: Use compact separators to save bandwidth
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(district_stations, f, ensure_ascii=False, separators=(',', ':'))
            print(f"   [JSON] {state}/{district}.json ({len(district_stations)} stations)")
            count += 1
    print(f"Generated {count} partitioned JSON files.")


def _generate_detail_shell(content_path: Path) -> None:
    """Create the dynamic detail page shell."""
    content = """---
title: Polling Station Details
template: station.html
---

<div id="station-detail-root">
    <div class="loading-state" style="text-align: center; padding: 3rem;">
        <p>Fetching polling station data...</p>
        <div class="spinner"></div>
    </div>
</div>

<script src="/js/station-detail.js"></script>
"""
    # Ensure the detail page is in the root of the stations category
    with open(content_path / "detail.md", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"   [MD]   Created dynamic shell: {content_path / 'detail.md'}")


def _generate_discovery_data(stations: list, data_dir: Path) -> None:
    """Generate a lightweight discovery JSON (State and District centroids)."""
    summary = {"states": {}}
    
    for s in stations:
        state = s.get("state", "Unknown")
        state_key = state.strip().lower().replace(" ", "_").replace(".", "")
        district = s.get("district", "Unknown")
        dist_key = district.strip().lower().replace(" ", "_").replace(".", "")
        lat = s.get("latitude")
        lng = s.get("longitude")
        
        if not lat or not lng: continue
        
        if state_key not in summary["states"]:
            summary["states"][state_key] = {"name": state, "districts": {}, "count": 0}
            
        st = summary["states"][state_key]
        st["count"] += 1
        
        if dist_key not in st["districts"]:
            st["districts"][dist_key] = {"name": district, "count": 0, "lat_sum": 0, "lng_sum": 0}
            
        d = st["districts"][dist_key]
        d["count"] += 1
        d["lat_sum"] += float(lat)
        d["lng_sum"] += float(lng)

    # Finalize centroids
    for state in summary["states"].values():
        for dist in state["districts"].values():
            dist["lat"] = round(dist["lat_sum"] / dist["count"], 4)
            dist["lng"] = round(dist["lng_sum"] / dist["count"], 4)
            del dist["lat_sum"]
            del dist["lng_sum"]

    output_path = data_dir / "summary.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, separators=(',', ':'))
    print(f"   [JSON] Created discovery summary: {output_path}")


def _generate_search_index(stations: list, data_dir: Path) -> None:
    """Generate a lightweight index for global search."""
    # Structure: [[id, name, state_key, dist_key], ...]
    index = []
    for s in stations:
        state_key = s.get("state", "Unknown").strip().lower().replace(" ", "_").replace(".", "")
        dist_key = s.get("district", "Unknown").strip().lower().replace(" ", "_").replace(".", "")
        index.append([
            s["station_id"],
            s["name"],
            state_key,
            dist_key
        ])
        
    output_path = data_dir / "search_index.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(index, f, separators=(',', ':'))
    print(f"   [JSON] Created search index: {output_path} ({len(index)} entries)")


def _generate_index_page(stations: list, content_path: Path) -> None:
    """Generate the station listing index page with dynamic links."""
    frontmatter = {
        "title": "All Polling Stations",
        "template": "list.html",
        "sort_by": "title",
    }

    body = f"# All Polling Stations\n\nTotal: {len(stations)} stations discovered.\n"

    # Group by state
    by_state = {}
    for s in stations:
        state = s.get("state", "Unknown")
        by_state.setdefault(state, []).append(s)

    for state, state_stations in sorted(by_state.items()):
        body += f"\n## {state} ({len(state_stations)} stations)\n\n"
        # Since we can't list 70k links easily, we'll provide a few samples and a search link
        # In a real app, this would be a filtered directory.
        sample_size = min(len(state_stations), 10)
        body += f"*Displaying {sample_size} sample stations. Use the map or search to find others.*\n\n"
        
        for s in state_stations[:sample_size]:
            # Link format: /stations/detail/?id=STATION_ID&loc=state/district
            state_key = s.get('state','').strip().lower().replace(' ', '_').replace('.', '')
            dist_key = s.get('district','').strip().lower().replace(' ', '_').replace('.', '')
            station_id = s['station_id']
            body += f"- [{s['name']}](/stations/detail/?id={station_id}&loc={state_key}/{dist_key})\n"

    frontmatter_yaml = yaml.dump(frontmatter, default_flow_style=False)
    index_content = f"---\n{frontmatter_yaml}---\n\n{body}"

    with open(content_path / "_index.md", "w", encoding="utf-8") as f:
        f.write(index_content)
    print(f"   [MD]   Generated index: {content_path / '_index.md'}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    generate_site(
        states_dir="data/states",
        content_dir="content/stations",
        dry_run=dry_run,
    )
