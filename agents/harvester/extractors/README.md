# Harvester Extractors

This directory contains specialized extraction logic for different Indian states/sources.

### Extractor Registry
- `tn_election_pdf.py`: PDF parser for Tamil Nadu electoral rolls.
- `kl_ceo_scraper.py`: Web scraper for Kerala CEO station data.
- `generic_pdf_llm.py`: (Planned) Fallback LLM logic for unstructured PDFs.

### Extractor Interface
Each extractor should return a list of dictionaries with the following structure:
```python
{
    "station_id": str,
    "name": str,
    "address": str,
    "state": str,
    "district": str,
    "latitude": float,
    "longitude": float,
    "metadata": {
        "data_source": str,
        "provenance": str
    }
}
```
The Harvester Agent will handle normalization and geocoding if coordinates are missing.
