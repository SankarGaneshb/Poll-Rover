# Poll-Rover: Manual Data Ingestion Guide

Because automated web-scraping of Indian government websites is fragile due to frequent layout changes and CAPTCHAs, Poll-Rover relies on a **Human-in-the-Loop** approach for downloading the initial raw data. 

This guide provides step-by-step instructions on how to manually acquire the official Electoral Roll PDFs for our three pilot states: **Tamil Nadu**, **Kerala**, and **Puducherry**. Once downloaded, dropping these PDFs into the `data/source_pdfs/` directory will trigger the Harvester Agent to process them.

---

## 🇮🇳 Tamil Nadu (TN)
**Target Directory:** `data/source_pdfs/TN/`

1. **Navigate to the CEO Portal:** Go to the official [Elections TN Portal](https://elections.tn.gov.in/).
2. **Locate Electoral Rolls:** Click on **"Electoral Rolls"** or "Final Publication of Electoral Roll" on the homepage.
3. **Select Region:** 
   * Choose your **District** (e.g., *Chennai*).
   * Choose the **Assembly Constituency (AC)** you want to map.
4. **Bypass Security:** Enter the required CAPTCHA displayed on the screen.
5. **Download:** You will see a list of Polling Stations. Click **"Download"** or "Print" for the entire AC Roll or specific booths.
6. **Save File:** Save the file as `[district_name]_roll.pdf` (e.g., `chennai_roll.pdf`) and move it into the TN source directory.

---

## 🌴 Kerala (KL)
**Target Directory:** `data/source_pdfs/KL/`

1. **Navigate to the CEO Portal:** Go to the official [CEO Kerala Portal](http://www.ceo.kerala.gov.in/).
2. **Locate Electoral Rolls:** Find the section titled **"Electoral Rolls"** (usually under "Voter Services").
3. **Select Region:**
   * Select the **District** (e.g., *Thiruvananthapuram*).
   * Select the **Legislative Assembly Constituency (LAC)**.
4. **Bypass Security:** Complete the image CAPTCHA verification to proceed.
5. **Download:** The site will present the PDF links for the selected LAC. Download the English version if available (for easier extraction).
6. **Save File:** Save the file as `[district_name]_roll.pdf` (e.g., `trivandrum_roll.pdf`) and move it into the KL source directory.

---

## 🏖️ Puducherry (PY)
**Target Directory:** `data/source_pdfs/PY/`

1. **Navigate to the CEO Portal:** Go to the official [CEO Puducherry Portal](https://ceopuducherry.py.gov.in/).
2. **Locate Electoral Rolls:** Click on **"Electoral Rolls"** in the main navigation menu.
3. **Select Region:**
   * Select the **Region** (Puducherry, Karaikal, Mahe, or Yanam).
   * Select the **Assembly Constituency**.
4. **Bypass Security:** Enter the verification code (CAPTCHA).
5. **Download:** Click to view the Draft or Final Electoral Roll. This will open the PDF in your browser. Download it.
6. **Save File:** Save the file as `[region_name]_roll.pdf` (e.g., `puducherry_roll.pdf`) and move it into the PY source directory.

---

> [!IMPORTANT]
> **What to do after downloading?**
> Once the PDFs are placed in their respective `data/source_pdfs/` folders, you simply need to commit and push the changes to your `main` branch. GitHub Actions will automatically wake up the **Harvester Agent** at midnight (or immediately if triggered repeatedly), parse the PDFs, update the DB, and redeploy the dashboard without any further action!
