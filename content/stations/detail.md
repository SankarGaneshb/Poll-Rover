---
title: Polling Station Details
template: station.html
---

<div id="station-detail-root">
    <div class="loading-state" style="text-align: center; padding: 3rem;">
        <p>Fetching polling station data...</p>
        <div class="spinner"></div>
    </div>
</div>

<script>
  // Inject base URL so the JS can construct correct data paths for GitHub Pages
  window.POLL_ROVER_BASE = "https://sankarganeshb.github.io/Poll-Rover";
</script>
<script src="{{ config.base_url | safe }}/js/station-detail.js"></script>
