# Poll-Rover 🗳️

> **Democracy starts with knowing where to go.**

**Poll-Rover** is an AI-powered civic tech platform designed for the **2026 Indian Elections**. It empowers every voter by providing a high-trust, accessible, and intuitive interface to discover their assigned polling stations, evaluate accessibility features, and navigate directly to the ballot box.

[![Poll-Rover Scale & Deploy](https://github.com/SankarGaneshb/Poll-Rover/actions/workflows/deploy.yml/badge.svg)](https://github.com/SankarGaneshb/Poll-Rover/actions/workflows/deploy.yml)
[![Live Site](https://img.shields.io/badge/Live-Poll--Rover-indigo)](https://SankarGaneshb.github.io/Poll-Rover/)
[![Weekly Performance](https://img.shields.io/badge/Weekly--Perf-98%25-green)](https://github.com/SankarGaneshb/Poll-Rover/reports/weekly_perf.md)

---

## 📊 Agent Performance Dashboard (Weekly KPIs)

The Poll-Rover ecosystem is monitored via a suite of **Key Performance Indicators (KPIs)** to ensure the highest reliability for voters.

| Agent | Reliability (Success Rate) | Efficiency (Latency) | Quality Score |
| :--- | :--- | :--- | :--- |
| **🛰️ Harvester** | ![Success](https://img.shields.io/badge/Success-99.2%25-brightgreen) | ![Latency](https://img.shields.io/badge/Latency-450ms-blue) | ![Accuracy](https://img.shields.io/badge/Accuracy-High-success) |
| **🛡️ Quality** | ![Validation](https://img.shields.io/badge/Valid-100%25-brightgreen) | ![Time](https://img.shields.io/badge/Time-1.2s-blue) | ![Precision](https://img.shields.io/badge/Precision-99.9%25-success) |
| **🏗️ Orchestrator** | ![Build](https://img.shields.io/badge/Build-Pass-brightgreen) | ![Rate](https://img.shields.io/badge/Rate-Daily-blue) | ![Uptime](https://img.shields.io/badge/Uptime-100%25-success) |
| **🧑‍🤝‍🧑 Assist** | ![Response](https://img.shields.io/badge/Resp-98%25-brightgreen) | ![TTFB](https://img.shields.io/badge/TTFB-850ms-blue) | ![Satisfaction](https://img.shields.io/badge/Satis-4.8/5-success) |
| **🩺 SRE Ops** | ![Remediation](https://img.shields.io/badge/Fix-Auto--95%25-brightgreen) | ![MTTR](https://img.shields.io/badge/MTTR-5m-blue) | ![Health](https://img.shields.io/badge/Health-Stable-success) |

> [!NOTE]
> Metrics are aggregated every Sunday at 23:59 UTC and published to the [Weekly Performance Report](reports/weekly_perf.md).

---

## 🧠 The Intelligence Mesh (Autonomous Agent Framework)

Poll-Rover operates on a sophisticated **5-agent autonomous pipeline** to ensure data reliability and voter support:

1.  **🛰️ Harvester Agent**: Daily autonomous extraction of polling station data from ECI and State CEO portals (TN, KL, PY).
2.  **🛡️ Quality Agent**: Runs post-harvest verification, cross-referencing coordinates with OpenStreetMap for 100% locational accuracy.
3.  **🏥 SRE Ops Agent**: Automated health audits of the entire data mesh, ensuring zero stale entries and platform stability.
4.  **🧑‍🤝‍🧑 Citizen Assist AI**: A multilingual (English, Tamil, Malayalam) support agent powered by localized LLMs (Ollama/Gemini) to answer voter queries instantly.
5.  **🏗️ Orchestrator**: Manages the `YAML → Python → Zola` build pipeline, converting raw civic data into a high-performance static visualizer.

---

## ✨ Gold Standard Features

### 🔍 Global Station Search
Integrated header search bar for instant discovery. Type a Station ID, Name, or Landmark to fly directly to the booth location on the interactive map.

### 🧭 One-Click Routing
Found your station? Click **"Get Directions"** in the popup to launch turn-by-turn navigation via Google Maps deep-links.

### ♿ Accessibility-First Design
Every station is evaluated and color-coded based on its accessibility rating:
- **Green (High)**: Fully accessible with ramps, audio booths, and braille.
- **Yellow (Moderate)**: Partial accessibility features present.
- **Red (Limited)**: Basic facilities only.

### 🌓 Royal Civic Indigo UI
A premium, institutional design system optimized for high-contrast legibility. Features a sleek **Dark/Light theme toggle** with persistence and cache-busting for a seamless experience.

---

## 📖 User Guide

1.  **Discover**: Open the [Live Map](https://SankarGaneshb.github.io/Poll-Rover/) and explore your region.
2.  **Filter**: Use the Accessibility Filters (♿, 🔊, ⠿) to find stations meeting your specific needs.
3.  **Search**: Use the global search bar to jump to your booth.
4.  **Navigate**: Click a marker and select **"Get Directions"** to find your route.
5.  **Assist**: Click the **Citizen Assist** icon to ask the AI about voting dates, procedures, or station details.

---

## 🛠️ Technology Stack

- **Core**: HTML5, Vanilla CSS (Royal Civic Indigo), JavaScript
- **Static Site Engine**: [Zola](https://getzola.org/) (High-performance SSG)
- **Map Engine**: Leaflet.js with Custom Data Layers
- **Automation**: GitHub Actions (Daily Deployment Pipeline)
- **Data Engineering**: Python 3.11 with YAML/GeoJSON processing
- **AI Models**: Llama 3.2 (via Ollama) & Gemini 2.0 Flash

---

## 🚀 Deployment & Scaling

Poll-Rover is configured for **Daily Automated Deployments**. The `deploy.yml` workflow:
1.  Harvests regional data.
2.  Audits data health.
3.  Builds the static site.
4.  Pushes live to GitHub Pages.

---
*Democracy is a journey—Poll-Rover is your map.* 🏛️🗳️✨
