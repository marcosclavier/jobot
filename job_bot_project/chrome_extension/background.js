chrome.runtime.onInstalled.addListener(() => {
  console.log('Extension installed');
});

// Listen for messages if needed (e.g., from content script)
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getData') {
    chrome.storage.local.get(['appData'], (result) => {
      sendResponse(result.appData);
    });
    return true;
  }
});