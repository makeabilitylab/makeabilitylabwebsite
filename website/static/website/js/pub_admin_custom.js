console.log('pub_admin_custom.js has been loaded');

// Wait for the DOM to fully load before executing the script
document.addEventListener('DOMContentLoaded', function () {
  console.log('DOMContentLoaded called');

  // Get the input field by its ID
  const myField = document.getElementById('id_forum_name');

  console.log('myField' + myField);

  // Add an event listener to the input field to detect changes
  myField.addEventListener('input', function () {
    console.log("addEventListener('input') called");

    // Check if a warning message already exists
    const warning = document.getElementById('year-warning');

    console.log("warning message exists", warning);

    // Test if the input value ends with a four-digit year
    const fieldEndsWithFourDigits = /\d{4}$/.test(myField.value);

    console.log(`myField=${myField.value} and fieldEndsWithFourDigits=${fieldEndsWithFourDigits}`);
  
    if (fieldEndsWithFourDigits) {
        // If no warning message exists, create one
        if (!warning) {
            const warningMessage = document.createElement('div');
            warningMessage.id = 'year-warning';
            warningMessage.style.color = '#b30000';
            warningMessage.textContent = 'Warning: your forum name appears to end with a year! We just need the short forum name.';
            warningMessage.style.marginTop = '1px';
            warningMessage.style.marginBottom = '2px';
            
            // Insert the warning message before the input field
            myField.parentNode.insertBefore(warningMessage, myField);

            // Append the warning message to the parent of the input field
            // myField.parentNode.appendChild(warningMessage);
        }
    } else {
        // If the input value does not end with a year, remove the warning message if it exists
        if (warning) {
            warning.remove();
        }
    }
  });
});