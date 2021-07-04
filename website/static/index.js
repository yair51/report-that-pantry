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

var JSfacebookLogo = $('.facebookLogo');
var JSinstaLogo = $('.instaLogo');

JSfacebookLogo.on("click", goToWebsiteFacebook);

function goToWebsiteFacebook() {
  event.preventDefault();
  window.location.href = "https://www.facebook.com/reportthatpantry";
}

JSinstaLogo.on("click", goToWebsiteInsta);

function goToWebsiteInsta() {
  event.preventDefault();
  window.location.href = "https://www.instagram.com";
}