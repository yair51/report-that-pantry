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

$(document).ready(function() {

  // Update time values in the table cells on page load
  $('[id^=time]').each(function() {
      const timestamp = parseInt($(this).text()); // Get and parse the timestamp
      $(this).text(timeFormatter(timestamp));  // Apply the timeFormatter
  });
});

// Formatter functions
function timeFormatter(value, row, index) {
  const now = new Date();
  const updatedAt = new Date(value * 1000); // Convert timestamp to milliseconds

  // Get user's timezone offset (in minutes)
  const timezoneOffset = new Date().getTimezoneOffset();

  // Adjust updatedAt to user's timezone
  updatedAt.setMinutes(updatedAt.getMinutes() - timezoneOffset);

  const secondsAgo = Math.round((now - updatedAt) / 1000);
  const minutesAgo = Math.round(secondsAgo / 60);
  const hoursAgo = Math.round(minutesAgo / 60);

  if (hoursAgo < 1) {
      return minutesAgo + " minute" + (minutesAgo > 1 ? "s" : "") + " ago";
  } else if (hoursAgo < 24) {
      return hoursAgo + " hour" + (hoursAgo > 1 ? "s" : "") + " ago";
  } else {
      return updatedAt.toLocaleDateString(); // Fallback to date if older
  }
}
// var JSfacebookLogo = $('.facebookLogo');
// var JSinstaLogo = $('.instaLogo');

// JSfacebookLogo.on("click", goToWebsiteFacebook);

// function goToWebsiteFacebook() {
//   event.preventDefault();
//   window.location.href = "https://www.facebook.com/reportthatpantry";
// }

// JSinstaLogo.on("click", goToWebsiteInsta);

// function goToWebsiteInsta() {
//   event.preventDefault();
//   window.location.href = "https://www.instagram.com";
// }