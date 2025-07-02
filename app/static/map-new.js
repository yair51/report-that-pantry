// Global variables
let userLocation;
let map;
let markers = [];
let filteredPantries = [];
const foodPantries = [];
const MAX_DISTANCE_MILES = 10;

// Initialize filter states
let currentFilters = {
    distance: 10,
    sort: 'distance'
};

// Make these available globally
window.currentFilters = currentFilters;
window.applyFilters = applyFilters;
window.getUserLocation = getUserLocation;
window.map = null;
window.updateMapView = updateMapView;
window.placesService = null;

function initMap() {
    const defaultMapCenter = { lat: 39.8283, lng: -98.5795 }; // Center of USA
    
    map = new google.maps.Map(document.getElementById("map"), {
        zoom: 4, // Zoom out to show more of the country
        center: defaultMapCenter,
        mapId: '3dbf8b9e408b987c',
        styles: [
            {
                featureType: "poi",
                elementType: "labels",
                stylers: [{ visibility: "off" }]
            },
            {
                featureType: "transit",
                elementType: "labels",
                stylers: [{ visibility: "off" }]
            }
        ],
        // Mobile-optimized settings
        gestureHandling: 'greedy',
        zoomControl: true,
        mapTypeControl: false,
        scaleControl: false,
        streetViewControl: false,
        rotateControl: false,
        fullscreenControl: false
    });
    
    // Make map available globally
    window.map = map;

    const placesService = new google.maps.places.PlacesService(map);
    window.placesService = placesService;

    setupAutocomplete(placesService);
    setupGeolocation();
    setupEventListeners();
    loadPantryData();
}

function setupEventListeners() {
    // Location button
    const locationBtn = document.getElementById("location-btn");
    if (locationBtn) {
        locationBtn.addEventListener("click", () => {
            getUserLocation(true, true);
        });
    }

    // Search input
    const searchInput = document.getElementById("search-input");
    if (searchInput) {
        searchInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                const query = searchInput.value;
                if (placesService) {
                    placesService.findPlaceFromQuery({
                        query: query,
                        fields: ['name', 'geometry'],
                    }, (results, status) => {
                        if (status === google.maps.places.PlacesServiceStatus.OK && results.length > 0) {
                            updateMapView(results[0].geometry);
                        }
                    });
                }
            }
        });
    }

    // Drawer toggle
    const drawerHeader = document.getElementById("drawer-header");
    const drawerToggle = document.getElementById("drawer-toggle");
    const pantryDrawer = document.getElementById("pantry-drawer");
    
    if (drawerHeader && drawerToggle && pantryDrawer) {
        const toggleDrawer = () => {
            pantryDrawer.classList.toggle("show");
            drawerToggle.classList.toggle("rotated");
        };
        
        drawerHeader.addEventListener("click", toggleDrawer);
        drawerToggle.addEventListener("click", (e) => {
            e.stopPropagation();
            toggleDrawer();
        });
    }
}

function setupAutocomplete(placesService) {
    const input = document.getElementById("search-input");
    
    if (input) {
        const autocomplete = new google.maps.places.Autocomplete(input, {
            types: ['geocode', 'establishment']
        });

        autocomplete.addListener("place_changed", () => {
            const place = autocomplete.getPlace();
            if (place.geometry) {
                updateMapView(place.geometry);
            }
        });
    }
}

function updateMapView(geometry) {
    if (geometry.viewport) {
        map.fitBounds(geometry.viewport);
    } else {
        map.setCenter(geometry.location);
        map.setZoom(15);
    }
}

function setupGeolocation() {
    getUserLocation(true, false);
}

async function getUserLocation(centerMap = true, popup = false) {
    if (navigator.geolocation) {
        try {
            const position = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 60000
                });
            });
            
            userLocation = {
                lat: position.coords.latitude,
                lng: position.coords.longitude,
            };
            
            if (centerMap) {
                // Center map on user location
                map.setCenter(userLocation);
                
                // Keep all pantries visible but update the distance badge
                const distanceBadge = document.querySelector('.distance-badge');
                if (distanceBadge) {
                    distanceBadge.innerHTML = '<i class="fas fa-circle"></i> Near You';
                }
                
                // Zoom to show the 10-mile radius area
                map.setZoom(13); // Zoom in more to show the 10-mile radius
            }
            
            addUserMarker(userLocation);
            
        } catch (error) {
            console.error("Geolocation error:", error);
            if (popup) {
                $('#locationModal').modal('show');
            }
        }
    } else {
        console.error("Error: Your browser doesn't support geolocation.");
    }
}

function addUserMarker(location) {
    // Create a custom user marker
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
        radius: 100,
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

function applyFilters() {
    // Show all pantries - no distance filtering
    filteredPantries = [...foodPantries];

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
                if (!userLocation) {
                    // If no user location, sort by name instead
                    return a.name.localeCompare(b.name);
                }
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
    const pantryCount = document.getElementById('pantry-count');
    const drawerCount = document.getElementById('drawer-count');
    
    if (pantryCount) {
        pantryCount.textContent = filteredPantries.length;
    }
    
    if (drawerCount) {
        drawerCount.textContent = filteredPantries.length;
    }
}

function updatePantryList() {
    const pantryList = document.getElementById('pantry-list');
    
    if (!pantryList) return;
    
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
        const distance = userLocation ? calculateDistance(userLocation.lat, userLocation.lng, pantry.latitude, pantry.longitude) : null;
        const distanceText = distance ? `${distance.toFixed(1)} miles` : '';
        
        return `
            <li class="pantry-card ${pantry.status || 'unknown'}">
                <div class="pantry-header">
                    <h3 class="pantry-name">${pantry.name}</h3>
                    <span class="pantry-status ${statusClass}">${statusText}</span>
                </div>
                <div class="pantry-address">
                    <i class="fas fa-map-marker-alt"></i>
                    ${pantry.address || 'Address not available'}
                </div>
                <div class="pantry-meta">
                    ${distanceText ? `<span class="pantry-distance">
                        <i class="fas fa-location-arrow"></i>
                        ${distanceText}
                    </span>` : ''}
                    <span class="pantry-updated">
                        <i class="fas fa-clock"></i>
                        ${formatTimeAgo(pantry.lastUpdated)}
                    </span>
                </div>
                <div class="pantry-actions" style="margin-top: 12px; display: flex; gap: 8px;">
                    <button onclick="focusOnPantry(${pantry.latitude}, ${pantry.longitude}, '${pantry.name}')" style="
                        background: rgba(102, 126, 234, 0.1);
                        color: #667eea;
                        border: 1px solid #667eea;
                        padding: 8px 16px;
                        border-radius: 12px;
                        font-size: 12px;
                        font-weight: 600;
                        cursor: pointer;
                        transition: all 0.3s ease;
                        flex: 1;
                    " onmouseover="this.style.background='rgba(102, 126, 234, 0.2)'" 
                       onmouseout="this.style.background='rgba(102, 126, 234, 0.1)'">
                        <i class="fas fa-map-marker-alt" style="margin-right: 6px;"></i>
                        Show on Map
                    </button>
                    <a href="/location/${pantry.id}" style="
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        text-decoration: none;
                        padding: 8px 16px;
                        border-radius: 12px;
                        font-size: 12px;
                        font-weight: 600;
                        display: inline-block;
                        transition: all 0.3s ease;
                        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
                        flex: 1;
                        text-align: center;
                    " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(102, 126, 234, 0.4)'" 
                       onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(102, 126, 234, 0.3)'">
                        <i class="fas fa-info-circle" style="margin-right: 6px;"></i>
                        Details
                    </a>
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
    map.setZoom(16);
    
    // Find and open the info window for this pantry
    const marker = markers.find(m => 
        m.position.lat === position.lat && m.position.lng === position.lng
    );
    if (marker && marker.infoWindow) {
        marker.infoWindow.open(map, marker);
    }
    
    // Close the drawer on mobile
    const pantryDrawer = document.getElementById('pantry-drawer');
    if (pantryDrawer && window.innerWidth <= 768) {
        pantryDrawer.classList.remove('show');
        const drawerToggle = document.getElementById('drawer-toggle');
        if (drawerToggle) {
            drawerToggle.classList.remove('rotated');
        }
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
    const bounds = new google.maps.LatLngBounds();
    
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
        
        // Extend bounds to include this marker
        bounds.extend(position);
    });
    
    // Fit map to show all markers if we have any
    if (markers.length > 0) {
        map.fitBounds(bounds);
        
        // Add some padding to the bounds
        const listener = google.maps.event.addListenerOnce(map, 'bounds_changed', () => {
            map.setZoom(Math.min(map.getZoom(), 10)); // Don't zoom in too much
        });
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

function createInfoWindowContent(pantry) {
    const statusClass = getStatusClass(pantry.status);
    const statusText = getStatusText(pantry.status);
    const distance = userLocation ? calculateDistance(userLocation.lat, userLocation.lng, pantry.latitude, pantry.longitude) : null;
    const distanceText = distance ? `${distance.toFixed(1)} miles away` : '';
    
    return `
        <div style="padding: 15px; max-width: 280px;">
            <h4 style="margin: 0 0 10px 0; color: #2c3e50; font-size: 16px;">${pantry.name}</h4>
            <p style="margin: 8px 0; color: #6c757d; font-size: 14px;">
                <i class="fas fa-map-marker-alt" style="color: #667eea;"></i>
                ${pantry.address || 'Address not available'}
            </p>
            <p style="margin: 8px 0; color: #6c757d; font-size: 14px;">
                <i class="fas fa-clock" style="color: #667eea;"></i>
                Updated ${formatTimeAgo(pantry.lastUpdated)}
            </p>
            ${distanceText ? `<p style="margin: 8px 0; color: #495057; font-size: 14px; font-weight: 600;">
                <i class="fas fa-location-arrow" style="color: #667eea;"></i>
                ${distanceText}
            </p>` : ''}
            <div style="margin-top: 12px; display: flex; gap: 8px; align-items: center;">
                <span class="pantry-status ${statusClass}" style="padding: 6px 12px; border-radius: 15px; font-size: 12px; font-weight: 600;">
                    ${statusText}
                </span>
                <a href="/location/${pantry.id}" style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    text-decoration: none;
                    padding: 8px 16px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: 600;
                    display: inline-block;
                    transition: all 0.3s ease;
                    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
                " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(102, 126, 234, 0.4)'" 
                   onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(102, 126, 234, 0.3)'">
                    <i class="fas fa-info-circle" style="margin-right: 6px;"></i>
                    Details
                </a>
            </div>
        </div>
    `;
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
            const pantryList = document.getElementById('pantry-list');
            if (pantryList) {
                pantryList.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-exclamation-triangle"></i>
                        <h4>Error loading pantries</h4>
                        <p>Unable to load pantry data. Please try again later.</p>
                    </div>
                `;
            }
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

// Make initMap available globally for the Google Maps callback
window.initMap = initMap; 