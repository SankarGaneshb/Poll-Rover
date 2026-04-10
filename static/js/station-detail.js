/**
 * Poll-Rover Station Detail Loader
 * Dynamically fetches and renders polling station data from partitioned JSON chunks.
 */

document.addEventListener('DOMContentLoaded', async () => {
    const root = document.getElementById('station-detail-root');
    const params = new URLSearchParams(window.location.search);
    const stationId = params.get('id');
    const locationKey = params.get('loc'); // e.g., "tamil_nadu/chennai"

    if (!stationId) {
        renderError('No station ID provided.');
        return;
    }

    try {
        // 1. Determine which chunk to fetch
        // If loc is missing, we might try to guess it from the ID prefix if we have a mapping
        // but for now, we expect 'loc' to be provided by the list/index page.
        if (!locationKey) {
            // Fallback: try to find it in the global stations.geojson if loaded, 
            // or show a find-me message.
            renderError('Station location not specified in URL.');
            return;
        }

        // 2. Fetch the JSON chunk
        const response = await fetch(`../../data/stations/${locationKey}.json`);
        if (!response.ok) throw new Error(`Could not load data for ${locationKey}`);
        
        const stations = await response.json();
        
        // 3. Find the specific station
        const station = stations.find(s => s.station_id === stationId);
        
        if (!station) {
            renderError(`Station ${stationId} not found in ${locationKey}.`);
            return;
        }

        // 4. Render the data
        renderStation(station);

    } catch (error) {
        console.error('Error fetching station details:', error);
        renderError(`Failed to load station details: ${error.message}`);
    }
});

function renderStation(station) {
    const root = document.getElementById('station-detail-root');
    const acc = station.accessibility || {};
    const election = station.election_details || {};
    const contact = station.contact || {};
    
    // Accessibility Stars/Icons
    const rating = parseInt(acc.accessibility_rating || 0);
    const stars = '⭐'.repeat(rating);
    
    const html = `
        <div class="station-detail-card">
            <header class="detail-header">
                <a href="../" class="back-link">← Back to List</a>
                <h1>${station.name}</h1>
                <p class="address">📍 ${station.address}</p>
                ${station.landmark ? `<p class="landmark">🏛️ Landmark: ${station.landmark}</p>` : ''}
            </header>

            <div class="detail-grid">
                <section class="info-section">
                    <h2>Electoral Information</h2>
                    <table class="detail-table">
                        <tr><th>State</th><td>${station.state}</td></tr>
                        <tr><th>District</th><td>${station.district || 'Unknown'}</td></tr>
                        <tr><th>Assembly Constituency</th><td>${station.assembly_constituency || 'Unknown'}</td></tr>
                        <tr><th>Parliamentary</th><td>${station.parliamentary_constituency || 'N/A'}</td></tr>
                        <tr><th>Ward</th><td>${station.ward || 'N/A'}</td></tr>
                    </table>
                </section>

                <section class="info-section">
                    <h2>Accessibility Features</h2>
                    <table class="detail-table">
                        <tr><th>Wheelchair Ramp</th><td>${getStatusBadge(acc.wheelchair_ramp)}</td></tr>
                        <tr><th>Parking</th><td>${getStatusBadge(acc.accessible_parking)}</td></tr>
                        <tr><th>Audio Booth</th><td>${acc.audio_booth ? '✅ Available' : '❌ Not Available'}</td></tr>
                        <tr><th>Braille Materials</th><td>${acc.braille_materials ? '✅ Available' : '❌ Not Available'}</td></tr>
                        <tr><th>Rating</th><td>${stars} (${rating}/5)</td></tr>
                    </table>
                </section>

                <section class="info-section">
                    <h2>Voting Details</h2>
                    <table class="detail-table">
                        <tr><th>Date</th><td>${election.voting_date || 'To be announced'}</td></tr>
                        <tr><th>Timing</th><td>${election.start_time || '07:00'} - ${election.end_time || '18:00'}</td></tr>
                        <tr><th>Booths</th><td>${election.number_of_booths || 'N/A'}</td></tr>
                        <tr><th>Estimated Voters</th><td>${election.estimated_voters || 'N/A'}</td></tr>
                    </table>
                </section>

                <section class="info-section">
                    <h2>Contact & Assistance</h2>
                    <table class="detail-table">
                        <tr><th>Officer</th><td>${contact.election_officer || 'N/A'}</td></tr>
                        <tr><th>Phone</th><td>${contact.phone || 'N/A'}</td></tr>
                        <tr><th>Services</th><td>${(acc.assistance_services || ['None']).join(', ')}</td></tr>
                    </table>
                </section>
            </div>

            <footer class="detail-footer">
                <p>Data Source: ${station.metadata?.data_source || 'ECI Official'}</p>
                <p class="timestamp">Last Updated: ${new Date().toLocaleDateString()}</p>
            </footer>
        </div>
    `;
    
    root.innerHTML = html;
    
    // Update Page Title
    document.title = `${station.name} | Poll-Rover`;
}

function getStatusBadge(status) {
    if (status === 'yes') return '<span class="badge available">✅ Available</span>';
    if (status === 'partial') return '<span class="badge partial">⚠️ Partial</span>';
    return '<span class="badge unavailable">❌ Not Available</span>';
}

function renderError(message) {
    const root = document.getElementById('station-detail-root');
    root.innerHTML = `
        <div class="error-container" style="text-align: center; padding: 4rem;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">⚠️</div>
            <h2>Station Details Unavailable</h2>
            <p>${message}</p>
            <br>
            <a href="/" class="btn-primary">Return to Homepage</a>
        </div>
    `;
}
