from agents.harvester.extractors.tn_election_pdf import extract_from_tn_pdf
from agents.harvester.harvester_agent import DataHarvesterAgent
from concurrent.futures import ProcessPoolExecutor
import yaml
import glob
import os
import logging
import sys

# Configure logging to see progress
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("harvester")

def process_single_pdf(pdf_path):
    try:
        # We need to initialize the harvester agent logic slightly for this or call directly
        # But for mass harvest, direct extraction + manual normalization is better
        print(f"📄 Processing {os.path.basename(pdf_path)}...")
        raw = extract_from_tn_pdf(pdf_path)
        return raw
    except Exception as e:
        print(f"❌ Error in {pdf_path}: {e}")
        return []

def parallel_mass_harvest():
    pdf_dir = "data/source_pdfs/TN"
    pdf_files = sorted(glob.glob(os.path.join(pdf_dir, "AC*.pdf")))
    
    print(f"🚀 Found {len(pdf_files)} PDFs. Starting parallel harvest using multiple CPUs...")
    
    all_raw_entries = []
    # Use 4-8 workers depending on typical laptop cores
    with ProcessPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(process_single_pdf, pdf_files))
        for res in results:
            all_raw_entries.extend(res)
            
    print(f"✅ Extracted {len(all_raw_entries)} stations total.")
    
    # Normalize with agent
    agent = DataHarvesterAgent()
    # Keep the initial 11 + newly extracted
    existing = agent._load_existing_stations()[:11]
    
    print(f"🧬 Normalizing for TN...")
    normalized = agent._normalize_entries(all_raw_entries, "TN", existing)
    
    # Save to YAML
    all_stations = existing + normalized
    with open("data/polling_stations.yml", "w", encoding="utf-8") as f:
        yaml.dump({"polling_stations": all_stations}, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"🎉 SUCCESS! Database updated with {len(all_stations)} stations.")

if __name__ == "__main__":
    parallel_mass_harvest()
