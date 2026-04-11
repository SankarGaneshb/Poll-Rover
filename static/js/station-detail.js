/**
 * Poll-Rover Station Detail Loader
 * Works with the actual ECI minimal data schema.
 */

(function () {
    const BASE = 'https://sankarganeshb.github.io/Poll-Rover';

    const params = new URLSearchParams(window.location.search);
    const stationId = params.get('id');
    const locationKey = params.get('loc'); // e.g., "tamil_nadu/ariyalur"

    function renderError(msg) {
        const root = document.getElementById('station-detail-root');
        if (!root) return;
        root.innerHTML = `
            <div style="text-align:center; padding:4rem; color:var(--text-primary)">
                <div style="font-size:3rem">⚠️</div>
                <h2>Station Details Unavailable</h2>
                <p style="color:var(--text-muted); margin:1rem 0">${msg}</p>
                <a href="${BASE}/stations/" style="color:var(--accent); font-weight:700">← Back to Directory</a>
            </div>`;
    }

    function renderStation(s, locKey) {
        const root = document.getElementById('station-detail-root');
        if (!root) return;

        // Parse address from name — the name field contains the full address in ECI format
        const nameParts = s.name.split(' - ');
        const displayName = nameParts[0]?.trim() || s.name;
        const addressPart = nameParts[1]?.trim() || '';

        const mapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${s.latitude},${s.longitude}`;
        const coordsLabel = (s.latitude && s.longitude && s.latitude !== 13.0)
            ? `${s.latitude.toFixed(4)}, ${s.longitude.toFixed(4)}`
            : 'Coordinates not available';

        document.title = `${displayName} | Poll-Rover`;

        root.innerHTML = `
            <style>
                .detail-card { max-width: 860px; margin: 0 auto; }
                .detail-hero {
                    background: var(--bg-glass);
                    border: 1px solid var(--border);
                    border-top: 4px solid var(--accent);
                    border-radius: var(--radius-lg);
                    padding: 2rem;
                    margin-bottom: 2rem;
                }
                .detail-hero h1 { font-size: 1.5rem; margin: 0.5rem 0; line-height: 1.4; }
                .detail-hero .badge-row { display: flex; gap: 0.8rem; flex-wrap: wrap; margin-bottom: 1rem; }
                .badge { padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.8rem; font-weight: 700; }
                .badge-state { background: var(--accent-glow); color: var(--accent); }
                .badge-district { background: rgba(255,255,255,0.05); color: var(--text-muted); border: 1px solid var(--border); }
                .detail-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; }
                .info-card {
                    background: var(--bg-glass);
                    border: 1px solid var(--border);
                    border-radius: var(--radius-md);
                    padding: 1.5rem;
                }
                .info-card h2 { font-size: 1rem; margin: 0 0 1rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
                .info-row { display: flex; justify-content: space-between; padding: 0.6rem 0; border-bottom: 1px solid var(--border); font-size: 0.9rem; }
                .info-row:last-child { border-bottom: none; }
                .info-label { color: var(--text-muted); }
                .info-value { color: var(--text-primary); font-weight: 600; text-align: right; max-width: 60%; }
                .action-btn {
                    display: inline-flex; align-items: center; gap: 0.6rem;
                    padding: 1rem 2rem; border-radius: var(--radius-md);
                    background: var(--accent); color: #fff; font-weight: 700;
                    text-decoration: none; font-size: 1rem; margin-top: 1rem;
                    border: none; cursor: pointer; transition: opacity 0.2s;
                }
                .action-btn:hover { opacity: 0.85; }
                .back-link { color: var(--accent); text-decoration: none; font-weight: 600; display: inline-block; margin-bottom: 1.5rem; }
            </style>
            <div class="detail-card">
                <a href="${BASE}/stations/" class="back-link">← Back to Directory</a>
                <div class="detail-hero">
                    <div class="badge-row">
                        <span class="badge badge-state">${s.state}</span>
                        <span class="badge badge-district">${s.district}</span>
                        <span class="badge badge-district">${s.assembly_constituency}</span>
                    </div>
                    <h1>${displayName}</h1>
                    ${addressPart ? `<p style="color:var(--text-muted); margin:0.5rem 0">📍 ${addressPart}</p>` : ''}
                    <p style="font-size:0.85rem; color:var(--text-muted); margin:0.3rem 0">Station ID: ${s.station_id}</p>
                    <a href="${mapsUrl}" target="_blank" class="action-btn">🚀 Get Directions</a>
                </div>

                <div class="detail-grid">
                    <div class="info-card">
                        <h2>Electoral Information</h2>
                        <div class="info-row"><span class="info-label">State</span><span class="info-value">${s.state}</span></div>
                        <div class="info-row"><span class="info-label">District</span><span class="info-value">${s.district}</span></div>
                        <div class="info-row"><span class="info-label">Assembly Constituency</span><span class="info-value">${s.assembly_constituency || 'N/A'}</span></div>
                        <div class="info-row"><span class="info-label">State Code</span><span class="info-value">${s.state_code || 'N/A'}</span></div>
                        <div class="info-row"><span class="info-label">AC Number</span><span class="info-value">${s.metadata?.ac_number || 'N/A'}</span></div>
                    </div>
                    <div class="info-card">
                        <h2>Location & Navigation</h2>
                        <div class="info-row"><span class="info-label">Coordinates</span><span class="info-value">${coordsLabel}</span></div>
                        <div class="info-row"><span class="info-label">Data Source</span><span class="info-value">${s.metadata?.data_source || 'ECI Official'}</span></div>
                        <div class="info-row"><span class="info-label">Voting Date</span><span class="info-value">April-May 2026</span></div>
                        <div class="info-row"><span class="info-label">Voting Hours</span><span class="info-value">07:00 AM – 06:00 PM</span></div>
                    </div>
                </div>
            </div>`;
    }

    async function load() {
        if (!stationId) { renderError('No station ID in URL.'); return; }
        if (!locationKey) { renderError('Station location missing from URL.'); return; }

        try {
            const url = `${BASE}/data/stations/${locationKey}.json`;
            const resp = await fetch(url);
            if (!resp.ok) throw new Error(`HTTP ${resp.status} for ${url}`);
            const stations = await resp.json();
            const station = stations.find(s => s.station_id === stationId);
            if (!station) { renderError(`Station ${stationId} not found in ${locationKey}.`); return; }
            renderStation(station, locationKey);
        } catch (err) {
            console.error('Detail load failed:', err);
            renderError(`Failed to load: ${err.message}`);
        }
    }

    // Run immediately if DOM is ready, else wait
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', load);
    } else {
        load();
    }
})();
