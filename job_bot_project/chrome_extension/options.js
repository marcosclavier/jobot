document.addEventListener('DOMContentLoaded', () => {
  const jsonFileInput = document.getElementById('jsonFile');
  const statusP = document.getElementById('status');

  jsonFileInput.addEventListener('change', (event) => {
    const file = event.target.files[0];
    if (!file) {
      statusP.textContent = 'No file selected.';
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const rawData = JSON.parse(e.target.result);
        const adaptedData = {
          profile: {
            name: rawData.personal.name,
            contact_info: {
              email: rawData.personal.email,
              phone: rawData.personal.phone
            },
            location: rawData.personal.location,
            address: rawData.personal.address || '',
            postal_code: rawData.personal.postal_code || '',
            linkedin_url: rawData.personal.linkedin_url || ''
          },
          materials: {
            cover_letter: "",
            question_answers: []
          }
        };
        chrome.storage.local.set({ appData: adaptedData }, () => {
          statusP.textContent = 'Data loaded successfully!';
        });
      } catch (error) {
        statusP.textContent = 'Error: Invalid JSON file.';
      }
    };
    reader.readAsText(file);
  });
});
