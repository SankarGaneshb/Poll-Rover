import fitz
import re

def check_acs(pdf_path):
    doc = fitz.open(pdf_path)
    acs = set()
    for i, page in enumerate(doc):
        text = page.get_text()
        # Look for the AC header pattern: "170 THIRUVIDAIMARUDUR (SC)"
        # Some are just digits, some have (SC) or (ST)
        match = re.search(r'(\d{3}\s+[A-Z\s]+(?:\(SC\)|\(ST\))?)', text)
        if match:
            acs.add(match.group(1).strip())
    
    print(f"Total Pages: {len(doc)}")
    print(f"Assembly Constituencies Found: {sorted(list(acs))}")

if __name__ == "__main__":
    check_acs("data/source_pdfs/TN/Thanjavur_dt.pdf")
