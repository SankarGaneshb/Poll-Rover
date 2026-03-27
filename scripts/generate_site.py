"""
Poll-Rover Site Generator
Generates Zola-compatible markdown pages from polling station YAML data.
Follows the ooru.space pattern: data/entries.yml → content/spaces/

Usage: python scripts/generate_site.py [--dry-run]
"""

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml


def generate_site(yaml_path: str, output_dir: str, dry_run: bool = False) -> dict:
    """Generate Zola markdown pages for each polling station.

    Args:
        yaml_path: Path to polling_stations.yml
        output_dir: Directory for generated Zola content
        dry_run: If True, only preview what would be generated.

    Returns:
        Generation report.
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    stations = data.get("polling_stations", [])
    output = Path(output_dir)

    if not dry_run:
        output.mkdir(parents=True, exist_ok=True)

    report = {"generated": 0, "skipped": 0, "errors": 0}

    # Generate individual station pages
    for station in stations:
        try:
            md_content = _station_to_markdown(station)
            station_id = station["station_id"]
            file_path = output / f"{station_id.lower()}.md"

            if dry_run:
                print(f"  Would create: {file_path}")
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(md_content)

            report["generated"] += 1
        except Exception as e:
            print(f"  Error generating {station.get('station_id', '?')}: {e}")
            report["errors"] += 1

    # Generate index page with all stations as JSON (for Leaflet map)
    if not dry_run:
        # Generate GeoJSON for Zola's static directory
        # This will be served at /data/stations.geojson in the final build
        _generate_map_data(stations, Path("static/data"))
        
        _generate_index_page(stations, output)

    print(f"\n{'=' * 50}")
    print(f"Generated: {report['generated']} pages, {report['errors']} errors")
    return report


def _station_to_markdown(station: dict) -> str:
    """Convert a station dict to Zola-compatible markdown with frontmatter."""
    acc = station.get("accessibility", {})
    election = station.get("election_details", {})
    contact = station.get("contact", {})

    # Accessibility icons
    icons = []
    if acc.get("wheelchair_ramp") in ("yes", "partial"):
        icons.append("♿ Wheelchair")
    if acc.get("audio_booth"):
        icons.append("🔊 Audio")
    if acc.get("braille_materials"):
        icons.append("⠿ Braille")

    # Zola frontmatter
    frontmatter = {
        "title": station["name"],
        "description": f"Polling station at {station['address']}",
        "date": date.today().isoformat(),
        "extra": {
            "station_id": station["station_id"],
            "state": station["state"],
            "district": station.get("district", "Unknown"),
            "latitude": station.get("latitude", 0),
            "longitude": station.get("longitude", 0),
            "assembly_constituency": station.get("assembly_constituency", "Unknown"),
            "parliamentary_constituency": station.get("parliamentary_constituency", "N/A"),
            "accessibility_rating": acc.get("accessibility_rating", 0),
            "wheelchair_ramp": acc.get("wheelchair_ramp", "no"),
            "audio_booth": acc.get("audio_booth", False),
            "braille_materials": acc.get("braille_materials", False),
        },
        "template": "station.html",
        "taxonomies": {
            "states": [station["state"]],
            "districts": [station.get("district", "Unknown")],
            "constituencies": [station.get("assembly_constituency", "Unknown")],
        },
    }

    # Markdown body
    body = f"""# {station['name']}

📍 **{station['address']}**
{f"🏛️ Landmark: {station['landmark']}" if station.get('landmark') else ""}

## Electoral Information
| Field | Value |
|-------|-------|
| Assembly Constituency | {station.get('assembly_constituency', 'Unknown')} |
| Parliamentary Constituency | {station.get('parliamentary_constituency', 'N/A')} |
| Ward | {station.get('ward', 'N/A')} |
| State | {station['state']} |
| District | {station.get('district', 'Unknown')} |

## Accessibility Features {' '.join(icons)}

| Feature | Status |
|---------|--------|
| Wheelchair Ramp | {_status_badge(acc.get('wheelchair_ramp', 'no'))} |
| Accessible Parking | {_status_badge(acc.get('accessible_parking', 'no'))} |
| Audio Booth | {'✅' if acc.get('audio_booth') else '❌'} |
| Braille Materials | {'✅' if acc.get('braille_materials') else '❌'} |
| Assistance Services | {', '.join(acc.get('assistance_services', ['None'])) } |
| Accessibility Rating | {'⭐' * int(acc.get('accessibility_rating', 0))} ({acc.get('accessibility_rating', 'N/A')}/5) |
| Crowding Level | {acc.get('crowding_difficulty', 'N/A')} |

## Voting Details

| Field | Value |
|-------|-------|
| Voting Date | {election.get('voting_date', 'To be announced')} |
| Phase | {election.get('voting_phase', 'TBD')} |
| Timing | {election.get('start_time', '07:00')} - {election.get('end_time', '18:00')} |
| Number of Booths | {election.get('number_of_booths', 'N/A')} |
| Estimated Voters | {election.get('estimated_voters', 'N/A')} |

## Contact

| | |
|---|---|
| Election Officer | {contact.get('election_officer', 'N/A')} |
| Phone | {contact.get('phone', 'N/A')} |
| Email | {contact.get('email', 'N/A')} |

---
*Data confidence: {station.get('metadata', {}).get('confidence_score', 'N/A')} | Source: {station.get('metadata', {}).get('data_source', 'N/A')}*
"""

    # Combine frontmatter + body
    frontmatter_yaml = yaml.dump(
        frontmatter, default_flow_style=False, allow_unicode=True
    )
    return f"---\n{frontmatter_yaml}---\n\n{body}"


def _status_badge(status: str) -> str:
    """Convert status string to emoji badge."""
    if status == "yes":
        return "✅ Available"
    elif status == "partial":
        return "⚠️ Partial"
    return "❌ Not Available"


def _generate_map_data(stations: list, data_dir: Path) -> None:
    """Generate GeoJSON for the Leaflet.js map."""
    data_dir.mkdir(parents=True, exist_ok=True)

    features = []
    for s in stations:
        acc = s.get("accessibility", {})
        rating = acc.get("accessibility_rating", 0)

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [s.get("longitude", 0), s.get("latitude", 0)],
            },
            "properties": {
                "station_id": s["station_id"],
                "name": s["name"],
                "address": s["address"],
                "constituency": s.get("assembly_constituency", ""),
                "state": s["state"],
                "accessibility_rating": rating,
                "wheelchair_ramp": acc.get("wheelchair_ramp", "no"),
                "audio_booth": acc.get("audio_booth", False),
                "braille_materials": acc.get("braille_materials", False),
                "voting_date": str(s.get("election_details", {}).get("voting_date", "")),
            },
        }
        features.append(feature)

    geojson = {"type": "FeatureCollection", "features": features}

    with open(data_dir / "stations.geojson", "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    print(f"  Generated GeoJSON with {len(features)} stations")


def _generate_index_page(stations: list, output_dir: Path) -> None:
    """Generate the station listing index page."""
    frontmatter = {
        "title": "All Polling Stations",
        "template": "list.html",
        "sort_by": "title",
    }

    body = f"# All Polling Stations\n\nTotal: {len(stations)} stations\n"

    # Group by state
    by_state = {}
    for s in stations:
        state = s.get("state", "Unknown")
        by_state.setdefault(state, []).append(s)

    for state, state_stations in sorted(by_state.items()):
        body += f"\n## {state} ({len(state_stations)} stations)\n\n"
        for s in state_stations:
            body += f"- [{s['name']}](@/stations/{s['station_id'].lower()}.md) — {s['assembly_constituency']}\n"

    frontmatter_yaml = yaml.dump(frontmatter, default_flow_style=False)
    index_content = f"---\n{frontmatter_yaml}---\n\n{body}"

    with open(output_dir / "_index.md", "w", encoding="utf-8") as f:
        f.write(index_content)


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    generate_site(
        yaml_path="data/polling_stations.yml",
        output_dir="content/stations",
        dry_run=dry_run,
    )
