function deleteLocation(locationId) {
  fetch("/delete-location", {
    method: "POST",
    body: JSON.stringify({ locationId: locationId }),
  }).then((_res) => {
    window.location.href = "/";
  });
}
