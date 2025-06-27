let userLocation;
let map;
let markers = [];
let filteredPantries = [];
const foodPantries = [];
const MAX_DISTANCE_MILES = 10;

// Initialize filter states
let currentFilters = {
    status: 'all',
    distance: 10,
    sort: 'distance'
};

// Make these available globally
window.currentFilters = currentFilters;
window.applyFilters = applyFilters;

async function initMap() {
    const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");
    const { Autocomplete } = await google.maps.importLibrary("places");
    const defaultMapCenter = { lat: 44.0521, lng: -123.0868 };
    
    map = new google.maps.Map(document.getElementById("map"), {
        zoom: 10,
        center: defaultMapCenter,
        mapId: '3dbf8b9e408b987c',
        styles: [
            {
                featureType: "poi",
                elementType: "labels",
                stylers: [{ visibility: "off" }]
            }
        ]
    });

    const placesService = new google.maps.places.PlacesService(map);

    setupAutocomplete(Autocomplete, placesService);
    setupGeolocation(PinElement);
    
    // Set up event listeners with a small delay to ensure DOM is ready
    setTimeout(setupEventListeners, 100);
    
    loadPantryData(AdvancedMarkerElement, PinElement);
}

function setupEventListeners() {
    console.log('Setting up event listeners...');
    
    // Find near me button
    const findNearMeBtn = document.getElementById("find-near-me");
    if (findNearMeBtn) {
        findNearMeBtn.addEventListener("click", () => {
            getUserLocation(true, true);
        });
        console.log('Find near me button listener added');
    } else {
        console.error('Find near me button not found');
    }

    // Status filters
    const statusFilters = document.querySelectorAll('.status-filter');
    console.log('Found status filters:', statusFilters.length);
    
    statusFilters.forEach(filter => {
        filter.addEventListener('click', (e) => {
            console.log('Status filter clicked:', e.target.dataset.status);
            // Remove active class from all filters
            document.querySelectorAll('.status-filter').forEach(f => f.classList.remove('active'));
            // Add active class to clicked filter
            e.target.classList.add('active');
            
            currentFilters.status = e.target.dataset.status;
            applyFilters();
        });
    });

    // Distance slider
    const distanceSlider = document.getElementById('distance-slider');
    const distanceValue = document.getElementById('distance-value');
    
    if (distanceSlider && distanceValue) {
        console.log('Distance slider found');
        
        // Update slider background on input
        function updateSliderBackground() {
            const value = (distanceSlider.value - distanceSlider.min) / (distanceSlider.max - distanceSlider.min) * 100;
            distanceSlider.style.background = `linear-gradient(to right, #667eea 0%, #667eea ${value}%, #e9ecef ${value}%, #e9ecef 100%)`;
        }
        
        // Initialize slider background
        updateSliderBackground();
        
        distanceSlider.addEventListener('input', (e) => {
            console.log('Distance slider changed:', e.target.value);
            const distance = e.target.value;
            distanceValue.textContent = distance;
            currentFilters.distance = parseInt(distance);
            updateSliderBackground();
            applyFilters();
        });
    } else {
        console.error('Distance slider or distance value element not found');
    }

    // Sort dropdown
    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) {
        sortSelect.addEventListener('change', (e) => {
            console.log('Sort changed:', e.target.value);
            currentFilters.sort = e.target.value;
            applyFilters();
        });
        console.log('Sort dropdown listener added');
    } else {
        console.error('Sort dropdown not found');
    }
}

function applyFilters() {
    // Filter pantries based on current filters
    filteredPantries = foodPantries.filter(pantry => {
        // Status filter
        if (currentFilters.status !== 'all') {
            if (pantry.status !== currentFilters.status) {
                return false;
            }
        }

        // Distance filter (if user location is available)
        if (userLocation) {
            const distance = calculateDistance(
                userLocation.lat, 
                userLocation.lng, 
                pantry.latitude, 
                pantry.longitude
            );
            if (distance > currentFilters.distance) {
                return false;
            }
        }

        return true;
    });

    // Sort pantries
    sortPantries();
    
    // Update display
    updatePantryList();
    updateMapMarkers();
    updateResultsCount();
}

function sortPantries() {
    filteredPantries.sort((a, b) => {
        switch (currentFilters.sort) {
            case 'distance':
                if (!userLocation) return 0;
                const distA = calculateDistance(userLocation.lat, userLocation.lng, a.latitude, a.longitude);
                const distB = calculateDistance(userLocation.lat, userLocation.lng, b.latitude, b.longitude);
                return distA - distB;
            
            case 'updated':
                return new Date(b.lastUpdated || 0) - new Date(a.lastUpdated || 0);
            
            case 'name':
                return a.name.localeCompare(b.name);
            
            case 'status':
                const statusOrder = { 'full': 0, 'low': 1, 'empty': 2, 'unknown': 3 };
                return statusOrder[a.status || 'unknown'] - statusOrder[b.status || 'unknown'];
            
            default:
                return 0;
        }
    });
}

function updateResultsCount() {
    document.getElementById('pantry-count').textContent = filteredPantries.length;
}

function updatePantryList() {
    const pantryList = document.getElementById('pantry-list');
    
    if (filteredPantries.length === 0) {
        pantryList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-search"></i>
                <h4>No pantries found</h4>
                <p>Try adjusting your search criteria or expanding your search radius.</p>
            </div>
        `;
        return;
    }

    pantryList.innerHTML = filteredPantries.map(pantry => {
        const statusClass = getStatusClass(pantry.status);
        const statusText = getStatusText(pantry.status);
        const distance = userLocation ? 
            calculateDistance(userLocation.lat, userLocation.lng, pantry.latitude, pantry.longitude) : null;
        
        return `
            <li class="pantry-card" onclick="focusOnPantry(${pantry.latitude}, ${pantry.longitude}, '${pantry.name}')">
                <div class="pantry-header">
                    <h4 class="pantry-name">${pantry.name}</h4>
                    <span class="pantry-status ${statusClass}">${statusText}</span>
                </div>
                <div class="pantry-address">
                    <i class="fas fa-map-marker-alt"></i>
                    ${pantry.address}
                </div>
                <div class="pantry-meta">
                    ${distance ? `<span class="pantry-distance">${distance.toFixed(1)} miles away</span>` : ''}
                    <span class="pantry-updated">
                        <i class="fas fa-clock"></i>
                        ${pantry.lastUpdated ? formatTimeAgo(pantry.lastUpdated) : 'No recent reports'}
                    </span>
                </div>
            </li>
        `;
    }).join('');
}

function getStatusClass(status) {
    switch (status) {
        case 'full': return 'status-full';
        case 'low': return 'status-low';
        case 'empty': return 'status-empty';
        default: return 'status-unknown';
    }
}

function getStatusText(status) {
    switch (status) {
        case 'full': return 'Full';
        case 'low': return 'Low';
        case 'empty': return 'Empty';
        default: return 'Unknown';
    }
}

function formatTimeAgo(date) {
    const now = new Date();
    const reportDate = new Date(date);
    const diffInHours = Math.floor((now - reportDate) / (1000 * 60 * 60));
    
    if (diffInHours < 1) return 'Just now';
    if (diffInHours < 24) return `${diffInHours}h ago`;
    
    const diffInDays = Math.floor(diffInHours / 24);
    if (diffInDays < 7) return `${diffInDays}d ago`;
    
    const diffInWeeks = Math.floor(diffInDays / 7);
    if (diffInWeeks < 4) return `${diffInWeeks}w ago`;
    
    const diffInMonths = Math.floor(diffInDays / 30);
    return `${diffInMonths}mo ago`;
}

function focusOnPantry(lat, lng, name) {
    map.setCenter({ lat: parseFloat(lat), lng: parseFloat(lng) });
    map.setZoom(15);
    
    // Find and trigger click on the marker
    const marker = markers.find(m => 
        m.position.lat === parseFloat(lat) && m.position.lng === parseFloat(lng)
    );
    if (marker && marker.infoWindow) {
        marker.infoWindow.open(map, marker);
    }
}

function updateMapMarkers() {
    // Clear existing markers
    markers.forEach(marker => marker.setMap(null));
    markers = [];

    // Add markers for filtered pantries
    filteredPantries.forEach(pantry => {
        const statusColor = getMarkerColor(pantry.status);
        const pin = new google.maps.marker.PinElement({
            background: statusColor,
            borderColor: statusColor,
            glyph: getStatusIcon(pantry.status),
            scale: 1.2
        });

        const marker = new google.maps.marker.AdvancedMarkerElement({
            map: map,
            position: { lat: pantry.latitude, lng: pantry.longitude },
            title: pantry.name,
            content: pin.element,
        });

        // Create info window
        const infoWindow = new google.maps.InfoWindow({
            content: createInfoWindowContent(pantry)
        });

        marker.addListener('click', () => {
            // Close all other info windows
            markers.forEach(m => {
                if (m.infoWindow) m.infoWindow.close();
            });
            infoWindow.open(map, marker);
        });

        marker.infoWindow = infoWindow;
        markers.push(marker);
    });

    // Adjust map bounds to show all markers
    if (markers.length > 0) {
        const bounds = new google.maps.LatLngBounds();
        markers.forEach(marker => bounds.extend(marker.position));
        
        if (userLocation) {
            bounds.extend(userLocation);
        }
        
        map.fitBounds(bounds);
        
        // Don't zoom in too much for single markers
        if (markers.length === 1 && !userLocation) {
            map.setZoom(14);
        }
    }
}


function getMarkerColor(status) {
    switch (status) {
        case 'full': return '#28a745';
        case 'low': return '#ffc107';
        case 'empty': return '#dc3545';
        default: return '#6c757d';
    }
}

function getStatusIcon(status) {
    switch (status) {
        case 'full': return '✓';
        case 'low': return '!';
        case 'empty': return '✗';
        default: return '?';
    }
}

function createInfoWindowContent(pantry) {
    const statusClass = getStatusClass(pantry.status);
    const statusText = getStatusText(pantry.status);
    const distance = userLocation ? 
        calculateDistance(userLocation.lat, userLocation.lng, pantry.latitude, pantry.longitude) : null;

    return `
        <div style="max-width: 300px; font-family: 'Inter', sans-serif;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                <h4 style="margin: 0; color: #2c3e50; font-size: 1.1rem; font-weight: 700;">${pantry.name}</h4>
                <span class="pantry-status ${statusClass}" style="margin-left: 10px;">${statusText}</span>
            </div>
            
            <div style="color: #6c757d; margin-bottom: 10px; display: flex; align-items: center;">
                <i class="fas fa-map-marker-alt" style="margin-right: 8px; color: #667eea;"></i>
                ${pantry.address}
            </div>
            
            ${pantry.description ? `<p style="color: #495057; margin-bottom: 12px; font-size: 0.9rem;">${pantry.description}</p>` : ''}
            
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; color: #6c757d; margin-bottom: 15px;">
                ${distance ? `<span style="font-weight: 600;">${distance.toFixed(1)} miles away</span>` : ''}
                <span>${pantry.lastUpdated ? formatTimeAgo(pantry.lastUpdated) : 'No recent reports'}</span>
            </div>
            
            <div style="display: flex; gap: 10px;">
                <a href="/location/${pantry.id}" class="btn btn-primary btn-sm" style="flex: 1; text-decoration: none; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; padding: 8px 16px; border-radius: 8px; color: white; text-align: center; font-weight: 600;">
                    View Details
                </a>
                ${distance ? `
                    <a href="https://www.google.com/maps/dir/?api=1&destination=${pantry.latitude},${pantry.longitude}" 
                       target="_blank" class="btn btn-outline-primary btn-sm" 
                       style="padding: 8px 16px; border-radius: 8px; text-decoration: none; border: 2px solid #667eea; color: #667eea; font-weight: 600;">
                        Directions
                    </a>
                ` : ''}
            </div>
        </div>
    `;
}


function setupAutocomplete(Autocomplete, placesService) {
    const input = document.getElementById("pac-input");
    const autocomplete = new Autocomplete(input, {});

    autocomplete.addListener("place_changed", () => {
        const place = autocomplete.getPlace();
        if (place.geometry) {
            updateMapView(place.geometry);
        }
    });

    input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            const query = input.value;
            placesService.findPlaceFromQuery({
                query: query,
                fields: ['name', 'geometry'],
            }, (results, status) => {
                if (status === google.maps.places.PlacesServiceStatus.OK && results.length > 0) {
                    updateMapView(results[0].geometry);
                } else {
                    console.log("No results found for: '" + query + "'");
                }
            });
        }
    });
}

function updateMapView(geometry) {
    if (geometry.viewport) {
        map.fitBounds(geometry.viewport);
    } else {
        map.setCenter(geometry.location);
        map.setZoom(17);
    }
}

function setupGeolocation(PinElement) {
    getUserLocation(true, false);
}

/**
 * Retrieves the user's location using the browser's geolocation API.
 * 
 * @param {boolean} [centerMap=true] - Determines whether to center the map on the user's location.
 * @returns {Promise<void>} - A promise that resolves when the user's location is retrieved and processed.
 * @throws {Error} - If the browser doesn't support geolocation or if there is an error retrieving the user's location.
 */
async function getUserLocation(centerMap = true, popup = false) {
    if (navigator.geolocation) {
        try {
            const position = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject);
            });
            userLocation = {
                lat: position.coords.latitude,
                lng: position.coords.longitude,
            };
            if (centerMap) {
                map.setCenter(userLocation);
                map.setZoom(11);
            }
            addUserMarker(userLocation);
            
            // Update filters to use the new location for distance calculations
            if (foodPantries.length > 0) {
                applyFilters();
            }
        } catch (error) {
            console.error("Geolocation error:", error);
            // display popup if argument is set to true
            if (popup) {
                $('#locationModal').modal('show');
            }
        }
    } else {
        console.error("Error: Your browser doesn't support geolocation.");
    }
}

// document.getElementById('enableLocation').onclick = function() {
//     if (error.code === error.PERMISSION_DENIED) {
//         $('#locationModal').modal('show');
//     }
//     // $('#locationModal').modal('hide');
//     // Optionally, you can add instructions or redirect to a help page
// };

function addUserMarker(location) {
    const icon = document.createElement("div");
    icon.innerHTML = '<i class="fa fa-user fa-lg"></i>';
    const faPin = new google.maps.marker.PinElement({
        glyph: icon,
        background: "#4285F4",
        borderColor: "#4285F4",
    });

    new google.maps.marker.AdvancedMarkerElement({
        map: map,
        position: location,
        title: "Your Location",
        content: faPin.element,
    });

    new google.maps.Circle({
        strokeColor: '#0000FF',
        strokeOpacity: 0.2,
        strokeWeight: 2,
        fillColor: '#0000FF',
        fillOpacity: 0.1,
        map,
        center: location,
        radius: 100, // Assuming a fixed accuracy radius for simplicity
    });
}

function loadPantryData(AdvancedMarkerElement, PinElement) {
    foodPantries.length = 0; // Clear previous pantries
    fetch('/get_pantry_data')
        .then(response => response.json())
        .then(pantries => {
            pantries.forEach(pantry => {
                foodPantries.push(pantry);
            });
            
            // Initialize filtered pantries with all pantries
            filteredPantries = [...foodPantries];
            
            // Apply initial filters and display
            applyFilters();
        })
        .catch(error => {
            console.error('Error loading pantry data:', error);
            // Show error message to user
            const pantryList = document.getElementById('pantry-list');
            pantryList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-exclamation-triangle"></i>
                    <h4>Error loading pantries</h4>
                    <p>Unable to load pantry data. Please try again later.</p>
                </div>
            `;
        });
}

function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 3959; // Radius of the earth in miles
    const dLat = deg2rad(lat2 - lat1);
    const dLon = deg2rad(lon2 - lon1);
    const a = 
        Math.sin(dLat/2) * Math.sin(dLat/2) +
        Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) * 
        Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    const d = R * c; // Distance in miles
    return d;
}

function deg2rad(deg) {
    return deg * (Math.PI/180);
}

// Initialize the map when both DOM and Google Maps API are ready
function initializeMapApplication() {
    if (typeof google !== 'undefined' && google.maps) {
        initMap();
    } else {
        console.log('Google Maps API not ready yet, waiting...');
        setTimeout(initializeMapApplication, 100);
    }
}

// Ensure DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeMapApplication);
} else {
    initializeMapApplication();
}

// Also make initMap available globally for the Google Maps callback
window.initMap = initMap;
