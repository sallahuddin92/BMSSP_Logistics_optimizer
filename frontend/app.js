// Global state
let map;
let currentMode = 'depot'; // 'depot' or 'stops'
let depot = null;
let stops = [];
let routeMarkers = [];
let routeLines = [];
let nearestNodes = [];
let selectionVersion = 0;
let solving = false;

// Route colors for multiple vehicles
const ROUTE_COLORS = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FCEA2B',
    '#FF9F43', '#EE5A52', '#0FB9B1', '#3742FA', '#2F3542'
];

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeMap();
    initializeUI();
    loadInitialData();
    
    // Additional fixes for map positioning
    setTimeout(() => {
        if (map) {
            map.invalidateSize(true);
            console.log('Additional map size fix applied');
        }
    }, 500);
    
    // Fix on window load as well
    window.addEventListener('load', () => {
        if (map) {
            map.invalidateSize(true);
            console.log('Map size fixed on window load');
        }
    });
});

function initializeMap() {
    map = L.map('map').setView([2.5, 102.5], 7);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors', maxZoom: 18
    }).addTo(map);
    addCoverageAreas();
    map.on('click', handleMapClick);
    map.zoomControl.setPosition('bottomright');
    window.addEventListener('resize', () => map.invalidateSize());
}

function initializeUI() {
    // Mode buttons
    document.getElementById('depot-mode').addEventListener('click', () => setMode('depot'));
    document.getElementById('stop-mode').addEventListener('click', () => setMode('stops'));
    
    // Vehicle count input
    document.getElementById('vehicle-input').addEventListener('change', () => { updateVehicleCount(); invalidateSolution(); });
    document.getElementById('engine-select').addEventListener('change', () => {
        const legacy = document.getElementById('engine-select').value === 'legacy_networkx';
        const roads = document.getElementById('road-select');
        roads.disabled = legacy;
        if (legacy && roads.value) { roads.value = ''; clearAll(); }
        else invalidateSolution();
    });
    document.getElementById('road-select').addEventListener('change', clearAll);
    
    // Advanced options toggle
    document.getElementById('advanced-toggle').addEventListener('click', toggleAdvancedOptions);
    
    // Capacity and time window checkboxes
    document.getElementById('enable-capacity').addEventListener('change', toggleCapacityInputs);
    document.getElementById('enable-time-windows').addEventListener('change', toggleTimeInputs);
    
    for (const id of ['enable-capacity','enable-time-windows','default-capacity','default-demand','default-start-time','default-end-time','duration-matrix','service-duration']) {
        document.getElementById(id).addEventListener('change', invalidateSolution);
    }
    // Action buttons
    document.getElementById('solve-btn').addEventListener('click', solveRoutes);
    document.getElementById('clear-btn').addEventListener('click', clearAll);
    
    // Set initial state
    updateInstructions();
    updateUI();
}

async function loadInitialData() {
    try {
        // Load available cities (optional feature)
        const response = await fetch(`${getBackendUrl()}/cities`);
        if (response.ok) {
            const data = await response.json();
            console.log('Available cities:', data.cities);
        }
    } catch (error) {
        console.warn('Could not load initial data:', error);
    }
}

function getBackendUrl() {
    // Use environment variable or default to localhost
    if (window.BMSSP_BACKEND_URL) return window.BMSSP_BACKEND_URL;
    return window.location.hostname === 'localhost' 
        ? 'http://localhost:8000' 
        : `http://${window.location.hostname}:8000`;
}

function setMode(mode) {
    currentMode = mode;
    
    // Update button states
    document.getElementById('depot-mode').classList.toggle('active', mode === 'depot');
    document.getElementById('stop-mode').classList.toggle('active', mode === 'stops');
    
    updateInstructions();
}

function updateInstructions() {
    const instructionEl = document.getElementById('instruction-text');
    const icon = instructionEl.querySelector('i');
    
    if (currentMode === 'depot' && !depot) {
        icon.className = 'fas fa-warehouse';
        instructionEl.innerHTML = '<i class="fas fa-warehouse"></i> Click on the map to set your depot location';
    } else if (currentMode === 'depot' && depot) {
        icon.className = 'fas fa-check-circle';
        instructionEl.innerHTML = '<i class="fas fa-check-circle"></i> Depot set! Switch to "Add Stops" mode to add delivery locations';
    } else if (currentMode === 'stops' && stops.length === 0) {
        icon.className = 'fas fa-map-marker-alt';
        instructionEl.innerHTML = '<i class="fas fa-map-marker-alt"></i> Click on the map to add delivery stops';
    } else if (currentMode === 'stops' && stops.length > 0) {
        icon.className = 'fas fa-plus-circle';
        instructionEl.innerHTML = '<i class="fas fa-plus-circle"></i> Continue adding stops or click "Solve Routes" to optimize';
    }
}

async function handleMapClick(e) {
    const version = selectionVersion;
    const mode = currentMode;
    try {
        let data;
        for (const radius of [1000, 2000, 5000, 10000]) {
            const response = await fetch(`${getBackendUrl()}/search-nodes?engine=${encodeURIComponent(document.getElementById("engine-select").value)}&place=${encodeURIComponent(document.getElementById("road-select").value)}`, {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({lat: e.latlng.lat, lon: e.latlng.lng, radius})
            });
            if (!response.ok) throw new Error('Nearby road search is unavailable. Load road data and retry.');
            data = await response.json();
            if (data.nodes && data.nodes.length) break;
        }
        if (selectionVersion !== version) return;
        if (!data || !data.nodes || !data.nodes.length) {
            showToast('No road node found within 10 km.', 'warning'); return;
        }
        const node = normalizeNode(data.nodes[0]);
        if (mode === 'depot') setDepot(node); else addStop(node);
    } catch (error) { showToast(error.message || 'Road search failed.', 'error'); }
}

function normalizeNode(node) { return RoutingContract.normalizeNode(node); }

function invalidateSolution() {
    selectionVersion++;
    clearRoutes();
    document.getElementById('results').style.display = 'none';
    document.getElementById('total-distance').textContent = '-';
}

function setDepot(node) {
    node = normalizeNode(node);
    if (stops.some(stop => stop.node_id === node.node_id)) { showToast('Remove this stop before using it as depot.', 'warning'); return; }
    invalidateSolution();
    console.log('setDepot called with node:', node);
    
    // Remove existing depot
    if (depot && depot.marker) {
        console.log('Removing existing depot marker');
        map.removeLayer(depot.marker);
    }
    
    // Create depot marker
    console.log('Creating depot marker at:', node.lat, node.lon);
    const marker = L.marker([node.lat, node.lon], {
        interactive: false,
        icon: L.divIcon({
            className: 'depot-marker',
            html: '<div class="depot-icon"><i class="fas fa-warehouse"></i></div>',
            iconSize: [30, 30],
            iconAnchor: [15, 15]
        })
    }).addTo(map);
    
    console.log('Depot marker created and added to map');
    
    depot = {
        node_id: node.node_id,
        lat: node.lat,
        lon: node.lon,
        marker: marker
    };
    
    console.log('Depot object set:', depot);
    
    // Update UI
    const depotCoordsEl = document.getElementById('depot-coords');
    const depotInfoEl = document.getElementById('depot-info');
    
    console.log('Updating UI elements:', depotCoordsEl, depotInfoEl);
    
    if (depotCoordsEl) {
        depotCoordsEl.textContent = `${node.lat.toFixed(4)}, ${node.lon.toFixed(4)}`;
    }
    if (depotInfoEl) {
        depotInfoEl.style.display = 'flex';
    }
    
    updateInstructions();
    updateUI();
    showToast('Depot location set!', 'success');
    console.log('setDepot completed successfully');
}

function addStop(node) {
    node = normalizeNode(node);
    if (depot && depot.node_id === node.node_id) { showToast('The depot is already selected.', 'warning'); return; }
    // Check if this node is already added
    const existingStop = stops.find(stop => stop.node_id === node.node_id);
    if (existingStop) {
        showToast('This location is already added as a stop', 'warning');
        return;
    }
    
    invalidateSolution();
    // Create stop marker
    const stopNumber = stops.length + 1;
    const marker = L.marker([node.lat, node.lon], {
        interactive: false,
        icon: L.divIcon({
            className: 'stop-marker',
            html: `<div class="stop-icon">${stopNumber}</div>`,
            iconSize: [25, 25],
            iconAnchor: [12.5, 12.5]
        })
    }).addTo(map);
    
    const stop = {
        node_id: node.node_id,
        lat: node.lat,
        lon: node.lon,
        marker: marker,
        index: stops.length
    };
    
    stops.push(stop);
    
    // Add to stops list in sidebar
    addStopToList(stop, stopNumber);
    
    updateInstructions();
    updateUI();
    showToast(`Stop ${stopNumber} added!`, 'success');
}

function addStopToList(stop, number) {
    const stopsList = document.getElementById('stops-list');
    
    const stopItem = document.createElement('div');
    stopItem.className = 'location-item stop';
    stopItem.setAttribute('data-stop-index', stop.index);
    
    stopItem.innerHTML = `
        <i class="fas fa-map-marker-alt"></i>
        <span class="location-text">Stop ${number}: ${stop.lat.toFixed(4)}, ${stop.lon.toFixed(4)}</span>
        <button class="remove-btn" onclick="removeStop(${stop.index})">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    stopsList.appendChild(stopItem);
}

function removeDepot() {
    invalidateSolution();
    if (depot && depot.marker) {
        map.removeLayer(depot.marker);
    }
    depot = null;
    document.getElementById('depot-info').style.display = 'none';
    updateInstructions();
    updateUI();
    showToast('Depot removed', 'info');
}

function removeStop(index) {
    invalidateSolution();
    const stop = stops[index];
    if (stop && stop.marker) {
        map.removeLayer(stop.marker);
    }
    
    // Remove from array
    stops.splice(index, 1);
    
    // Update all stop indices and markers
    stops.forEach((stop, i) => {
        stop.index = i;
        // Update marker number
        const newNumber = i + 1;
        stop.marker.getElement().querySelector('.stop-icon').textContent = newNumber;
    });
    
    // Rebuild stops list
    const stopsList = document.getElementById('stops-list');
    stopsList.innerHTML = '';
    stops.forEach((stop, i) => {
        addStopToList(stop, i + 1);
    });
    
    updateInstructions();
    updateUI();
    showToast('Stop removed', 'info');
}

function updateVehicleCount() {
    const count = parseInt(document.getElementById('vehicle-input').value);
    document.getElementById('vehicle-count').textContent = count;
}

function toggleAdvancedOptions() {
    const options = document.getElementById('advanced-options');
    const toggle = document.getElementById('advanced-toggle');
    const icon = toggle.querySelector('i');
    
    const isOpen = options.style.display === 'block';
    options.style.display = isOpen ? 'none' : 'block';
    icon.className = isOpen ? 'fas fa-chevron-down' : 'fas fa-chevron-up';
}

function toggleCapacityInputs() {
    const enabled = document.getElementById('enable-capacity').checked;
    const inputs = document.getElementById('capacity-inputs');
    inputs.style.display = enabled ? 'block' : 'none';
}

function toggleTimeInputs() {
    const enabled = document.getElementById('enable-time-windows').checked;
    const inputs = document.getElementById('time-inputs');
    inputs.style.display = enabled ? 'block' : 'none';
}

function updateUI() {
    // Update location count
    document.getElementById('location-count').textContent = depot ? stops.length + 1 : stops.length;
    
    // Enable/disable solve button
    const canSolve = depot && stops.length > 0 && !solving;
    document.getElementById('solve-btn').disabled = !canSolve;
}

async function solveRoutes() {
    if (!depot || !stops.length || solving) return;
    invalidateSolution();
    const version = selectionVersion;
    solving = true; updateUI();
    document.getElementById('loading').style.display = 'block';
    try {
        const locations = [depot.node_id, ...stops.map(x => x.node_id)];
        const integer = (id) => {
            const raw = document.getElementById(id).value.trim();
            if (!raw) throw new Error('Complete all enabled numeric fields; zero is allowed.');
            const value = Number(raw);
            if (!Number.isSafeInteger(value) || value < 0) throw new Error('Enter nonnegative whole-number counts.');
            return value;
        };
        const count = integer('vehicle-input');
        if (count < 1 || count > 10) throw new Error('Choose 1 to 10 vehicles.');
        const request = {locations, vehicle_count: count, depot: 0, engine: document.getElementById('engine-select').value, place: document.getElementById('road-select').value || null};
        if (document.getElementById('enable-capacity').checked) {
            request.capacities = Array(count).fill(integer('default-capacity'));
            request.demands = [0, ...stops.map(() => integer('default-demand'))];
        }
        if (document.getElementById('enable-time-windows').checked) {
            if (['default-start-time','default-end-time','service-duration'].some(id => !document.getElementById(id).value.trim())) throw new Error('Complete the enabled seconds fields.');
            const start = Number(document.getElementById('default-start-time').value);
            const end = Number(document.getElementById('default-end-time').value);
            if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end < start) throw new Error('Enter valid time windows in seconds.');
            request.time_windows = locations.map(() => [start, end]);
            const durations = document.getElementById('duration-matrix').value.trim();
            if (durations) request.duration_matrix = JSON.parse(durations);
            const service = Number(document.getElementById('service-duration').value);
            if (!Number.isFinite(service) || service < 0) throw new Error('Service duration must be nonnegative seconds.');
            request.service_durations = [0, ...stops.map(() => service)];
        }
        const response = await fetch(`${getBackendUrl()}/vrp`, {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(request)
        });
        if (selectionVersion !== version) return;
        if (!response.ok) {
            let message = response.status >= 500 ? 'Routing is unavailable or failed. Check that native road data and the module are loaded.' : 'Invalid route request. Check stops, capacities and duration/time inputs.';
            if (response.status === 413) message = 'Request exceeds the routing resource budget. Reduce stops or vehicles.';
            if (response.status === 400) {
                const details = await response.json();
                if (typeof details.detail === 'string' && /duration|time window|capacity|capacities|demand|duplicate/i.test(details.detail)) message = details.detail;
            }
            throw new Error(message);
        }
        const solution = await response.json();
        if (solution.selected_engine !== request.engine) throw new Error('Unexpected routing engine in response.');
        displaySolution(solution);
    } catch (error) {
        if (selectionVersion === version) showToast(error instanceof SyntaxError ? 'Duration matrix must be valid JSON seconds.' : error.message, 'error');
    } finally {
        solving = false;
        document.getElementById('loading').style.display = 'none';
        updateUI();
    }
}

function displaySolution(solution) {
    clearRoutes();
    const accepted = RoutingContract.validSolution(solution);
    document.getElementById('results').style.display = 'block';
    if (!accepted) {
        document.getElementById('total-distance').textContent = '-';
        document.getElementById('results-content').textContent = `No verified route: ${['NO_SOLUTION','TIMEOUT','INVALID_INPUT'].includes(solution.status) ? solution.status : 'FAILED'}. Check reachability, capacities and time inputs.`;
        showToast('No feasible route was established.', 'warning'); return false;
    }
    const native = solution.selected_engine !== 'legacy_networkx';
    if (native && (!solution.exact_routing || !Array.isArray(solution.route_legs)
        || solution.route_legs.length !== solution.routes.length
        || solution.route_legs.some((legs, i) => legs.length !== solution.routes[i].length-1 || legs.some(l => l.path_status !== 'VERIFIED')))) {
        document.getElementById('results-content').textContent = 'Invalid native route verification data.';
        return false;
    }
    const validPoint = p => Array.isArray(p) && p.length === 2 && p.every(Number.isFinite) && Math.abs(p[0])<=90 && Math.abs(p[1])<=180;
    const routeInfos = solution.routes.map((route, i) => ({vehicle: i+1, stops: Math.max(0, route.length-2),
        distance: solution.vehicle_distances[i], assignment: route.slice(1,-1).map(index => `Stop ${index}`).join(' → ') || 'Unused vehicle', color: ROUTE_COLORS[i % ROUTE_COLORS.length]}));
    const segments = native ? solution.route_geometry_segments : (solution.route_geometries || []).map(g => [g]);
    let unavailable = false;
    const endpointGeometry = native && solution.route_legs.some(legs => legs.some(l => l.geometry_status === 'ENDPOINTS_ONLY'));
    (segments || []).forEach((parts, i) => parts.forEach(points => {
        if (Array.isArray(points) && points.length === 1 && validPoint(points[0])) return;
        if (!points || points.length<2 || !points.every(validPoint)) { unavailable = true; return; }
        routeLines.push(L.polyline(points, {color: ROUTE_COLORS[i % ROUTE_COLORS.length], weight:4, opacity:.8}).addTo(map));
    }));
    if (native && solution.route_legs.some(legs => legs.some(l => l.geometry_status === 'UNAVAILABLE'))) unavailable = true;
    document.getElementById('total-distance').textContent = formatDistanceKm(solution.total_distance);
    displayResults(routeInfos, solution);
    const label = document.createElement('p');
    label.textContent = `Engine: ${solution.selected_engine} · ${solution.status}${solution.exact_routing ? '' : ' · Legacy approximation / non-certified'}${unavailable ? ' · Some geometry unavailable' : ''}${endpointGeometry ? ' · Some edges have endpoint-only geometry' : ''}`;
    document.getElementById('results-content').prepend(label);
    if (routeLines.length) map.fitBounds(L.featureGroup(routeLines).getBounds().pad(.1));
    showToast(solution.status === 'APPROXIMATED' ? 'Approximate legacy result.' : 'Feasible routes found; global optimality is not claimed.', solution.exact_routing ? 'success' : 'warning');
    return true;
}

function displayResults(routeInfos, solution) {
    const resultsDiv = document.getElementById('results-content');
    
    let html = `
        <div class="result-summary">
            <div class="result-metric">
                <span class="metric-label">Total Distance:</span>
                <span class="metric-value">${formatDistanceKm(solution.total_distance)}</span>
            </div>
            <div class="result-metric">
                <span class="metric-label">Computation Time:</span>
                <span class="metric-value">${solution.computation_times.total.toFixed(2)}s</span>
            </div>
        </div>
        <div class="route-details">
    `;
    
    routeInfos.forEach(route => {
        html += `
            <div class="route-item">
                <div class="route-header" style="border-left-color: ${route.color}">
                    <span class="route-title">Vehicle ${route.vehicle}</span>
                    <span class="route-distance">${formatDistanceKm(route.distance)}</span>
                </div>
                <div class="route-info">
                    <span class="route-stops">${route.stops} stops · ${route.assignment}</span>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    resultsDiv.innerHTML = html;
    
    document.getElementById('results').style.display = 'block';
}

function clearRoutes() {
    // Remove existing route lines
    routeLines.forEach(line => map.removeLayer(line));
    routeLines = [];
}

function clearAll() {
    // Remove depot
    removeDepot();
    
    // Remove all stops
    while (stops.length > 0) {
        removeStop(0);
    }
    
    // Clear routes
    clearRoutes();
    
    // Reset UI
    document.getElementById('total-distance').textContent = '-';
    document.getElementById('results').style.display = 'none';
    
    // Reset mode to depot
    setMode('depot');
    
    showToast('All locations cleared', 'info');
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icon = type === 'success' ? 'fas fa-check-circle' :
                type === 'warning' ? 'fas fa-exclamation-triangle' :
                type === 'error' ? 'fas fa-times-circle' :
                'fas fa-info-circle';
    
    const text = document.createElement("span");
    text.textContent = message;
    toast.appendChild(text);
    
    container.appendChild(toast);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.classList.add('fade-out');
            setTimeout(() => {
                if (toast.parentNode) {
                    container.removeChild(toast);
                }
            }, 300);
        }
    }, 3000);
}

function addCoverageAreas() {
    // Coverage area for Malaysia, Singapore, and Brunei
    const malaysiaBounds = [
        [0.5, 99.5],    // Southwest corner
        [7.5, 119.5]    // Northeast corner
    ];
    
    // Add a rectangle to show the coverage area
    L.rectangle(malaysiaBounds, {
        interactive: false,
        color: '#4ECDC4',
        fillColor: '#4ECDC4',
        fillOpacity: 0.05,
        weight: 2,
        opacity: 0.3
    }).addTo(map).bindPopup('<strong>Malaysia, Singapore & Brunei</strong><br>Click anywhere in this region to add locations');
    
    // Add major city markers for reference
    const majorCities = [
        { name: 'Kuala Lumpur', coords: [3.139, 101.6869] },
        { name: 'Singapore', coords: [1.3521, 103.8198] },
        { name: 'Penang', coords: [5.4164, 100.3327] },
        { name: 'Johor Bahru', coords: [1.4927, 103.7414] },
        { name: 'Kota Kinabalu', coords: [5.9749, 116.0724] },
        { name: 'Kuching', coords: [1.5533, 110.3592] }
    ];
    
    majorCities.forEach(city => {
        L.circleMarker(city.coords, {
            interactive: false,
            color: '#007bff',
            fillColor: '#007bff',
            fillOpacity: 0.3,
            radius: 8,
            weight: 2
        }).addTo(map).bindPopup(`<strong>${city.name}</strong><br>Major city reference`);
    });
    
    // Add a legend
    const legend = L.control({position: 'topright'});
    legend.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'legend');
        div.innerHTML = `
            <div style="background: white; padding: 10px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
                <h4 style="margin: 0 0 5px 0;">Map reference area</h4>
                <div style="display: flex; align-items: center; margin-bottom: 3px;">
                    <div style="width: 15px; height: 15px; background: #4ECDC4; opacity: 0.3; margin-right: 8px;"></div>
                    <span style="font-size: 12px;">Malaysia, Singapore & Brunei</span>
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 3px;">
                    <div style="width: 15px; height: 15px; background: #007bff; opacity: 0.3; border-radius: 50%; margin-right: 8px;"></div>
                    <span style="font-size: 12px;">Major cities</span>
                </div>
                <p style="font-size: 11px; margin: 5px 0 0 0; color: #666;">
                    Road data coverage must be verified separately
                </p>
            </div>
        `;
        return div;
    };
    legend.addTo(map);
}

function formatDistanceKm(val) {
  if (val === null || val === undefined) return '–';
  
  // Force conversion from meters to kilometers
  let meters = parseFloat(val);
  if (isNaN(meters) || !isFinite(meters)) return '–';
  
  // Convert meters to kilometers by dividing by 1000
  let kilometers = meters / 1000.0;
  
  if (kilometers >= 1.0) {
    // Show as kilometers with 2 decimal places
    return kilometers.toFixed(2) + ' km';
  } else {
    // Show as meters rounded to nearest whole number
    return Math.round(meters) + ' m';
  }
}