// Global state
let map;
let currentMode = 'depot'; // 'depot' or 'stops'
let depot = null;
let stops = [];
let routeMarkers = [];
let routeLines = [];
let nearestNodes = [];

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
    console.log('Initializing map...');
    // Initialize map centered between KL and Singapore  
    map = L.map('map').setView([2.5, 102.5], 7);
    console.log('Map created:', map);
    
    // Add tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }).addTo(map);
    
    // Add coverage area indicators
    addCoverageAreas();
    
    // Add raw DOM click handler to override Leaflet's coordinate calculation
    document.getElementById('map').addEventListener('click', function(domEvent) {
        console.log('Raw DOM click intercepted');
        
        const mapContainer = document.getElementById('map');
        const containerRect = mapContainer.getBoundingClientRect();
        
        // Calculate correct relative position
        const relativeX = domEvent.clientX - containerRect.left;
        const relativeY = domEvent.clientY - containerRect.top;
        
        console.log('DOM click details:', {
            clientX: domEvent.clientX,
            clientY: domEvent.clientY,
            containerLeft: containerRect.left,
            containerTop: containerRect.top,
            relativeX: relativeX,
            relativeY: relativeY
        });
        
        // Convert to lat/lng using map's containerPointToLatLng
        const containerPoint = L.point(relativeX, relativeY);
        const latLng = map.containerPointToLatLng(containerPoint);
        
        console.log('Corrected coordinates:', latLng);
        
        // Create a synthetic event object
        const syntheticEvent = {
            latlng: latLng,
            containerPoint: containerPoint,
            layerPoint: containerPoint,
            originalEvent: domEvent
        };
        
        // Call our handler with corrected coordinates
        handleMapClick(syntheticEvent);
        
        // Prevent the original Leaflet click from firing
        domEvent.stopPropagation();
    });
    console.log('Map click handler added');

    // Add zoom control
    map.zoomControl.setPosition('bottomright');
    
    // Fix map size calculation after DOM is ready
    setTimeout(() => {
        map.invalidateSize();
        console.log('Map size invalidated and recalculated');
        
        // Debug container positioning
        const mapContainer = document.getElementById('map');
        const containerRect = mapContainer.getBoundingClientRect();
        console.log('Map container position:', {
            left: containerRect.left,
            top: containerRect.top,
            width: containerRect.width,
            height: containerRect.height
        });
    }, 100);
    
    // Also invalidate size when window is resized
    window.addEventListener('resize', () => {
        map.invalidateSize();
    });
}

function initializeUI() {
    // Mode buttons
    document.getElementById('depot-mode').addEventListener('click', () => setMode('depot'));
    document.getElementById('stop-mode').addEventListener('click', () => setMode('stops'));
    
    // Vehicle count input
    document.getElementById('vehicle-input').addEventListener('change', updateVehicleCount);
    
    // Advanced options toggle
    document.getElementById('advanced-toggle').addEventListener('click', toggleAdvancedOptions);
    
    // Capacity and time window checkboxes
    document.getElementById('enable-capacity').addEventListener('change', toggleCapacityInputs);
    document.getElementById('enable-time-windows').addEventListener('change', toggleTimeInputs);
    
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
    console.log('Map clicked!', e.latlng);
    const lat = e.latlng.lat;
    const lon = e.latlng.lng;
    
    // Add temporary red marker to show exactly where click was registered
    const tempMarker = L.circleMarker([lat, lon], {
        color: 'red',
        fillColor: 'red',
        fillOpacity: 0.8,
        radius: 10,
        weight: 2
    }).addTo(map);
    
    // Remove temp marker after 2 seconds
    setTimeout(() => {
        map.removeLayer(tempMarker);
    }, 2000);
    
    console.log('Current mode:', currentMode);
    console.log('Searching for nodes at:', lat, lon);
    console.log('Backend URL:', getBackendUrl());
    
    try {
        // Find nearest nodes to the clicked location with progressive search radius
        let data = null;
        const searchRadii = [1000, 2000, 5000, 10000, 20000, 50000]; // Progressive search from 1km to 50km
        
        for (const radius of searchRadii) {
            console.log('Trying radius:', radius);
            const requestBody = { lat, lon, radius };
            console.log('Request body:', requestBody);
            
            const response = await fetch(`${getBackendUrl()}/search-nodes`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });
            
            console.log('Response status:', response.status);
            console.log('Response ok:', response.ok);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.log('Error response:', errorText);
                throw new Error(`Failed to find nearby nodes: ${response.status} ${errorText}`);
            }
            
            data = await response.json();
            console.log('API Response data:', data);
            console.log('Found nodes:', data.nodes ? data.nodes.length : 0);
            
            if (data.nodes && data.nodes.length > 0) {
                break; // Found nodes, stop searching
            }
        }
        
        if (!data || !data.nodes || data.nodes.length === 0) {
            showToast('No nearby road nodes found within 50km. Try clicking closer to a major road or city center in Malaysia, Singapore, or Brunei.', 'warning');
            return;
        }
        
        const nearestNode = data.nodes[0];
        console.log('Selected nearest node:', nearestNode);
        
        if (currentMode === 'depot') {
            console.log('Setting depot with node:', nearestNode);
            setDepot(nearestNode);
        } else {
            console.log('Adding stop with node:', nearestNode);
            addStop(nearestNode);
        }
        
    } catch (error) {
        console.error('Error handling map click:', error);
        showToast('Error finding nearby locations. Please try again.', 'error');
    }
}

function setDepot(node) {
    console.log('setDepot called with node:', node);
    
    // Remove existing depot
    if (depot && depot.marker) {
        console.log('Removing existing depot marker');
        map.removeLayer(depot.marker);
    }
    
    // Create depot marker
    console.log('Creating depot marker at:', node.lat, node.lon);
    const marker = L.marker([node.lat, node.lon], {
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
    // Check if this node is already added
    const existingStop = stops.find(stop => stop.node_id === node.node_id);
    if (existingStop) {
        showToast('This location is already added as a stop', 'warning');
        return;
    }
    
    // Create stop marker
    const stopNumber = stops.length + 1;
    const marker = L.marker([node.lat, node.lon], {
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
    const canSolve = depot && stops.length > 0;
    document.getElementById('solve-btn').disabled = !canSolve;
}

async function solveRoutes() {
    if (!depot || stops.length === 0) {
        showToast('Please set a depot and add at least one stop', 'warning');
        return;
    }
    
    // Show loading
    document.getElementById('loading').style.display = 'block';
    document.getElementById('results').style.display = 'none';
    
    try {
        // Prepare request data
        const locations = [depot.node_id, ...stops.map(stop => stop.node_id)];
        const vehicleCount = parseInt(document.getElementById('vehicle-input').value);
        
        const requestData = {
            locations: locations,
            vehicle_count: vehicleCount,
            depot: 0 // Depot is always first in locations array
        };
        
        // Add capacity constraints if enabled
        if (document.getElementById('enable-capacity').checked) {
            const capacity = parseInt(document.getElementById('default-capacity').value) || 100;
            const demand = parseInt(document.getElementById('default-demand').value) || 10;
            
            requestData.capacities = Array(vehicleCount).fill(capacity);
            requestData.demands = [0, ...Array(stops.length).fill(demand)]; // Depot has 0 demand
        }
        
        // Add time windows if enabled
        if (document.getElementById('enable-time-windows').checked) {
            const startTime = parseInt(document.getElementById('default-start-time').value) || 0;
            const endTime = parseInt(document.getElementById('default-end-time').value) || 1000;
            
            requestData.time_windows = Array(locations.length).fill([startTime, endTime]);
        }
        
        // Solve VRP
        const response = await fetch(`${getBackendUrl()}/vrp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            // Handle validation errors (422) which return array of error objects
            let errorMessage = 'Failed to solve routes';
            if (Array.isArray(errorData.detail)) {
                errorMessage = errorData.detail.map(err => err.msg || err).join(', ');
            } else if (typeof errorData.detail === 'string') {
                errorMessage = errorData.detail;
            }
            throw new Error(errorMessage);
        }
        
        const solution = await response.json();
        displaySolution(solution);
        
    } catch (error) {
        console.error('Error solving routes:', error);
        showToast(`Error solving routes: ${error.message || error}`, 'error');
    } finally {
        document.getElementById('loading').style.display = 'none';
    }
}

function displaySolution(solution) {
    // Clear existing routes
    clearRoutes();
    
    const routes = solution.routes;
    const locationCoords = solution.location_coordinates;
    const routeGeometries = solution.route_geometries || [];
    
    let totalDistance = 0;
    const routeInfos = [];
    
    // Draw routes using real road paths if available
    routeGeometries.forEach((geometry, vehicleIndex) => {
        if (!geometry || geometry.length < 2) return;
        const color = ROUTE_COLORS[vehicleIndex % ROUTE_COLORS.length];
        const latlngs = geometry.map(pt => [pt.lat, pt.lon]);
        const routeLine = L.polyline(latlngs, {
            color: color,
            weight: 4,
            opacity: 0.8
        }).addTo(map);
        routeLines.push(routeLine);
        // Add route info
        const vehicleDistance = solution.vehicle_distances[vehicleIndex] || 0;
        totalDistance += vehicleDistance;
        routeInfos.push({
            vehicle: vehicleIndex + 1,
            stops: routes[vehicleIndex] ? routes[vehicleIndex].length - 1 : 0, // Exclude depot
            distance: vehicleDistance,
            color: color
        });
    });
    // Fallback: if no geometries, use old method
    if (routeGeometries.length === 0) {
        routes.forEach((route, vehicleIndex) => {
            if (route.length <= 2) return; // Skip empty routes (just depot)
            const color = ROUTE_COLORS[vehicleIndex % ROUTE_COLORS.length];
            const routeCoords = [];
            route.forEach(locationIndex => {
                const nodeId = solution.locations[locationIndex];
                if (locationCoords[nodeId]) {
                    routeCoords.push([locationCoords[nodeId].lat, locationCoords[nodeId].lon]);
                }
            });
            if (routeCoords.length > 1) {
                const routeLine = L.polyline(routeCoords, {
                    color: color,
                    weight: 4,
                    opacity: 0.8
                }).addTo(map);
                routeLines.push(routeLine);
                const vehicleDistance = solution.vehicle_distances[vehicleIndex] || 0;
                totalDistance += vehicleDistance;
                routeInfos.push({
                    vehicle: vehicleIndex + 1,
                    stops: route.length - 1, // Exclude depot
                    distance: vehicleDistance,
                    color: color
                });
            }
        });
    }
    
    // Update total distance display
    document.getElementById('total-distance').textContent = formatDistanceKm(totalDistance);
    
    // Display results
    displayResults(routeInfos, solution);
    
    // Fit map to show all routes
    if (routeLines.length > 0) {
        const group = new L.featureGroup(routeLines);
        map.fitBounds(group.getBounds().pad(0.1));
    }
    
    showToast('Routes optimized successfully!', 'success');
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
                    <span class="route-stops">${route.stops} stops</span>
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
    
    toast.innerHTML = `
        <i class="${icon}"></i>
        <span>${message}</span>
    `;
    
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
                <h4 style="margin: 0 0 5px 0;">Coverage Area</h4>
                <div style="display: flex; align-items: center; margin-bottom: 3px;">
                    <div style="width: 15px; height: 15px; background: #4ECDC4; opacity: 0.3; margin-right: 8px;"></div>
                    <span style="font-size: 12px;">Malaysia, Singapore & Brunei</span>
                </div>
                <div style="display: flex; align-items: center; margin-bottom: 3px;">
                    <div style="width: 15px; height: 15px; background: #007bff; opacity: 0.3; border-radius: 50%; margin-right: 8px;"></div>
                    <span style="font-size: 12px;">Major cities</span>
                </div>
                <p style="font-size: 11px; margin: 5px 0 0 0; color: #666;">
                    Click anywhere in the highlighted region to add locations
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