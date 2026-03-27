/**
 * Poll-Rover Map Engine
 * Leaflet.js interactive map with accessibility-colored markers,
 * filter layers, proximity search, and chat widget integration.
 */

// ===== STATION DATA (embedded from seed YAML) =====
let map;
let markers = [];
let STATIONS = []; // Now loaded dynamically
let tileLayer;
let currentTheme = localStorage.getItem('theme') || 'dark';

// Help Modal State
let currentHelpStep = 0;
const HELP_STEPS = [
  {
    icon: "🗺️",
    title: "Welcome to Poll Rover",
    text: "Your 'Gold Standard' guide to the 2026 Indian Elections. We help you find your polling station with institutional-grade accuracy."
  },
  {
    icon: "🔍",
    title: "Instant Discovery",
    text: "Use the new **Global Search** in the header or the **AI Chat** below to find your specific booth number or school in seconds."
  },
  {
    icon: "🧭",
    title: "Find Your Route",
    text: "Every station now has a **'Get Directions'** link. Tap it to open a precise route map from your current location directly to the ballot box."
  },
  {
    icon: "🦾",
    title: "Intelligence Mesh",
    text: "A mesh of **5 Autonomous Agents** (Harvester, SRE, Quality) works 24/7 to verify every single station coordinate and accessibility feature."
  },
  {
    icon: "♿",
    title: "Accessibility First",
    text: "Look for Green markers for 100% barrier-free stations. Use the filters to only see stations with Ramps, Braille, or Audio assistance."
  }
];

let activeFilters = {
  wheelchair: false,
  audio: false,
  braille: false,
  regions: []
};

// Apply theme on load
if (currentTheme === 'light') {
  document.documentElement.classList.add('light-theme');
}

function toggleTheme() {
  currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
  document.documentElement.classList.toggle('light-theme');
  localStorage.setItem('theme', currentTheme);
  
  // Swap map tiles if layer exists
  if (tileLayer) {
    const tileUrl = currentTheme === 'dark' 
      ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
      : 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';
    
    tileLayer.setUrl(tileUrl);
  }
}

async function initMap() {
  // Center on South India (covers TN, KL, PY)
  map = L.map('map', {
    center: [11.0, 79.5],
    zoom: 7,
    zoomControl: false, // Moved to bottomleft manually
    attributionControl: true
  });

  L.control.zoom({ position: 'bottomleft' }).addTo(map);

  // Theme-aware tile layer
  // DARK: Carto Midnight | LIGHT: Carto Voyager
  const tileUrl = currentTheme === 'dark' 
    ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
    : 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';

  tileLayer = L.tileLayer(tileUrl, {
    attribution: '© OpenStreetMap contributors © CARTO',
    maxZoom: 19
  }).addTo(map);

  // Apply trustworthy tone to tiles via CSS filters
  const container = map.getContainer();
  if (currentTheme === 'dark') {
    // Subtle indigo tint for better theme integration
    container.style.filter = 'saturate(0.7) brightness(0.9) hue-rotate(-15deg) contrast(1.1)';
  } else {
    container.style.filter = 'contrast(1.05) saturate(0.8) sepia(0.05)';
  }

  // Load dynamic data
  try {
    const response = await fetch('static/data/stations.geojson');
    const data = await response.json();
    
    // Map GeoJSON features back to our internal STATIONS structure
    STATIONS = (data.features || []).map(f => {
        const p = f.properties || {};
        const g = f.geometry || { coordinates: [0, 0] };
        return {
          station_id: p.station_id || "unknown",
          name: p.name || "Unknown Station",
          address: p.address || "No address provided",
          landmark: p.landmark || "N/A",
          ward: p.ward || "N/A",
          constituency: p.constituency || "Unknown",
          state: p.state || "Unknown",
          lat: g.coordinates[1],
          lng: g.coordinates[0],
          voting_date: p.voting_date || "Coming Soon",
          voting_time: "07:00 - 18:00",
          booths: p.booths || 0,
          estimated_voters: p.estimated_voters || 0,
          accessibility: {
              wheelchair_ramp: p.wheelchair_ramp || "no",
              rating: p.accessibility_rating || 0,
              audio_booth: p.audio_booth || false,
              braille_materials: p.braille_materials || false,
              accessible_parking: p.accessible_parking || "no",
              crowding: p.crowding || "low",
              notes: p.notes || ""
          },
          community: { wait_time: p.wait_time || "Unknown", crowd_rating: 0 },
          confidence: p.confidence || 0.5
        };
    });

    // Add all station markers
    STATIONS.forEach(station => addMarker(station));

    // Fit bounds to show all markers
    if (markers.length > 0) {
      const group = L.featureGroup(markers);
      map.fitBounds(group.getBounds().pad(0.15));
    }
  } catch (error) {
    console.error("Error loading station data:", error);
  }

  updateStats();
}

function addMarker(station) {
  const acc = station.accessibility;
  const rating = acc.rating;

  // Color class based on accessibility rating
  let colorClass = 'access-low';
  let markerColor = '#EF4444';
  if (rating >= 4.0) {
    colorClass = 'access-high';
    markerColor = '#10B981';
  } else if (rating >= 2.5) {
    colorClass = 'access-mid';
    markerColor = '#F59E0B';
  }

  // Custom icon - Designed as an "official civic badge"
  const icon = L.divIcon({
    className: '',
    html: `<div class="station-marker ${colorClass}" style="box-shadow: 0 0 15px ${markerColor}44; border: 2.5px solid white;">
             <span class="marker-inner">🗳️</span>
           </div>`,
    iconSize: [38, 38],
    iconAnchor: [19, 38],
    popupAnchor: [0, -38]
  });

  const marker = L.marker([station.lat, station.lng], { icon })
    .addTo(map)
    .bindPopup(buildPopupHTML(station), { maxWidth: 320, closeButton: true });

  marker._stationData = station;
  markers.push(marker);
}

function buildPopupHTML(s) {
  const acc = s.accessibility;
  const ratingPct = (acc.rating / 5) * 100;

  let ratingColor = '#EF4444';
  if (acc.rating >= 4) ratingColor = '#10B981';
  else if (acc.rating >= 2.5) ratingColor = '#F59E0B';

  const badges = [];
  if (acc.wheelchair_ramp === 'yes') badges.push('<span class="access-badge available">♿ Ramp</span>');
  else if (acc.wheelchair_ramp === 'partial') badges.push('<span class="access-badge partial">♿ Partial</span>');
  else badges.push('<span class="access-badge unavailable">♿ None</span>');

  if (acc.audio_booth) badges.push('<span class="access-badge available">🔊 Audio</span>');
  // Header Stats
  const statsHtml = `
    <div class="popup-stats">
      <div class="p-stat"><span>♿</span> ${s.accessibility.wheelchair_ramp === 'yes' ? 'Ramp Available' : 'No Ramp'}</div>
      <div class="p-stat"><span>🔊</span> ${s.accessibility.audio_booth ? 'Audio Booth' : 'Generic Booth'}</div>
      <div class="p-stat"><span>⠿</span> ${s.accessibility.braille_materials ? 'Braille Ready' : 'Standard Material'}</div>
    </div>
    <div class="popup-actions">
      <a href="https://www.google.com/maps/dir/?api=1&destination=${s.lat},${s.lng}" target="_blank" class="directions-btn">
        <span>🚗</span> GET DIRECTIONS
      </a>
    </div>
  `;
  
  return `
    <div class="station-popup">
      <div class="popup-header" style="border-left: 4px solid ${ratingColor}">
        <div class="name-row">
          <h3>${s.name}</h3>
          <span class="conf-badge" title="Data Confidence">${Math.round(s.confidence * 100)}% Trust</span>
        </div>
        <div class="constituency">${s.constituency} · Ward ${s.ward} · ${s.state}</div>
      </div>
      <div class="popup-body">
        <div class="popup-address">📍 ${s.address}<br>🏛️ ${s.landmark}</div>
        ${statsHtml}
        <div class="popup-footer">
          <span style="font-size:0.65rem; color:var(--text-muted)">📅 07 May 2026 · ${s.accessibility.crowding} crowd</span>
        </div>
      </div>
    </div>
  `;
}

// ===== FILTERS =====
function toggleFilter(type, value) {
  if (type === 'region') {
    const idx = activeFilters.regions.indexOf(value);
    if (idx > -1) activeFilters.regions.splice(idx, 1);
    else activeFilters.regions.push(value);
  } else {
    activeFilters[type] = !activeFilters[type];
  }
  applyFilters();
}

function applyFilters() {
  const isRegionFilterActive = activeFilters.regions.length > 0;

  markers.forEach(marker => {
    const s = marker._stationData;
    const acc = s.accessibility;

    let visible = true;

    // Region Filter (OR logic within regions)
    if (isRegionFilterActive && !activeFilters.regions.includes(s.state)) {
      visible = false;
    }

    // Accessibility Filter (AND logic)
    if (activeFilters.wheelchair && acc.wheelchair_ramp === 'no') visible = false;
    if (activeFilters.audio && !acc.audio_booth) visible = false;
    if (activeFilters.braille && !acc.braille_materials) visible = false;

    marker.setOpacity(visible ? 1 : 0.1);
    if (!visible) marker.closePopup();
  });

  updateStats();
}

function updateStats() {
  const visibleMarkers = markers.filter(m => m.options.opacity !== 0.1);
  const visibleCount = visibleMarkers.length;
  const visibleStates = new Set(visibleMarkers.map(m => m._stationData.state));

  document.getElementById('station-count').textContent = visibleCount;
  document.getElementById('state-count').textContent = visibleStates.size || 0;
}

// ===== LOCATE ME =====
function locateMe() {
  if (!navigator.geolocation) {
    alert('Geolocation is not supported by your browser.');
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const { latitude, longitude } = pos.coords;
      map.setView([latitude, longitude], 13);

      L.circle([latitude, longitude], {
        radius: 2000,
        color: '#FF9933',
        fillColor: '#FF9933',
        fillOpacity: 0.1,
        weight: 2,
        dashArray: '5, 10'
      }).addTo(map);

      L.marker([latitude, longitude], {
        icon: L.divIcon({
          className: '',
          html: '<div style="width:14px;height:14px;border-radius:50%;background:#FF9933;border:3px solid white;box-shadow:0 0 15px rgba(255,153,51,0.6)"></div>',
          iconSize: [14, 14],
          iconAnchor: [7, 7]
        })
      }).addTo(map).bindPopup('<b>📍 You are here</b>');
    },
    () => alert('Unable to get your location. Please allow location access.'),
    { enableHighAccuracy: true }
  );
}

// ===== CHAT WIDGET =====
let chatOpen = false;

function toggleChat() {
  chatOpen = !chatOpen;
  const widget = document.getElementById('chat-widget');
  const toggle = document.getElementById('chat-toggle');

  widget.classList.toggle('open', chatOpen);
  toggle.classList.toggle('active', chatOpen);
  toggle.innerHTML = chatOpen ? '✕' : '💬';
}

function sendMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;

  addChatMessage(text, 'user');
  input.value = '';

  // Process query locally (simulates Citizen Assist Agent)
  setTimeout(() => processQuery(text), 600);
}

function handleQuickAction(text) {
  document.getElementById('chat-input').value = text;
  sendMessage();
}

function processQuery(query) {
  const lower = query.toLowerCase();
  let matches = [];
  let response = '';

  // Accessibility queries
  if (lower.includes('wheelchair') || lower.includes('ramp') || lower.includes('accessible')) {
    matches = STATIONS.filter(s => s.accessibility.wheelchair_ramp === 'yes');
    response = `♿ Found <b>${matches.length} wheelchair-accessible stations</b>:\n\n`;
    matches.forEach(s => {
      response += `📍 <b>${s.name}</b><br>${s.address}<br>Rating: ${'⭐'.repeat(Math.round(s.accessibility.rating))}<br>`;
      response += `<span class="station-link" onclick="flyToStation('${s.station_id}')">🗺️ Show on map</span><br><br>`;
    });

    // Highlight on map
    highlightStations(matches.map(s => s.station_id));

  } else if (lower.includes('chennai') || lower.includes('t. nagar') || lower.includes('mylapore')) {
    matches = STATIONS.filter(s => s.district === 'Chennai');
    response = `Found <b>${matches.length} stations in Chennai</b>:\n\n`;
    matches.forEach(s => {
      response += `📍 <b>${s.name}</b> (${s.constituency})<br>♿ Ramp: ${s.accessibility.wheelchair_ramp} · Rating: ${s.accessibility.rating}/5<br>`;
      response += `<span class="station-link" onclick="flyToStation('${s.station_id}')">🗺️ Show on map</span><br><br>`;
    });
    highlightStations(matches.map(s => s.station_id));

  } else if (lower.includes('puducherry') || lower.includes('pondicherry')) {
    matches = STATIONS.filter(s => s.state === 'Puducherry');
    response = `Found <b>${matches.length} station in Puducherry</b>:\n\n`;
    matches.forEach(s => {
      response += `📍 <b>${s.name}</b><br>♿ Rating: ${'⭐'.repeat(Math.round(s.accessibility.rating))} (${s.accessibility.rating}/5)<br>`;
      response += `✨ ${s.accessibility.notes}<br>`;
      response += `<span class="station-link" onclick="flyToStation('${s.station_id}')">🗺️ Show on map</span><br><br>`;
    });
    highlightStations(matches.map(s => s.station_id));

  } else if (lower.includes('kerala') || lower.includes('thiruvananthapuram') || lower.includes('trivandrum')) {
    matches = STATIONS.filter(s => s.state === 'Kerala');
    response = `Found <b>${matches.length} station in Kerala</b>:\n\n`;
    matches.forEach(s => {
      response += `📍 <b>${s.name}</b> (${s.constituency})<br>♿ Ramp: ${s.accessibility.wheelchair_ramp} · Audio: ${s.accessibility.audio_booth ? '✅' : '❌'}<br>`;
      response += `<span class="station-link" onclick="flyToStation('${s.station_id}')">🗺️ Show on map</span><br><br>`;
    });
    highlightStations(matches.map(s => s.station_id));

  } else if (lower.includes('all') || lower.includes('list') || lower.includes('how many')) {
    response = `We currently have <b>${STATIONS.length} polling stations</b> across <b>${new Set(STATIONS.map(s => s.state)).size} states</b>:\n\n`;
    STATIONS.forEach(s => {
      response += `• <b>${s.name}</b> — ${s.state} (${s.accessibility.rating}/5 ♿)\n`;
    });

  } else if (lower.includes('vote') || lower.includes('when') || lower.includes('date')) {
    response = `🗓️ <b>Voting Date: May 10, 2026</b><br>⏰ Time: 7:00 AM – 6:00 PM<br><br>`;
    response += `📋 <b>What to bring:</b><br>• Voter ID (EPIC card)<br>• Aadhaar / Passport / DL (if no EPIC)<br>• Avoid wearing party symbols`;

  } else {
    // Generic search across all fields
    matches = STATIONS.filter(s =>
      JSON.stringify(s).toLowerCase().includes(lower)
    );

    if (matches.length > 0) {
      response = `Found <b>${matches.length} matching station(s)</b>:\n\n`;
      matches.forEach(s => {
        response += `📍 <b>${s.name}</b> — ${s.constituency}, ${s.state}<br>`;
        response += `<span class="station-link" onclick="flyToStation('${s.station_id}')">🗺️ Show on map</span><br><br>`;
      });
      highlightStations(matches.map(s => s.station_id));
    } else {
      response = `I couldn't find stations matching "<i>${query}</i>". Try:\n\n`;
      response += `• A city name (Chennai, Puducherry, Thiruvananthapuram)\n`;
      response += `• "Wheelchair accessible stations"\n`;
      response += `• "When is voting?"`;
    }
  }

  addChatMessage(response, 'bot');
}

function addChatMessage(html, type) {
  const container = document.getElementById('chat-messages');
  const msg = document.createElement('div');
  msg.className = `chat-message ${type}`;
  msg.innerHTML = html;
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
}

function flyToStation(stationId) {
  const station = STATIONS.find(s => s.station_id === stationId);
  if (station) {
    map.flyTo([station.lat, station.lng], 15, { duration: 1.5 });
    // Open popup
    markers.forEach(m => {
      if (m._stationData.station_id === stationId) {
        m.openPopup();
      }
    });
  }
}

function highlightStations(stationIds) {
  markers.forEach(m => {
    const isMatch = stationIds.includes(m._stationData.station_id);
    m.setOpacity(isMatch ? 1 : 0.2);
  });

  // Fit to highlighted stations
  const matchedMarkers = markers.filter(m => stationIds.includes(m._stationData.station_id));
  if (matchedMarkers.length > 0) {
    const group = L.featureGroup(matchedMarkers);
    map.flyToBounds(group.getBounds().pad(0.3), { duration: 1 });
  }

  // Reset after 8 seconds
  setTimeout(() => {
    markers.forEach(m => m.setOpacity(1));
  }, 8000);
}

// ===== SEARCH LOGIC =====
document.getElementById('station-search').addEventListener('input', (e) => {
  const query = e.target.value.toLowerCase();
  const resultsDiv = document.getElementById('search-results');
  
  if (query.length < 2) {
    resultsDiv.classList.add('hidden');
    return;
  }
  
  const matches = STATIONS.filter(s => 
    s.name.toLowerCase().includes(query) || 
    s.station_id.toLowerCase().includes(query) ||
    s.address.toLowerCase().includes(query)
  ).slice(0, 5);
  
  if (matches.length > 0) {
    resultsDiv.innerHTML = matches.map(s => `
      <div class="search-item" onclick="selectSearchStation('${s.station_id}')">
        <span class="name">${s.name}</span>
        <span class="meta">${s.station_id} · ${s.district}</span>
      </div>
    `).join('');
    resultsDiv.classList.remove('hidden');
    resultsDiv.style.display = 'block'; // Force visibility
  } else {
    resultsDiv.classList.add('hidden');
  }
});

function selectSearchStation(stationId) {
  document.getElementById('search-results').classList.add('hidden');
  document.getElementById('station-search').value = '';
  flyToStation(stationId);
}

// ===== HELP MODAL LOGIC =====
function openHelp() {
  currentHelpStep = 0;
  updateHelpUI();
  document.getElementById('help-modal').classList.remove('hidden');
}

function closeHelp() {
  document.getElementById('help-modal').classList.add('hidden');
  localStorage.setItem('hasSeenHelp', 'true');
}

function nextHelpStep() {
  if (currentHelpStep < HELP_STEPS.length - 1) {
    currentHelpStep++;
    updateHelpUI();
  } else {
    closeHelp();
  }
}

function prevHelpStep() {
  if (currentHelpStep > 0) {
    currentHelpStep--;
    updateHelpUI();
  }
}

function updateHelpUI() {
  const step = HELP_STEPS[currentHelpStep];
  const content = document.getElementById('help-content');
  const dots = document.getElementById('step-dots');
  
  content.innerHTML = `
    <div class="help-step-icon">${step.icon}</div>
    <div class="help-step-title">${step.title}</div>
    <p class="help-step-text">${step.text}</p>
  `;
  
  dots.innerHTML = HELP_STEPS.map((_, i) => `
    <div class="dot ${i === currentHelpStep ? 'active' : ''}"></div>
  `).join('');
  
  document.getElementById('help-prev').style.display = currentHelpStep === 0 ? 'none' : 'block';
  document.getElementById('help-next').textContent = currentHelpStep === HELP_STEPS.length - 1 ? 'Start Exploring' : 'Next';
}

// Auto-show help for first timers
window.addEventListener('load', () => {
  if (!localStorage.getItem('hasSeenHelp')) {
    setTimeout(openHelp, 1500);
  }
});

// Close search on click outside
document.addEventListener('click', (e) => {
  if (!e.target.closest('.search-box')) {
    document.getElementById('search-results').classList.add('hidden');
  }
});

// ===== KEYBOARD SHORTCUTS =====
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && chatOpen) toggleChat();
  if (e.key === 'Enter' && chatOpen) {
    const input = document.getElementById('chat-input');
    if (document.activeElement === input) sendMessage();
  }
});

// ===== INIT =====
document.addEventListener('DOMContentLoaded', initMap);
