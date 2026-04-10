/* Poll-Rover — Know Your Polling Station
   Production-Grade Map Engine (Optimized Partitioned Version)
   Features: Lazy Loading, Discovery Summary, Satellite Search Index */

let map;
let tileLayer;
let STATIONS = []; // Active detailed stations loaded in memory
let SEARCH_INDEX = [];
let markers = null;
let discoveryMarkers = null; 
let loadedDistricts = new Set();
let currentTheme = localStorage.getItem('theme') || 'dark';

const HELP_STEPS = [
  { icon: "🏗️", title: "Project Poll-Rover", text: "Poll-Rover is a civic initiative to help voters find their booths." },
  { icon: "🧭", title: "Global Search", text: "Type any station name or ID in the search bar above to instantly find your booth." },
  { icon: "🗺️", title: "Live Routing", text: "Click any station marker and select 'Get Directions' to open navigation." },
  { icon: "♿", title: "Accessibility First", text: "Look for Green markers for 100% barrier-free stations." }
];

let activeFilters = { wheelchair: false, audio: false, braille: false, region: [] };
let currentHelpStep = 0;

if (currentTheme === 'light') document.documentElement.classList.add('light-theme');

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
  if (!mapElement) return;

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

  markers = L.markerClusterGroup({
    chunkedLoading: true,
    spiderfyOnMaxZoom: true,
    showCoverageOnHover: false,
    zoomToBoundsOnClick: true
  });
  map.addLayer(markers);

  try {
    const response = await fetch('data/summary.json');
    const summary = await response.json();
    renderDiscoveryMarkers(summary);
  } catch (e) {
    console.error("Failed to load discovery summary:", e);
  }

  initSearch();
}

function renderDiscoveryMarkers(summary) {
    discoveryMarkers = L.layerGroup().addTo(map);
    Object.keys(summary.states).forEach(stateKey => {
        const state = summary.states[stateKey];
        Object.keys(state.districts).forEach(distKey => {
            const dist = state.districts[distKey];
            const distIcon = L.divIcon({
                className: 'district-centroid',
                html: `<div class="centroid-inner"><span>${dist.count}</span></div>`,
                iconSize: [40, 40]
            });
            const marker = L.marker([dist.lat, dist.lng], { icon: distIcon });
            marker.bindTooltip(`<b>${dist.name}</b><br>${dist.count} stations`, { direction: 'top' });
            marker.on('click', () => {
                map.flyTo([dist.lat, dist.lng], 12);
                loadDistrictData(stateKey, distKey);
            });
            discoveryMarkers.addLayer(marker);
        });
    });

    map.on('zoomend', () => {
        if (map.getZoom() > 10) map.removeLayer(discoveryMarkers);
        else map.addLayer(discoveryMarkers);
    });
}

async function loadDistrictData(stateKey, distKey) {
    const dKey = `${stateKey}/${distKey}`;
    if (loadedDistricts.has(dKey)) return;
    try {
        const response = await fetch(`data/stations/${stateKey}/${distKey}.json`);
        const stations = await response.json();
        stations.forEach(s => {
            const station = {
                station_id: s.station_id,
                name: s.name,
                address: s.location?.address || "No address provided",
                lat: s.latitude,
                lng: s.longitude,
                constituency: s.assembly_constituency || "Unknown",
                accessibility: {
                    rating: s.accessibility?.accessibility_rating || 0,
                    wheelchair_ramp: s.accessibility?.description?.includes('Ramp') || false
                },
                voting_date: s.election_details?.voting_date || "April-May, 2026"
            };
            if (station.lat && station.lng) {
                addStationMarker(station);
                STATIONS.push(station);
            }
        });
        loadedDistricts.add(dKey);
        updateStats();
    } catch (e) { console.error(`Failed to load ${dKey}:`, e); }
}

function addStationMarker(station) {
    const color = station.accessibility.rating >= 4.0 ? 'access-high' : station.accessibility.rating >= 2.5 ? 'access-mid' : 'access-low';
    const icon = station.accessibility.rating >= 4.0 ? '♿' : '🏫';
    const customIcon = L.divIcon({
      className: `station-marker ${color}`,
      html: `<div class="marker-inner">${icon}</div>`,
      iconSize: [36, 36],
      iconAnchor: [18, 36]
    });
    const marker = L.marker([station.lat, station.lng], { icon: customIcon });
    marker.bindPopup(`
      <div class="popup-content">
        <span class="constituency">${station.constituency}</span>
        <h3>${station.name}</h3>
        <p>${station.address}</p>
        <a href="https://www.google.com/maps/dir/?api=1&destination=${station.lat},${station.lng}" target="_blank" class="btn-header">🚀 Directions</a>
      </div>
    `);
    markers.addLayer(marker);
}

function updateStats() {
    const countEl = document.getElementById('station-count');
    if (countEl) countEl.innerText = STATIONS.length.toLocaleString();
}

async function initSearch() {
  const searchInput = document.getElementById('station-search');
  const resultsBox = document.getElementById('search-results');
  if (!searchInput) return;

  searchInput.addEventListener('focus', async () => {
    if (SEARCH_INDEX.length === 0) {
        try {
            const resp = await fetch('data/search_index.json');
            SEARCH_INDEX = await resp.json();
        } catch (e) { console.error("Search index fail", e); }
    }
  });

  searchInput.addEventListener('input', (e) => {
    const term = e.target.value.toLowerCase();
    if (!term) { resultsBox.classList.add('hidden'); return; }
    
    const matches = SEARCH_INDEX.filter(s => 
        s[1].toLowerCase().includes(term) || s[0].toLowerCase().includes(term)
    ).slice(0, 10);

    if (matches.length > 0) {
        resultsBox.innerHTML = matches.map(s => `
            <div class="search-item" onclick="selectSearchStation('${s[0]}', '${s[2]}', '${s[3]}')">
                <span class="name">${s[1]}</span>
                <span class="meta">${s[0]}</span>
            </div>
        `).join('');
        resultsBox.classList.remove('hidden');
    } else {
        resultsBox.innerHTML = '<div class="search-item">No results</div>';
    }
  });

  document.addEventListener('click', (e) => {
    if (!searchInput.contains(e.target) && !resultsBox.contains(e.target)) resultsBox.classList.add('hidden');
  });
}

async function selectSearchStation(id, stateKey, distKey) {
    document.getElementById('search-results').classList.add('hidden');
    await loadDistrictData(stateKey, distKey);
    const station = STATIONS.find(s => s.station_id === id);
    if (station) {
        map.flyTo([station.lat, station.lng], 17);
        setTimeout(() => {
            const m = markers.getLayers().find(l => l.getLatLng().lat === station.lat);
            if (m) m.openPopup();
        }, 2000);
    }
}

// Global UI controls
window.toggleTheme = toggleTheme;
window.initMap = initMap;
window.selectSearchStation = selectSearchStation;

initMap();
