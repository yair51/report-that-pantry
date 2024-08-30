let userLocation;
let map;
const foodPantries = [];
const MAX_DISTANCE_MILES = 10;


async function initMap() {
    const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");
    const { Autocomplete } = await google.maps.importLibrary("places");
    const defaultMapCenter = { lat: 36.1627, lng: -86.7816 };
    
    map = new google.maps.Map(document.getElementById("map"), {
        zoom: 10,
        center: defaultMapCenter,
        mapId: '3dbf8b9e408b987c',
    });

    const placesService = new google.maps.places.PlacesService(map);

    setupAutocomplete(Autocomplete, placesService);
    setupGeolocation(PinElement);
    loadPantryData(AdvancedMarkerElement, PinElement);

    
    document.getElementById("find-near-me").addEventListener("click", () => {
        // setupGeolocation(PinElement);
        getUserLocation(true, true);
        // loadPantryData(AdvancedMarkerElement, PinElement);
        loadPantryData(AdvancedMarkerElement, PinElement);

    });
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
        } catch (error) {
            console.error("Geolocation error:", error);
            // display popup if argument is set to true
            if (popup) {
                $('#locationModal').modal('show');
            }
            // if (error.code === error.PERMISSION_DENIED) {
            //     $('#locationModal').modal('show');
            // }
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
                const marker = createPantryMarker(pantry, AdvancedMarkerElement, PinElement);
                const infoWindow = createInfoWindow(pantry);
                
                marker.addListener("click", () => {
                    infoWindow.open({
                        anchor: marker,
                        map,
                        shouldFocus: false,
                    });
                });

                const distance = getDistance(
                    userLocation || map.getCenter(),
                    { lat: pantry.latitude, lng: pantry.longitude }
                );
                const distanceMiles = distance * 0.000621371;

                foodPantries.push({ ...pantry, marker, distanceMiles });
            });
            // sort and display pantries
            sortAndDisplayPantries();
        });
}

function createPantryMarker(pantry, AdvancedMarkerElement, PinElement) {
    const icon = document.createElement("div");
    icon.innerHTML = '<i class="fa fa-apple-alt fa-lg"></i>';
    const pin = new PinElement({
        glyph: icon,
        glyphColor: 'black',
        background: pantry.marker_color,
        borderColor: pantry.marker_color,
    });

    return new AdvancedMarkerElement({
        map: map,
        position: { lat: pantry.latitude, lng: pantry.longitude },
        title: pantry.name,
        content: pin.element,
    });
}

// Create an info window for a pantry
function createInfoWindow(pantry) {
    return new google.maps.InfoWindow({
        content: `
            <h3>${pantry.name}</h3>
            <p>${pantry.address}</p>
            <div class="progress" style="height: 20px; position: relative;"> 
                <div class="progress-bar" role="progressbar" 
                     style="background-color: ${pantry.marker_color}; width: ${pantry.fullness}%;" 
                     aria-valuenow="${pantry.fullness}" aria-valuemin="0" aria-valuemax="100">
                    <span class="fullness-overlay">${pantry.fullness}%</span> 
                </div>
            </div>
            <p>Last Reported Status: ${pantry.fullness || 'Unknown'}% Full</p>
            <p>Last Updated: ${pantry.last_updated ? new Date(pantry.last_updated).toLocaleString() : 'N/A'}</p>
            <a href="/location/${pantry.id}">View Details & Report Status</a>
        `
    });
}

// Calculate distance between two points
function getDistance(point1, point2) {
    return google.maps.geometry.spherical.computeDistanceBetween(
        new google.maps.LatLng(point1.lat, point1.lng),
        new google.maps.LatLng(point2.lat, point2.lng)
    );
}

// Sort and display pantries within a certain distance
function sortAndDisplayPantries() {
    foodPantries.sort((a, b) => a.distanceMiles - b.distanceMiles);

    const listContainer = document.getElementById("pantry-list");
    listContainer.innerHTML = ''; // Clear previous list

     // Create and add the section header
     const header = document.createElement("h2");
     header.textContent = "Nearby Food Pantries";
     header.classList.add('section-header'); // Optional: Add a class for styling
     listContainer.appendChild(header);

    foodPantries.forEach((pantry) => {
        if (pantry.distanceMiles <= MAX_DISTANCE_MILES) {
            // Create list item with Bootstrap styling
            const listItem = document.createElement("li");
            listItem.classList.add('list-group-item', 'd-flex', 'justify-content-between', 'align-items-center');

            // Create the left side content (pantry name and distance)
            const leftContent = document.createElement('div');
            const pantryName = document.createElement('span');
            pantryName.classList.add('font-weight-bold');
            pantryName.textContent = pantry.name;
            leftContent.appendChild(pantryName);
            leftContent.appendChild(document.createTextNode(` - ${pantry.distanceMiles.toFixed(1)} miles`));

            // Create the right side content (progress bar)
            const rightContent = document.createElement('div');
            rightContent.classList.add('progress');
            rightContent.style.width = '100px';
            rightContent.style.height = '15px';

            const progressBar = document.createElement('div');
            progressBar.classList.add('progress-bar');
            progressBar.role = 'progressbar';
            progressBar.style.width = `${pantry.fullness || 0}%`; // Handle 'Unknown' fullness
            progressBar.style.backgroundColor = pantry.marker_color;
            progressBar.setAttribute('aria-valuenow', pantry.fullness || 0);
            progressBar.setAttribute('aria-valuemin', 0);
            progressBar.setAttribute('aria-valuemax', 100);

            rightContent.appendChild(progressBar);

            // Append both sides to the list item
            listItem.appendChild(leftContent);
            listItem.appendChild(rightContent);

            listContainer.appendChild(listItem);

            listItem.addEventListener("click", () => {
                map.panTo(pantry.marker.position);
                map.setZoom(15);
            });
        }
    });
}
