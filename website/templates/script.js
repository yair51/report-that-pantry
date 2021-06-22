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