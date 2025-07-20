async function autoFillForm() {
  const url = new URL(window.location.href);
  const jobId = url.searchParams.get("jobId"); // Assuming jobId is in the URL

  if (!jobId) {
    alert("Job ID not found in URL.");
    return;
  }

  try {
    // 1. Get auth token
    const token = await new Promise((resolve) => {
      chrome.storage.local.get(["authToken"], (result) => {
        resolve(result.authToken);
      });
    });

    if (!token) {
      alert("Authentication token not found. Please log in.");
      return;
    }

    // 2. Call the new generate-documents endpoint
    const response = await fetch(`http://127.0.0.1:8000/api/jobs/${jobId}/generate-documents`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to generate documents: ${response.statusText}`);
    }

    const documents = await response.json();

    // 3. Fetch selectors and fill the form
    const selectorResponse = await fetch(`http://127.0.0.1:8000/api/selectors?domain=${window.location.hostname}`);
    const selectors = await selectorResponse.json();

    chrome.storage.local.get(['appData'], (result) => {
      const data = result.appData;
      if (!data) return alert('Load data first.');

      // Fill form using remote selectors and generated documents
      fillFields(selectors, data, documents);
    });

  } catch (error) {
    console.error('Error during form fill:', error);
    alert(`An error occurred: ${error.message}`);
  }
}

function fillFields(selectors, data, documents) {
  // Fill basic fields
  fillField(selectors.firstName || 'input[placeholder*="First name"]', data.profile.name.split(' ')[0]);
  fillField(selectors.lastName || 'input[placeholder*="Last name"]', data.profile.name.split(' ').slice(1).join(' '));
  fillField(selectors.email || 'input[type="email"]', data.profile.contact_info.email);
  fillField(selectors.phone || 'input[type="tel"]', data.profile.contact_info.phone);

  // Fill with generated content
  if (documents.cover_letter) {
    fillField(selectors.coverLetter || 'textarea[name*="cover_letter"]', documents.cover_letter);
  }

  // Handle resume upload
  if (documents.refined_resume) {
    // This is tricky due to security restrictions. We can't set the value of a file input.
    // We can, however, prompt the user to download the resume and select it.
    const resumeBlob = new Blob([documents.refined_resume], { type: 'text/plain' });
    const resumeUrl = URL.createObjectURL(resumeBlob);
    const downloadLink = document.createElement('a');
    downloadLink.href = resumeUrl;
    downloadLink.download = "refined_resume.txt";
    downloadLink.style.display = "none";
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);

    alert("Your refined resume has been downloaded. Please upload it to the file input field.");
  }

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