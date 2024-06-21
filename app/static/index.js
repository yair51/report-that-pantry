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

$(document).ready(function() {

  // Update time values in the table cells on page load
  $('[id^=time]').each(function() {
      const timestamp = parseInt($(this).text()); // Get and parse the timestamp
      $(this).text(timeFormatter(timestamp));  // Apply the timeFormatter
  });
});

// Formatter functions
function timeFormatter(value, row, index) {
  if (!value) {
      return 'Never'; // Handle cases where there's no report yet
  }

  const now = new Date();
  const updatedAt = new Date(value * 1000); // Convert timestamp to milliseconds (assuming value is in seconds)

  // Get time difference in milliseconds
  const timeDiff = Math.abs(now - updatedAt);

  const secondsDiff = Math.round(timeDiff / 1000);
  const minutesAgo = Math.round(secondsDiff / 60);
  const hoursAgo = Math.round(minutesAgo / 60);

  if (hoursAgo < 1) {
      return minutesAgo + " minute" + (minutesAgo > 1 ? "s" : "") + " ago";
  } else if (hoursAgo < 24) {
      return hoursAgo + " hour" + (hoursAgo > 1 ? "s" : "") + " ago";
  } else {
      const options = { year: 'numeric', month: 'long', day: 'numeric', hour: 'numeric', minute: 'numeric' };
      return updatedAt.toLocaleDateString(undefined, options); 
  }
}


// Wait for DOM to load
document.addEventListener("DOMContentLoaded", function () {
  // Toggle password inputs
  const togglePasswordButtons = document.querySelectorAll("[id^=toggle]");

  if (togglePasswordButtons) {
    togglePasswordButtons.forEach(button => {
        const passwordInputId = button.id.replace("toggle", ""); // Get the corresponding input ID
        const passwordInput = document.getElementById(passwordInputId);

        button.addEventListener("click", function() {
            // toggle the type attribute
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);

            // toggle the eye / eye slash icon
            this.querySelector("i").classList.toggle("fa-eye");
            this.querySelector("i").classList.toggle("fa-eye-slash");
        });
    });
  }
});

// const togglePasswordButton = document.getElementById("togglePassword");
  const passwordInput = document.getElementById("Password");
  const passwordGroup = document.getElementById("passwordGroup");

  if (passwordInput) {
    passwordInput.addEventListener("input", function () {
      if (passwordInput.checkValidity() === false) {
        // Customize your error message here
        passwordGroup.classList.add('is-invalid');
        passwordInput.classList.add('is-invalid');
        passwordGroup.classList.remove('is-valid');
        passwordInput.classList.remove('is-valid');
      } else {
        passwordGroup.classList.remove('is-invalid');
        passwordInput.classList.remove('is-invalid');
        passwordGroup.classList.add('is-valid');
        passwordInput.classList.add('is-valid');
      }
    });
  }