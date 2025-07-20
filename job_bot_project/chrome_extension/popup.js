document.addEventListener('DOMContentLoaded', () => {
  const fillFormButton = document.getElementById('fillForm');
  const optionsLink = document.getElementById('optionsLink');

  fillFormButton.addEventListener('click', () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      chrome.scripting.executeScript({
        target: { tabId: tabs[0].id },
        func: autoFillForm
      });
    });
  });

  optionsLink.addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });
});

function autoFillForm() {
  chrome.storage.local.get(['appData'], (result) => {
    const data = result.appData;
    if (!data) {
      alert('Please load your data file in the extension options first.');
      return;
    }

    // Helper function to safely set the value of an input field
    const safeSetValue = (selector, value) => {
      const element = document.querySelector(selector);
      if (element) {
        element.value = value;
      } else {
        console.log(`Job Bot: Could not find element with selector: ${selector}`);
      }
    };

    const profile = data.profile;
    const locationParts = profile.location.split(', ');
    const city = locationParts[0];
    const province = locationParts.length > 1 ? locationParts[1] : '';

    safeSetValue('input[name="firstName"], input[placeholder*="First name"]', profile.name.split(' ')[0]);
    safeSetValue('input[name="lastName"], input[placeholder*="Last name"]', profile.name.split(' ').slice(1).join(' '));
    safeSetValue('input[name="email"], input[type="email"]', profile.contact_info.email);
    safeSetValue('input[name="phone"], input[type="tel"]', profile.contact_info.phone);
    safeSetValue('input[name*="address"], input[placeholder*="Address"]', profile.address);
    safeSetValue('input[name*="city"], input[placeholder*="City"]', city);
    safeSetValue('input[name*="province"], input[placeholder*="Province"], input[placeholder*="State / Province"]', province);
    safeSetValue('input[name*="postal"], input[placeholder*="Postal Code"]', profile.postal_code);
    safeSetValue('input[name*="linkedin"], input[placeholder*="LinkedIn"]', profile.linkedin_url);
    safeSetValue('input[name*="date-available"], input[placeholder*="Date Available"]', ''); // No data for this yet
  });
}
