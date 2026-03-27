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
    const response = await fetch('data/stations.geojson');
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
