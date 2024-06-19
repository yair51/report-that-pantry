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


// const togglePasswordButton = document.getElementById("togglePassword");
// const passwordInput = document.getElementById("password");

// togglePasswordButton.addEventListener("click", function () {
//     // toggle the type attribute
//     const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
//     passwordInput.setAttribute('type', type);
//     // toggle the eye / eye slash icon
//     this.querySelector("i").classList.toggle("fa-eye");
//     this.querySelector("i").classList.toggle("fa-eye-slash");
// });

// Wait for DOM to load
document.addEventListener("DOMContentLoaded", function () {
  // Toggle password inputs
  const togglePasswordButtons = document.querySelectorAll("[id^=toggle]");

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
});

// const togglePasswordButton = document.getElementById("togglePassword");
  const passwordInput = document.getElementById("Password");
  const passwordGroup = document.getElementById("passwordGroup");

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

//   document
//     .getElementById("newPassword")
//     .addEventListener("input", validatePassword);
//   document
//     .getElementById("confirmPassword")
//     .addEventListener("input", validatePassword)

// // Password validation
// function validatePassword() {
//   const password = document.getElementById("newPassword").value;
//   const confirmPassword = document.getElementById("confirmPassword").value;
//   const passwordError = document.getElementById("newPassword");

//   if (password.length < 7) {
//     passwordError.textContent = "Password must be at least 7 characters long!";
//     passwordError.style.display = "block";
//     document.getElementById("newPassword").classList.add('is-invalid');
//     document.getElementById("newPassword").classList.remove('is-valid');
//   } else {
//     passwordError.style.display = "none";
//     document.getElementById("newPassword").classList.remove('is-invalid');
//     document.getElementById("newPassword").classList.add('is-valid');
//   }
//   if(password != confirmPassword){
//     document.getElementById("confirmPassword").classList.add('is-invalid');
//     document.getElementById("confirmPassword").classList.remove('is-valid');
//   }
//   else{
//     document.getElementById("confirmPassword").classList.remove('is-invalid');
//     document.getElementById("confirmPassword").classList.add('is-valid');
//   }
// }




// document.addEventListener("DOMContentLoaded", function() { // Wait for the DOM to load
//   // Get all password toggle buttons
//   const togglePasswordButtons = document.querySelectorAll("[id^=togglePassword]");

//   togglePasswordButtons.forEach(button => {
//       const passwordInputId = button.id.replace("toggle", "");
//       const passwordInput = document.getElementById(passwordInputId);

//       button.addEventListener("click", function() {
//           // toggle the type attribute
//           const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
//           passwordInput.setAttribute('type', type);
//           // toggle the eye / eye slash icon
//           this.querySelector("i").classList.toggle("fa-eye");
//           this.querySelector("i").classList.toggle("fa-eye-slash");
//       });
//   });
// });

// const togglePasswordButton = document.getElementById("togglePassword");
// const passwordInput = document.getElementById("password");

// togglePasswordButton.addEventListener("click", function () {
//     // toggle the type attribute
//     const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
//     passwordInput.setAttribute('type', type);
//     // toggle the eye / eye slash icon
//     this.querySelector("i").classList.toggle("fa-eye");
//     this.querySelector("i").classList.toggle("fa-eye-slash");
// });