"""Verification script: runs Quality, SRE, and Site Generator."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("STAGE 1: Data Quality Agent")
print("=" * 60)
from agents.quality.quality_agent import DataQualityAgent
quality = DataQualityAgent()
qr = quality.run(fix_issues=True)
print(f"  Audited: {qr['stations_audited']}")
print(f"  Passed:  {qr['passed']}")
print(f"  Warnings: {qr['warnings']}")
print(f"  Errors:  {qr['errors']}")

print()
print("=" * 60)
print("STAGE 2: SRE Ops Agent")
print("=" * 60)
from agents.sre_ops.sre_agent import SREOpsAgent
sre = SREOpsAgent()
sr = sre.run()
print(f"  Status: {sr['overall_status']}")
print(f"  Incidents: {len(sr.get('incidents', []))}")
print(f"  Remediations: {len(sr.get('remediations', []))}")
for check in sr.get("checks_run", []):
    print(f"    {check['name']}: {check['status']}")

print()
print("=" * 60)
print("STAGE 3: Site Generator")
print("=" * 60)
from scripts.generate_site import generate_site
gr = generate_site("data/polling_stations.yml", "content/stations")
print(f"  Pages generated: {gr['generated']}")

print()
print("=" * 60)
print("STAGE 4: Orchestrator Status")
print("=" * 60)
from agents.orchestrator.orchestrator import AgentOrchestrator
orch = AgentOrchestrator()
status = orch.status()
print(f"  Version:  {status['version']}")
print(f"  Stations: {status['stations_loaded']}")
print(f"  Pilots:   {', '.join(status['pilot_states'])}")
for agent, enabled in status['agents'].items():
    print(f"    {agent}: {'enabled' if enabled else 'disabled'}")

print()
print("ALL VERIFICATION COMPLETE")
