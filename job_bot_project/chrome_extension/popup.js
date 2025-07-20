document.addEventListener('DOMContentLoaded', () => {
  const fillFormButton = document.getElementById('fillForm');
  const optionsLink = document.getElementById('optionsLink');

  fillFormButton.addEventListener('click', () => {
    // 1. Get auth token from storage
    chrome.storage.local.get(['authToken'], (result) => {
      const token = result.authToken;
      if (!token) {
        alert('Please log in first via the options page.');
        chrome.runtime.openOptionsPage();
        return;
      }

      // 2. Fetch profile from the API
      fetch('http://127.0.0.1:8000/api/me/profile', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      .then(response => {
        if (!response.ok) {
          // If the token is invalid or expired, or another server error
          if (response.status === 401) {
             alert('Your session has expired. Please log in again.');
             chrome.runtime.openOptionsPage();
          }
          throw new Error('API request failed');
        }
        return response.json();
      })
      .then(profileData => {
        // 3. Cache the new data and fill the form
        chrome.storage.local.set({ 'userProfile': profileData }, () => {
          console.log('Profile fetched from API and cached.');
          injectAutoFill(profileData);
        });
      })
      .catch(error => {
        console.error('Error fetching profile from API:', error);
        // 4. If API fails, try to use cached data
        console.log('Attempting to use cached profile data...');
        chrome.storage.local.get(['userProfile'], (cacheResult) => {
          if (cacheResult.userProfile) {
            console.log('Using cached profile.');
            injectAutoFill(cacheResult.userProfile);
          } else {
            alert('Could not fetch your profile. Please check your internet connection and try logging in again.');
          }
        });
      });
    });
  });

  optionsLink.addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });
});

// This function will be injected into the active tab
function autoFillForm(profile) {
    if (!profile) {
      console.log('Job Bot: No profile data available to fill the form.');
      return;
    }

    // Helper function to safely set the value of an input field
    const safeSetValue = (selector, value) => {
      // Ensure value is not null or undefined
      if (value === null || typeof value === 'undefined') return;
      try {
        const element = document.querySelector(selector);
        if (element) {
          element.value = value;
        } else {
          console.log(`Job Bot: Could not find element with selector: ${selector}`);
        }
      } catch (e) {
        console.error(`Job Bot: Error with selector "${selector}":`, e);
      }
    };

    const locationParts = profile.location ? profile.location.split(', ') : ['', ''];
    const city = locationParts[0];
    const province = locationParts.length > 1 ? locationParts[1] : '';
    const fullName = profile.name || '';
    const nameParts = fullName.split(' ');
    const firstName = nameParts[0] || '';
    const lastName = nameParts.slice(1).join(' ') || '';


    safeSetValue('input[name*="firstName" i], input[placeholder*="First name" i]', firstName);
    safeSetValue('input[name*="lastName" i], input[placeholder*="Last name" i]', lastName);
    safeSetValue('input[name*="email" i], input[type="email"]', profile.contact_info?.email);
    safeSetValue('input[name*="phone" i], input[type="tel"]', profile.contact_info?.phone);
    safeSetValue('input[name*="address" i], input[placeholder*="Address" i]', profile.address);
    safeSetValue('input[name*="city" i], input[placeholder*="City" i]', city);
    safeSetValue('input[name*="province" i], input[placeholder*="Province" i], input[placeholder*="State / Province" i]', province);
    safeSetValue('input[name*="postal" i], input[placeholder*="Postal Code" i]', profile.postal_code);
    safeSetValue('input[name*="linkedin" i], input[placeholder*="LinkedIn" i]', profile.linkedin_url);
    safeSetValue('input[name*="website" i], input[placeholder*="Website" i]', profile.portfolio_url);
    safeSetValue('input[name*="date-available" i], input[placeholder*="Date Available" i]', ''); // No data for this yet
}

// Helper to inject the autoFillForm function into the active tab
function injectAutoFill(profileData) {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs.length > 0) {
      chrome.scripting.executeScript({
        target: { tabId: tabs[0].id },
        func: autoFillForm,
        args: [profileData]
      });
    } else {
      console.error("Job Bot: Could not find an active tab to inject script.");
    }
  });
}