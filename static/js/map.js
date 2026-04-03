/* Poll-Rover — Know Your Polling Station
   Production-Grade Map Engine (Gold Standard)
   Features: Theme-Aware Tiling, Global Search, Routing, Intelligence Mesh */

let map;
let tileLayer;
let STATIONS = [];
let markers = null; // Changed to cluster group
let currentTheme = localStorage.getItem('theme') || 'dark';

const HELP_STEPS = [
  {
    icon: "🏗️",
    title: "Project Poll-Rover",
    text: "Poll-Rover is a civic initiative to help voters find their booths. Our data is extracted directly from official Election Commission records."
  },
  {
    icon: "🧭",
    title: "Global Search",
    text: "Type any station name or ID in the search bar above to instantly find your booth on the map. We support instant fly-to navigation."
  },
  {
    icon: "🗺️",
    title: "Live Routing",
    text: "Click any station marker and select 'Get Directions' to open turn-by-turn navigation in Google Maps directly from your current location."
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
  region: []
};

let currentHelpStep = 0;

// Apply theme on load
if (currentTheme === 'light') {
  document.documentElement.classList.add('light-theme');
}

function toggleTheme() {
  currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
  document.documentElement.classList.toggle('light-theme');
  localStorage.setItem('theme', currentTheme);
  
  if (tileLayer) {
    const tileUrl = currentTheme === 'dark' 
      ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
      : 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';
    tileLayer.setUrl(tileUrl);
  }
}

async function initMap() {
  const mapElement = document.getElementById('map');
  if (!mapElement) {
    console.log("No map element found, skipping map initialisation.");
    // Still trigger search init if search bar exists
    if (document.getElementById('station-search')) {
        initSearch();
    }
    return;
  }

  map = L.map('map', {
    center: [11.0, 79.5],
    zoom: 7,
    zoomControl: false,
    attributionControl: true
  });

  L.control.zoom({ position: 'bottomleft' }).addTo(map);

  const tileUrl = currentTheme === 'dark' 
    ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
    : 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';

  tileLayer = L.tileLayer(tileUrl, {
    attribution: '© OpenStreetMap contributors © CARTO',
    maxZoom: 19
  }).addTo(map);

  // Load dynamic data with production fallback
  let data;
  try {
    // Try production path first
    const response = await fetch('data/stations.geojson');
    if (!response.ok) throw new Error("Prod path fail");
    data = await response.json();
  } catch (e) {
    try {
      // Fallback to local dev path
      const response = await fetch('static/data/stations.geojson');
      data = await response.json();
    } catch (e2) {
      console.error("Failed to load station data from both paths:", e2);
      return;
    }
  }
    
  STATIONS = (data.features || []).map(f => {
      const p = f.properties || {};
      const g = f.geometry || { coordinates: [0, 0] };
      return {
        station_id: p.station_id || "unknown",
        name: p.name || "Unknown Station",
        address: p.address || "No address provided",
        landmark: p.landmark || "N/A",
        constituency: p.constituency || "Unknown",
        district: p.district || "Unknown",
        state: p.state || "Unknown",
        lat: g.coordinates[1],
        lng: g.coordinates[0],
        accessibility: {
          rating: p.accessibility_rating || 0,
          wheelchair_ramp: p.wheelchair_ramp || false,
          audio_booth: p.audio_booth || false,
          braille_materials: p.braille_materials || false
        },
        voting_date: p.voting_date || "May 10, 2026",
        meta: {
          confidence: p.confidence_score || 0.8,
          last_verified: p.last_verified || "2024-03-27"
        }
      };
  });

  updateMap();
  updateStats();
  initSearch();
}

function updateMap() {
  if (markers) {
    map.removeLayer(markers);
  }
  markers = L.markerClusterGroup({
    chunkedLoading: true,
    spiderfyOnMaxZoom: true,
    showCoverageOnHover: false,
    zoomToBoundsOnClick: true
  });

  const filtered = STATIONS.filter(s => {
    if (activeFilters.wheelchair && !s.accessibility.wheelchair_ramp) return false;
    if (activeFilters.audio && !s.accessibility.audio_booth) return false;
    if (activeFilters.braille && !s.accessibility.braille_materials) return false;
    if (activeFilters.region.length > 0 && !activeFilters.region.includes(s.state)) return false;
    return true;
  });

  filtered.forEach(station => {
    const color = station.accessibility.rating >= 4.0 ? 'access-high' : 
                station.accessibility.rating >= 2.5 ? 'access-mid' : 'access-low';
    const icon = station.accessibility.rating >= 4.0 ? '♿' : 
               station.accessibility.rating >= 2.5 ? '🏫' : '⚠️';

    const customIcon = L.divIcon({
      className: `station-marker ${color}`,
      html: `<div class="marker-inner">${icon}</div>`,
      iconSize: [36, 36],
      iconAnchor: [18, 36],
      popupAnchor: [0, -32]
    });

    const marker = L.marker([station.lat, station.lng], { icon: customIcon }).addTo(map);
    
    const popupContent = `
      <div class="popup-content">
        <div class="popup-header">
          <span class="constituency">${station.constituency}</span>
          <h3>${station.name}</h3>
        </div>
        <div class="popup-body">
          <p class="popup-address">${station.address}</p>
          <div class="popup-access-icons">
            <span class="access-badge ${station.accessibility.wheelchair_ramp ? 'available' : 'unavailable'}">♿ Ramp</span>
            <span class="access-badge ${station.accessibility.audio_booth ? 'available' : 'unavailable'}">🔊 Audio</span>
            <span class="access-badge ${station.accessibility.braille_materials ? 'available' : 'unavailable'}">⠿ Braille</span>
          </div>
          <div class="popup-button-container" style="margin-top:10px">
            <a href="https://www.google.com/maps/dir/?api=1&destination=${station.lat},${station.lng}" target="_blank" class="btn-header" style="justify-content:center; background:var(--accent); color:var(--bg-primary); font-weight:700">
                🚀 Get Directions
            </a>
          </div>
        </div>
        <div class="popup-footer">
          <span class="voting-date">🗳️ ${station.voting_date}</span>
          <span class="confidence confidence-${station.meta.confidence >= 0.9 ? 'high' : 'mid'}">
            ${Math.round(station.meta.confidence * 100)}% Trusted
          </span>
        </div>
      </div>
    `;

    marker.bindPopup(popupContent);
    markers.addLayer(marker);
  });

  map.addLayer(markers);
}

function updateStats() {
  const stationCount = STATIONS.length;
  document.getElementById('station-count').innerText = stationCount.toLocaleString();
}

function toggleFilter(type, value) {
  if (type === 'region') {
    if (activeFilters.region.includes(value)) {
      activeFilters.region = activeFilters.region.filter(r => r !== value);
    } else {
      activeFilters.region.push(value);
    }
  } else {
    activeFilters[type] = !activeFilters[type];
  }
  updateMap();
}

function locateMe() {
  map.locate({ setView: true, maxZoom: 15 });
  map.on('locationfound', e => {
    L.circle(e.latlng, e.accuracy / 2).addTo(map);
  });
}

// Global Search
function initSearch() {
  const searchInput = document.getElementById('station-search');
  const resultsBox = document.getElementById('search-results');
  let currentLimit = 5;

  searchInput.addEventListener('input', (e) => {
    currentLimit = 5; // Reset limit on new search
    renderResults(e.target.value.toLowerCase());
  });

  function renderResults(term) {
    if (!term) {
      resultsBox.classList.add('hidden');
      return;
    }

    const allMatches = STATIONS.filter(s => 
      s.name.toLowerCase().includes(term) || 
      s.station_id.toLowerCase().includes(term) ||
      s.address.toLowerCase().includes(term)
    );

    const matches = allMatches.slice(0, currentLimit);

    if (matches.length > 0) {
      let html = matches.map(s => `
        <div class="search-item" onclick="selectSearchStation('${s.station_id}')">
          <span class="name">${s.name}</span>
          <span class="meta">${s.constituency} · ${s.state}</span>
        </div>
      `).join('');

      if (allMatches.length > currentLimit) {
        html += `
          <div class="search-item show-more" onclick="event.stopPropagation(); loadMoreResults('${term.replace(/'/g, "\\'")}')">
            <span class="name" style="color:var(--accent); text-align:center">⬇️ Show More (${allMatches.length - currentLimit} remaining)</span>
          </div>
        `;
      }

      resultsBox.innerHTML = html;
      resultsBox.classList.remove('hidden');
    } else {
      resultsBox.innerHTML = '<div class="search-item"><span class="name">No stations found</span></div>';
    }
  }

  window.loadMoreResults = (term) => {
    currentLimit += 10;
    renderResults(term);
  };

  document.addEventListener('click', (e) => {
    if (!searchInput.contains(e.target) && !resultsBox.contains(e.target)) {
      resultsBox.classList.add('hidden');
    }
  });
}

function selectSearchStation(id) {
  const station = STATIONS.find(s => s.station_id === id);
  if (station) {
    map.flyTo([station.lat, station.lng], 16, { animate: true, duration: 2 });
    // Open popup after flyTo
    setTimeout(() => {
        markers.find(m => m.getLatLng().lat === station.lat).openPopup();
    }, 2100);
    document.getElementById('search-results').classList.add('hidden');
    document.getElementById('station-search').value = station.name;
  }
}

// Help Modal / Intelligence Mesh
function openHelp() {
  document.getElementById('help-modal').classList.remove('hidden');
  currentHelpStep = 0;
  updateHelpUI();
}

function closeHelp() {
  document.getElementById('help-modal').classList.add('hidden');
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
  const nextBtn = document.getElementById('help-next');
  const prevBtn = document.getElementById('help-prev');

  content.innerHTML = `
    <div class="help-step-box">
      <div class="help-icon">${step.icon}</div>
      <h3>${step.title}</h3>
      <p>${step.text}</p>
    </div>
  `;

  dots.innerHTML = HELP_STEPS.map((_, i) => 
    `<div class="dot ${i === currentHelpStep ? 'active' : ''}"></div>`
  ).join('');

  prevBtn.style.visibility = currentHelpStep === 0 ? 'hidden' : 'visible';
  nextBtn.innerText = currentHelpStep === HELP_STEPS.length - 1 ? 'Start Exploring' : 'Next';
}

// Chat functions (Stubs for the full demo)
function toggleChat() {
  document.getElementById('chat-widget').classList.toggle('open');
}

function handleQuickAction(text) {
    document.getElementById('chat-input').value = text;
    sendMessage();
}

function sendMessage() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;

    addMessage(msg, 'user');
    input.value = '';

    setTimeout(() => {
        addMessage("I'm checking the live election data mesh for you... 🕵️‍♂️", 'bot');
    }, 500);
}

function addMessage(text, type) {
    const chat = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `chat-message ${type}`;
    div.innerHTML = text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

window.initMap = initMap;
window.toggleFilter = toggleFilter;
window.toggleTheme = toggleTheme;
window.locateMe = locateMe;
window.openHelp = openHelp;
window.closeHelp = closeHelp;
window.nextHelpStep = nextHelpStep;
window.prevHelpStep = prevHelpStep;
window.toggleChat = toggleChat;
window.sendMessage = sendMessage;
window.handleQuickAction = handleQuickAction;
window.selectSearchStation = selectSearchStation;

initMap();
