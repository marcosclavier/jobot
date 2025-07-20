async function autoFillForm() {
  const domain = window.location.hostname;

  try {
    // Fetch selectors from the backend
    const response = await fetch(`http://127.0.0.1:8000/api/selectors?domain=${domain}`);
    const remoteSelectors = await response.json();

    // Get local data
    chrome.storage.local.get(['appData'], (result) => {
      const data = result.appData;
      if (!data) return alert('Load data first.');

      // Fill form using remote selectors
      fillFields(remoteSelectors, data);
    });
  } catch (error) {
    console.error('Could not fetch remote selectors, falling back to local:', error);
    // Fallback to local selectors if the backend is unavailable
    chrome.storage.local.get(['appData', 'learnedSelectors'], (result) => {
      const data = result.appData;
      const selectors = result.learnedSelectors || {};
      if (!data) return alert('Load data first.');

      const domainSelectors = selectors[domain] || {};
      fillFields(domainSelectors, data);
    });
  }
}

function fillFields(selectors, data) {
  // Try to fill with learned/default selectors
  fillField(selectors.firstName || 'input[placeholder*="First name"]', data.profile.name.split(' ')[0]);
  fillField(selectors.lastName || 'input[placeholder*="Last name"]', data.profile.name.split(' ').slice(1).join(' '));
  fillField(selectors.email || 'input[type="email"]', data.profile.contact_info.email);
  fillField(selectors.phone || 'input[type="tel"]', data.profile.contact_info.phone);
  // Add more: cover letter, questions, etc.

  // Upload resume (prompt user due to security)
  const resumeInput = document.querySelector('input[type="file"]');
  if (resumeInput) alert('Select resume manually.');

  // If fill fails, trigger learning
  if (!document.querySelector(selectors.firstName)) {
    learnSelector('firstName', window.location.hostname);
  }

  // Submit if confirmed
  if (confirm('Form filled. Submit?')) {
    document.querySelector('button[type="submit"]').click();
  }
}

function fillField(selector, value) {
  const elem = document.querySelector(selector);
  if (elem) elem.value = value;
}

function learnSelector(field, domain) {
  alert(`Click the ${field} field to learn selector.`);
  document.addEventListener('click', function learn(e) {
    const newSelector = generateSelector(e.target);

    // Save to local storage for immediate use
    chrome.storage.local.get(['learnedSelectors'], (result) => {
      const selectors = result.learnedSelectors || {};
      selectors[domain] = selectors[domain] || {};
      selectors[domain][field] = newSelector;
      chrome.storage.local.set({ learnedSelectors: selectors });
    });

    // Send to backend
    fetch('http://127.0.0.1:8000/api/selectors', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ domain, field, selector: newSelector }),
    });

    document.removeEventListener('click', learn);
  }, { once: true });
}

function generateSelector(elem) {
  // Simple unique selector generator (improve with libs)
  let path = [];
  while (elem && elem.nodeType === 1) {
    let sel = elem.tagName.toLowerCase();
    if (elem.id) return `#${elem.id}`;
    if (elem.className) sel += `.${elem.className.split(' ').join('.')}`;
    path.unshift(sel);
    elem = elem.parentNode;
  }
  return path.join(' > ');
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'fill') {
    autoFillForm();
    sendResponse({status: 'done'});
  } else if (request.action === 'learn') {
    // For now, we'll just learn the 'firstName' field as an example
    learnSelector('firstName', window.location.hostname);
    sendResponse({status: 'learning started'});
  }
});
// Listen for messages from popup or background scrip