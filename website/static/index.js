function deleteLocation(locationId) {
  if (confirm("Are you sure you want to delete this address?"))
  {
    fetch("/delete-location", {
      method: "POST",
      body: JSON.stringify({ locationId: locationId }),
    }).then((_res) => {
      window.location.href = "/";
    });
  }
}

function redirectHome() {
  location.href = "/";
}