document.addEventListener('DOMContentLoaded', () => {
  const authTokenTextarea = document.getElementById('authToken');
  const saveTokenButton = document.getElementById('saveToken');
  const statusP = document.getElementById('status');

  // Load saved token when options page opens
  chrome.storage.sync.get(['authToken'], (result) => {
    if (result.authToken) {
      authTokenTextarea.value = result.authToken;
      statusP.textContent = 'Token loaded.';
    }
  });

  // Save token when button is clicked
  saveTokenButton.addEventListener('click', () => {
    const token = authTokenTextarea.value.trim();
    if (token) {
      // Basic JWT format validation: check for three parts separated by dots
      if (token.split('.').length === 3) {
        chrome.storage.sync.set({ authToken: token }, () => {
          statusP.textContent = 'Token saved successfully!';
        });
      } else {
        statusP.textContent = 'Invalid token format. Please paste a valid JWT.';
      }
    } else {
      statusP.textContent = 'Please enter a token.';
    }
  });
});
