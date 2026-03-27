"""
Poll-Rover Schema Validation Script
Validates all entries in polling_stations.yml against the Pydantic schema.

Usage: python scripts/validate_schema.py [data/polling_stations.yml]
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from pydantic import ValidationError
from data.models.polling_station import PollingStation


def validate(yaml_path: str) -> bool:
    """Validate all polling station entries in a YAML file.

    Returns True if all entries pass validation.
    """
    path = Path(yaml_path)
    if not path.exists():
        print(f"❌ File not found: {yaml_path}")
        return False

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    stations = data.get("polling_stations", [])
    if not stations:
        print("⚠️  No stations found in file.")
        return True

    print(f"Validating {len(stations)} stations from {yaml_path}...\n")

    passed = 0
    failed = 0

    for i, entry in enumerate(stations):
        station_id = entry.get("station_id", f"entry_{i}")
        try:
            station = PollingStation.from_yaml_dict(entry)
            print(f"  ✅ {station_id}: {station.name}")
            passed += 1
        except ValidationError as e:
            print(f"  ❌ {station_id}: {e.error_count()} validation errors")
            for error in e.errors():
                field = " → ".join(str(x) for x in error["loc"])
                print(f"     • {field}: {error['msg']}")
            failed += 1

    print(f"\n{'━' * 50}")
    print(f"Results: {passed} passed, {failed} failed ({len(stations)} total)")

    if failed == 0:
        print("✅ All stations valid!")
    else:
        print(f"❌ {failed} stations have validation errors.")

    return failed == 0


if __name__ == "__main__":
    yaml_file = sys.argv[1] if len(sys.argv) > 1 else "data/polling_stations.yml"
    success = validate(yaml_file)
    sys.exit(0 if success else 1)
