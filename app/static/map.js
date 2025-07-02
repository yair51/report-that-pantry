let userLocation;
let map;
let markers = [];
let filteredPantries = [];
const foodPantries = [];
const MAX_DISTANCE_MILES = 10;

// Initialize filter states - simplified without status filters
let currentFilters = {
    distance: 10,
    sort: 'distance'
};

// Make these available globally
window.currentFilters = currentFilters;
window.applyFilters = applyFilters;
window.getUserLocation = getUserLocation;
window.map = null; // Will be set in initMap
window.updateMapView = updateMapView; // Will be set below

function initMap() {
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
    
    // Make map available globally
    window.map = map;

    const placesService = new google.maps.places.PlacesService(map);
    
    // Make placesService available globally
    window.placesService = placesService;

    setupAutocomplete(placesService);
    setupGeolocation();
    
    // Set up event listeners with a small delay to ensure DOM is ready
    setTimeout(setupEventListeners, 100);
    
    loadPantryData();
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
    // Filter pantries based on current filters - simplified without status filtering
    filteredPantries = foodPantries.filter(pantry => {
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
    const desktopCount = document.getElementById('pantry-count');
    const mobileCount = document.getElementById('mobile-pantry-count');
    
    if (desktopCount) {
        desktopCount.textContent = filteredPantries.length;
    }
    
    if (mobileCount) {
        mobileCount.textContent = filteredPantries.length;
    }
}

function updatePantryList() {
    const pantryList = document.getElementById('pantry-list');
    const mobilePantryList = document.getElementById('mobile-pantry-list-content');
    
    const pantryHTML = filteredPantries.length === 0 ? `
        <div class="empty-state">
            <i class="fas fa-search"></i>
            <h4>No pantries found</h4>
            <p>Try adjusting your search criteria or expanding your search radius.</p>
        </div>
    ` : filteredPantries.map(pantry => {
        const statusClass = getStatusClass(pantry.status);
        const statusText = getStatusText(pantry.status);
        const distance = userLocation ? calculateDistance(userLocation.lat, userLocation.lng, pantry.latitude, pantry.longitude) : null;
        const distanceText = distance ? `${distance.toFixed(1)} miles` : '';
        
        return `
            <li class="pantry-card" onclick="focusOnPantry(${pantry.latitude}, ${pantry.longitude}, '${pantry.name}')">
                <div class="pantry-header">
                    <h3 class="pantry-name">${pantry.name}</h3>
                    <span class="pantry-status ${statusClass}">${statusText}</span>
                </div>
                <div class="pantry-address">
                    <i class="fas fa-map-marker-alt"></i>
                    ${pantry.address || 'Address not available'}
                </div>
                <div class="pantry-meta">
                    <span class="pantry-distance">${distanceText}</span>
                    <span class="pantry-updated">
                        <i class="fas fa-clock"></i>
                        ${formatTimeAgo(pantry.lastUpdated)}
                    </span>
                </div>
            </li>
        `;
    }).join('');
    
    // Update desktop list
    if (pantryList) {
        pantryList.innerHTML = pantryHTML;
    }
    
    // Update mobile list
    if (mobilePantryList) {
        mobilePantryList.innerHTML = pantryHTML;
    }
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
    if (!date) return 'Unknown';
    
    const now = new Date();
    const updated = new Date(date);
    const diffMs = now - updated;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
    return `${Math.floor(diffDays / 30)} months ago`;
}

function focusOnPantry(lat, lng, name) {
    const position = { lat: parseFloat(lat), lng: parseFloat(lng) };
    map.setCenter(position);
    map.setZoom(15);
    
    // Find and open the info window for this pantry
    const marker = markers.find(m => 
        m.position.lat === position.lat && m.position.lng === position.lng
    );
    if (marker && marker.infoWindow) {
        marker.infoWindow.open(map, marker);
    }
}

function updateMapMarkers() {
    // Clear existing markers
    markers.forEach(marker => {
        if (marker.infoWindow) {
            marker.infoWindow.close();
        }
        marker.setMap(null);
    });
    markers = [];

    // Add new markers for filtered pantries
    filteredPantries.forEach(pantry => {
        const position = { lat: pantry.latitude, lng: pantry.longitude };
        const markerColor = getMarkerColor(pantry.status);
        
        const marker = new google.maps.Marker({
            position: position,
            map: map,
            title: pantry.name,
            icon: {
                url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
                    <svg width="40" height="40" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="20" cy="20" r="18" fill="${markerColor}" stroke="white" stroke-width="2"/>
                        <text x="20" y="25" text-anchor="middle" fill="white" font-family="Arial, sans-serif" font-size="16" font-weight="bold">🏪</text>
                    </svg>
                `)}`,
                scaledSize: new google.maps.Size(40, 40),
                anchor: new google.maps.Point(20, 20)
            }
        });

        const infoWindow = new google.maps.InfoWindow({
            content: createInfoWindowContent(pantry)
        });

        marker.addListener('click', () => {
            infoWindow.open(map, marker);
        });

        marker.infoWindow = infoWindow;
        markers.push(marker);
    });
}

function getMarkerColor(status) {
    switch (status) {
        case 'full': return '#28a745';
        case 'low': return '#ffc107';
        case 'empty': return '#dc3545';
        default: return '#6c757d';
    }
}



function createInfoWindowContent(pantry) {
    const statusClass = getStatusClass(pantry.status);
    const statusText = getStatusText(pantry.status);
    const distance = userLocation ? calculateDistance(userLocation.lat, userLocation.lng, pantry.latitude, pantry.longitude) : null;
    const distanceText = distance ? `${distance.toFixed(1)} miles away` : '';
    
    return `
        <div style="padding: 10px; max-width: 250px;">
            <h4 style="margin: 0 0 10px 0; color: #2c3e50;">${pantry.name}</h4>
            <p style="margin: 5px 0; color: #6c757d; font-size: 14px;">
                <i class="fas fa-map-marker-alt" style="color: #667eea;"></i>
                ${pantry.address || 'Address not available'}
            </p>
            <p style="margin: 5px 0; color: #6c757d; font-size: 14px;">
                <i class="fas fa-clock" style="color: #667eea;"></i>
                Updated ${formatTimeAgo(pantry.lastUpdated)}
            </p>
            ${distanceText ? `<p style="margin: 5px 0; color: #495057; font-size: 14px; font-weight: 600;">
                <i class="fas fa-location-arrow" style="color: #667eea;"></i>
                ${distanceText}
            </p>` : ''}
            <div style="margin-top: 10px;">
                <span class="pantry-status ${statusClass}" style="padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: 600;">
                    ${statusText}
                </span>
            </div>
        </div>
    `;
}

function setupAutocomplete(placesService) {
    const input = document.getElementById("pac-input");
    
    // Create autocomplete using the traditional approach
    const autocomplete = new google.maps.places.Autocomplete(input, {});

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

function setupGeolocation() {
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
    // Create a custom user marker with pulsing animation
    const userMarker = new google.maps.Marker({
        map: map,
        position: location,
        title: "Your Location",
        icon: {
            url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`
                <svg width="50" height="50" viewBox="0 0 50 50" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                        <filter id="glow">
                            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                            <feMerge> 
                                <feMergeNode in="coloredBlur"/>
                                <feMergeNode in="SourceGraphic"/>
                            </feMerge>
                        </filter>
                    </defs>
                    <circle cx="25" cy="25" r="22" fill="#4285F4" stroke="white" stroke-width="3" filter="url(#glow)"/>
                    <text x="25" y="32" text-anchor="middle" fill="white" font-family="Arial, sans-serif" font-size="20" font-weight="bold">👤</text>
                </svg>
            `)}`,
            scaledSize: new google.maps.Size(50, 50),
            anchor: new google.maps.Point(25, 25)
        }
    });

    // Add a pulsing circle around the user marker
    const pulseCircle = new google.maps.Circle({
        strokeColor: '#4285F4',
        strokeOpacity: 0.8,
        strokeWeight: 3,
        fillColor: '#4285F4',
        fillOpacity: 0.2,
        map,
        center: location,
        radius: 100, // Small radius for pulsing effect
    });

    // Add a circle to show the 10-mile radius
    new google.maps.Circle({
        strokeColor: '#4285F4',
        strokeOpacity: 0.3,
        strokeWeight: 2,
        fillColor: '#4285F4',
        fillOpacity: 0.1,
        map,
        center: location,
        radius: 16093.4, // 10 miles in meters
    });

    // Create pulsing animation for the user marker
    let pulseRadius = 100;
    let growing = true;
    
    setInterval(() => {
        if (growing) {
            pulseRadius += 20;
            if (pulseRadius >= 200) growing = false;
        } else {
            pulseRadius -= 20;
            if (pulseRadius <= 100) growing = true;
        }
        
        pulseCircle.setRadius(pulseRadius);
        pulseCircle.setOptions({
            fillOpacity: Math.max(0.1, 0.3 - (pulseRadius - 100) / 1000)
        });
    }, 100);
}

function loadPantryData() {
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
