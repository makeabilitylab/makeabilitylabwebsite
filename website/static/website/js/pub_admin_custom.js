/**
 * Custom JavaScript for the Publication admin interface.
 * 
 * Provides real-time validation warnings for the forum_name field,
 * alerting users when the field appears to contain a year (which
 * should typically be omitted from forum names).
 */
console.log('pub_admin_custom.js has been loaded');

// Wait for the DOM to fully load before executing the script
document.addEventListener('DOMContentLoaded', function () {
  console.log('DOMContentLoaded called');

  // Get the input field by its ID
  const forumNameField = document.getElementById('id_forum_name');

  // Early exit if the field doesn't exist (e.g., on the list view page)
  // This prevents errors when the script runs on pages without the form
  if (!forumNameField) {
    console.log('Forum name field not found - likely not on add/change form');
    return;
  }

  console.log('Forum name field found:', forumNameField);

  // Add an event listener to the input field to detect changes
  forumNameField.addEventListener('input', function () {
    console.log("addEventListener('input') called");

    // Check if a warning message already exists
    const existingWarning = document.getElementById('year-warning');

    console.log("warning message exists", existingWarning);

    // Test if the input value ends with a four-digit year
    const fieldEndsWithFourDigits = /\d{4}$/.test(forumNameField.value);

    console.log(`myField=${forumNameField.value} and fieldEndsWithFourDigits=${fieldEndsWithFourDigits}`);

    if (fieldEndsWithFourDigits) {
      // If no warning message exists, create one
      if (!existingWarning) {
        const warningMessage = document.createElement('div');
        warningMessage.id = 'year-warning';
        warningMessage.style.color = '#b30000';
        warningMessage.textContent = 'Warning: your forum name appears to end with a year! We just need the short forum name.';
        warningMessage.style.marginTop = '1px';
        warningMessage.style.marginBottom = '2px';

        // Insert the warning message before the input field
        // myField.parentNode.insertBefore(warningMessage, myField);

        // Append the warning message to the parent of the input field
        forumNameField.parentNode.appendChild(warningMessage);
      }
    } else {
      // If the input value does not end with a year, remove the warning message if it exists
      if (existingWarning) {
        existingWarning.remove();
      }
    }
  });
});