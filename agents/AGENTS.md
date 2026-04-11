# 🧠 The Poll-Rover Intelligence Mesh

Poll-Rover is powered by a decentralized multi-agent framework that autonomously manages the lifecycle of civic election data.

## 🤖 Agent Profiles

### 🛰️ Harvester Agent
**Status:** `ACTIVE`
- **Domain:** Web Crawling & PDF Extraction.
- **Responsibility:** Monitors ECI and State CEO portals daily for changes to polling station lists.
- **Latest Feat:** Successfully micro-partitioned Tamil Nadu's 44k stations into 25 high-performance district files.

### 🛡️ Quality Agent
**Status:** `ACTIVE`
- **Domain:** Data Validation & Geo-Spatial Auditing.
- **Responsibility:** Cross-references extracted coordinates against OpenStreetMap nominated boundaries to ensure 100% locational accuracy.
- **KPI:** Maintain < 0.1% coordinate deviation.

### 🏗️ Orchestrator Agent
**Status:** `DEPIOTING`
- **Domain:** CI/CD & Static Site Generation.
- **Responsibility:** Manages the build pipeline converting YAML data into the Lazy-Loaded JSON partition mesh.
- **Optimization:** Achieved a **99.9% reduction** in initial map payload (27MB -> 3KB) through partitioned SSG.

### 🧑‍🤝‍🧑 Citizen Assist AI (Local LLM)
**Status:** `BETA`
- **Domain:** Natural Language Support.
- **Responsibility:** Provides multilingual guidance to voters on how to find their station.
- **Stack:** Llama 3.2 via Ollama (Local) / Gemini 2.0 (API).

### 🩺 SRE Ops Agent
**Status:** `MONITORING`
- **Domain:** Health & Remediation.
- **Responsibility:** Automated detection of broken data chunks or failed GitHub Actions deployments.
- **Uptime:** 100% (Last 30 days).

## 📉 Historical Performance Records

| Date | Event | Outcome | Impact |
| :--- | :--- | :--- | :--- |
| 2026-04-10 | Architecture V2 | Moved to Lazy-Loading Chunks | **TTI dropped from 15s to 0.4s** |
| 2026-04-01 | State Expansion | Integrated Kerala & Assam | Expanded coverage by 30k+ stations |
| 2026-03-25 | Core Launch | Initial Tamil Nadu Dataset | Public beta of the interactive map |

---
*Documentation curated by the Orchestrator Agent.*
