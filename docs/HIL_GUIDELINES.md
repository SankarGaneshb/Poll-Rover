# 🤝 Human-In-The-Loop (HIL) Operational Guidelines

To maintain the scale and speed of Poll-Rover while ensuring 100% data trust, we use a hybrid **HIL (Human-In-The-Loop)** model. This document outlines the protocols for the human operator to provide timely feedback and approvals.

## 📅 Training & User Testing Window (Current)
Poll-Rover is currently in development and user testing. The approval windows are relaxed to ensure we have time for high-quality manual checks:
- **Phase 1 (Next 7 Days)**: **1 Day** Approval Window.
- **Phase 2 (Post-Testing)**: **1 Hour** Approval Window.

## 🧭 Where to Find Incident & Approval Info
You can monitor and approve agent actions in three primary locations:

### 1. Real-time Console Logs
If you are running the orchestrator locally, look for the **⚠️ [HIL-REQUIRED]** flag in the terminal. It will appear after Stage 4 (SRE Health Checks) fails.
- **Key indicator**: `⚠️ [HIL-REQUIRED] Action needed for Incident [TYPE]`.

### 2. SRE Operations Reports (Deep Detail)
For every run, the SRE agent generates a YAML report with full context on what failed and how it plans to fix it.
- **Path**: `ops_logs/sre_report_YYYY-MM-DD.yml`
- **What to look for**: The `incidents` list and the `playbook` suggested for each.

### 3. Weekly Performance Dashboard
For a high-level view of how many approvals are pending or how the agents are behaving over time.
- **Path**: `reports/weekly_perf.md`

### 4. GitHub Actions (Production)
If the pipeline runs in the cloud, check the **GitHub Actions tab**.
- Locate the latest `Poll-Rover Scale & Deploy` run.
- Click on the `sre_ops` step and expand the logs to see the `WAITING_FOR_HUMAN` status.

## 🚦 HIL Modes & Triggers

| Mode | Trigger | Human Action Required |
| :--- | :--- | :--- |
| **`REQUIRED`** | **Critical Data Errors** | Review the proposal in `ops_logs/` and grant `APPROVE` or `REJECT`. |
| **`OPTIONAL`** | **Minor Anomalies** | No block. Agent remediates and logs for **retrospective review**. |
| **`HARVEST`** | **New State Onboarding** | Verify the first 100 coordinates for "hallucination" before full crawl. |

## 📝 Review Checklist for HIL
When the SRE agent flags an incident, follow these 3 steps:

1.  **Check Coordinates**: Does the station actually exist in the reported District? (Verify 2-3 samples on Google Maps).
2.  **Verify Schema**: Did the LLM extract the AC Name and Ward correctly from the source PDF?
3.  **Assess Risk**: If the agent proposes `pip install`, is the package trusted? If it proposes `delete_entry`, is it a true duplicate or a multi-booth station?

## 📬 Communication Protocol

- **Approval**: To approve an automated fix, simply reply in our chat with: `[SRE-APPROVE] IncidentID: XXX`.
- **Rejection**: To stop a fix, reply: `[SRE-REJECT] IncidentID: XXX` and provide the manual correction.
- **Immediate Pause**: If the pipeline is malfunctioning, use `[AGENT-STOP-ALL]`.

## 🛠️ Performance Records for HIL
The HIL’s efficiency is tracked as a KPI:
- **MTTA (Mean Time to Approval)**: Target < 15 minutes.
- **Accuracy Rate**: Consistency between AI proposal and Human correction.

---
*Democracy is powered by people—HIL ensures the AI stays grounded.* 🗳️✨
