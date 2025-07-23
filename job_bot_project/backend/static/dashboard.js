document.addEventListener('DOMContentLoaded', () => {
    const logoutButton = document.getElementById('logoutButton');
    const resetButton = document.getElementById('resetProfileButton');
    const uploadButton = document.getElementById('uploadButton');
    const cvFile = document.getElementById('cvFile');
    const uploadStatus = document.getElementById('uploadStatus');
    const runJobMatchingButton = document.getElementById('runJobMatchingButton');
    const jobMatchingStatus = document.getElementById('jobMatchingStatus');
    const matchedStatusFilter = document.getElementById('matchedStatusFilter');
    const matchedJobList = document.getElementById('matched-job-list');
    const savedJobList = document.getElementById('saved-job-list');
    const jobCardTemplate = document.getElementById('job-card-template');
    const profileForm = document.getElementById('profile-form');
    const saveProfileButton = document.getElementById('saveProfileButton');

    // Tab switching logic
    const manageProfileTab = document.getElementById('manage-profile-tab');
    const matchedJobsTab = document.getElementById('matched-jobs-tab');
    const savedJobsTab = document.getElementById('saved-jobs-tab');
    const careerCoachTab = document.getElementById('career-coach-tab');
    const manageProfileContent = document.getElementById('manage-profile');
    const matchedJobsContent = document.getElementById('matched-jobs');
    const savedJobsContent = document.getElementById('saved-jobs');
    const careerCoachContent = document.getElementById('career-coach');

    function switchTab(tabName) {
        manageProfileTab.classList.remove('border-blue-600', 'text-blue-600');
        manageProfileContent.classList.add('hidden');
        matchedJobsTab.classList.remove('border-blue-600', 'text-blue-600');
        matchedJobsContent.classList.add('hidden');
        savedJobsTab.classList.remove('border-blue-600', 'text-blue-600');
        savedJobsContent.classList.add('hidden');
        careerCoachTab.classList.remove('border-blue-600', 'text-blue-600');
        careerCoachContent.classList.add('hidden');

        if (tabName === 'manage') {
            manageProfileTab.classList.add('border-blue-600', 'text-blue-600');
            manageProfileContent.classList.remove('hidden');
            fetchProfile();
        } else if (tabName === 'matched') {
            matchedJobsTab.classList.add('border-blue-600', 'text-blue-600');
            matchedJobsContent.classList.remove('hidden');
            fetchMatchedJobs();
        } else if (tabName === 'saved') {
            savedJobsTab.classList.add('border-blue-600', 'text-blue-600');
            savedJobsContent.classList.remove('hidden');
            fetchSavedJobs();
        } else if (tabName === 'coach') {
            careerCoachTab.classList.add('border-blue-600', 'text-blue-600');
            careerCoachContent.classList.remove('hidden');
        }
    }

    manageProfileTab.addEventListener('click', () => switchTab('manage'));
    matchedJobsTab.addEventListener('click', () => switchTab('matched'));
    savedJobsTab.addEventListener('click', () => switchTab('saved'));
    careerCoachTab.addEventListener('click', () => switchTab('coach'));

    // Initial tab load
    switchTab('manage');

    logoutButton.addEventListener('click', () => {
        document.cookie = "access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/";
        window.location.href = '/login';
    });

    resetButton.addEventListener('click', async () => {
        const token = await getAuthToken();
        if (!token) {
            alert('Authentication token not found. Please log in.');
            return;
        }

        if (confirm('Are you sure you want to reset your profile? This action cannot be undone.')) {
            try {
                const response = await fetch('/api/me/profile', {
                    method: 'DELETE',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (response.ok) {
                    alert('Profile reset successfully!');
                    window.location.reload();
                } else {
                    const error = await response.json();
                    alert(`Failed to reset profile: ${error.detail || response.statusText}`);
                }
            } catch (error) {
                alert(`An error occurred: ${error.message}`);
            }
        }
    });

    uploadButton.addEventListener('click', async () => {
        const file = cvFile.files[0];
        if (!file) {
            uploadStatus.textContent = 'Please select a file to upload.';
            uploadStatus.className = 'mt-2 text-sm text-red-600';
            return;
        }

        const token = await getAuthToken();
        if (!token) {
            uploadStatus.textContent = 'Authentication token not found. Please log in.';
            uploadStatus.className = 'mt-2 text-sm text-red-600';
            return;
        }

        uploadStatus.textContent = 'Uploading...';
        uploadStatus.className = 'mt-2 text-sm text-blue-600';

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/cv-upload', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });

            if (response.ok) {
                const result = await response.json();
                uploadStatus.textContent = `CV uploaded and profile updated successfully!`;
                uploadStatus.className = 'mt-2 text-sm text-green-600';
                fetchProfile(); // Refresh the profile form
            } else {
                const error = await response.json();
                uploadStatus.textContent = `Upload failed: ${error.detail || response.statusText}`;
                uploadStatus.className = 'mt-2 text-sm text-red-600';
            }
        } catch (error) {
            uploadStatus.textContent = `An error occurred: ${error.message}`;
            uploadStatus.className = 'mt-2 text-sm text-red-600';
        }
    });

    runJobMatchingButton.addEventListener('click', async () => {
        jobMatchingStatus.textContent = 'Running job matching... This may take a while.';
        jobMatchingStatus.className = 'mt-2 text-sm text-blue-600';
        const token = await getAuthToken();
        if (!token) {
            jobMatchingStatus.textContent = 'Authentication token not found. Please log in.';
            jobMatchingStatus.className = 'mt-2 text-sm text-red-600';
            return;
        }

        try {
            const response = await fetch('/api/run-job-matching', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const result = await response.json();
                jobMatchingStatus.textContent = `Job matching initiated: ${result.message}`;
                jobMatchingStatus.className = 'mt-2 text-sm text-green-600';
                // Optionally refresh job list after a delay
                setTimeout(fetchMatchedJobs, 5000); 
            } else {
                const error = await response.json();
                jobMatchingStatus.textContent = `Job matching failed: ${error.detail || response.statusText}`;
                jobMatchingStatus.className = 'mt-2 text-sm text-red-600';
            }
        } catch (error) {
            jobMatchingStatus.textContent = `An error occurred: ${error.message}`;
            jobMatchingStatus.className = 'mt-2 text-sm text-red-600';
        }
    });

    matchedStatusFilter.addEventListener('change', fetchMatchedJobs);

    function getAuthToken() {
        const name = "access_token=";
        const decodedCookie = decodeURIComponent(document.cookie);
        const ca = decodedCookie.split(';');
        for(let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') {
                c = c.substring(1);
            }
            if (c.indexOf(name) === 0) {
                return c.substring(name.length, c.length);
            }
        }
        return "";
    }

    async function fetchProfile() {
        const token = await getAuthToken();
        if (!token) {
            profileForm.innerHTML = '<p class="text-red-500">Please log in to view your profile.</p>';
            return;
        }

        try {
            const response = await fetch('/api/me/profile', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const profile = await response.json();
                const transformedProfile = { ...profile };
                if (profile.clusters) {
                    if (profile.clusters.work_experience?.data) {
                        transformedProfile.work_experience = profile.clusters.work_experience.data;
                    }
                    if (profile.clusters.education?.data) {
                        transformedProfile.education = profile.clusters.education.data;
                    }
                    delete transformedProfile.clusters;
                } else {
                    // Ensure defaults if missing (flat case)
                    transformedProfile.work_experience = profile.work_experience || [];
                    transformedProfile.education = profile.education || [];
                }
                transformedProfile.contact_info = profile.contact_info || {};
                console.log('Fetched Profile JSON:', JSON.stringify(profile, null, 2));
                console.log('Transformed Profile JSON:', JSON.stringify(transformedProfile, null, 2));
                renderProfileForm(transformedProfile);
            } else {
                profileForm.innerHTML = '<p class="text-red-500">Failed to load profile. Please upload your CV.</p>';
            }
        } catch (error) {
            profileForm.innerHTML = `<p class="text-red-500">An error occurred: ${error.message}</p>`;
        }
    }

    function renderProfileForm(profile) {
    profileForm.innerHTML = ''; // Clear the form

    const profileSchema = {
        name: { type: 'string' },
        contact_info: { 
            type: 'object', 
            schema: { email: { type: 'string' }, phone: { type: 'string' }, linkedin: { type: 'string' } }
        },
        experience_summary: { type: 'string' },
        enhanced_skills: { type: 'array-of-string' },
        work_experience: { 
            type: 'array-of-object', 
            schema: { title: { type: 'string' }, company: { type: 'string' }, dates: { type: 'string' }, description: { type: 'string' } }
        },
        education: { 
            type: 'array-of-object', 
            schema: { institution: { type: 'string' }, degree: { type: 'string' }, year: { type: 'string' } }
        },
        suggested_keywords: { type: 'array-of-string' },
        salary_range: { type: 'string' }
    };

    const createField = (key, fieldSchema, value, prefix = '') => {
        const fieldId = prefix ? `${prefix}.${key}` : key;
        const label = `<label for="${fieldId}" class="block text-sm font-medium text-gray-700 capitalize">${key.replace(/_/g, ' ')}</label>`;

        switch (fieldSchema.type) {
            case 'string':
                return `
                    <div class="mb-4">
                        ${label}
                        <input type="text" name="${fieldId}" id="${fieldId}" value="${value || ''}" class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md">
                    </div>
                `;
            case 'array-of-string':
                return `
                    <div class="mb-4">
                        ${label}
                        <textarea name="${fieldId}" id="${fieldId}" class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md">${(value || []).join(', ')}</textarea>
                    </div>
                `;
            case 'object': {
                const currentData = value || {};
                const fieldsHtml = Object.keys(fieldSchema.schema).map(nestedKey => 
                    createField(nestedKey, fieldSchema.schema[nestedKey], currentData[nestedKey], fieldId)
                ).join('');
                return `
                    <fieldset class="mb-4 p-2 border border-gray-200 rounded-lg">
                        <legend class="text-lg font-semibold text-gray-800 capitalize">${key.replace(/_/g, ' ')}</legend>
                        ${fieldsHtml}
                    </fieldset>
                `;
            }
            case 'array-of-object': {
                const items = value || [];
                const itemsHtml = items.map((item, index) => `
                    <div class="p-3 mb-2 border border-gray-300 rounded-md relative item-card">
                        <button type="button" class="absolute top-2 right-2 text-red-500 remove-item-btn">&times;</button>
                        ${Object.keys(fieldSchema.schema).map(itemKey => createField(itemKey, fieldSchema.schema[itemKey], item[itemKey], `${fieldId}[${index}]`)).join('')}
                    </div>
                `).join('');
                return `
                    <fieldset class="mb-4 p-2 border border-gray-200 rounded-lg" data-section="${key}">
                        <legend class="text-lg font-semibold text-gray-800 capitalize">${key.replace(/_/g, ' ')}</legend>
                        <div class="items-container">${itemsHtml}</div>
                        <button type="button" class="mt-2 text-blue-500 add-item-btn" data-type="${key}">+ Add ${key.replace(/_/g, ' ')}</button>
                    </fieldset>
                `;
            }
            default:
                return '';
        }
    };
    
    profileForm.innerHTML = Object.keys(profileSchema).map(key => {
        // Use the schema to drive the form creation
        return createField(key, profileSchema[key], profile[key]);
    }).join('');
}

profileForm.addEventListener('click', (e) => {
    if (e.target.classList.contains('add-item-btn')) {
        const type = e.target.dataset.type;
        const container = e.target.closest('fieldset').querySelector('.items-container');
        const newIndex = container.querySelectorAll('.item-card').length;

        const templates = {
            work_experience: { title: '', company: '', dates: '', description: '' },
            education: { institution: '', degree: '', year: '' }
        };
        const itemTemplate = templates[type];
        if (!itemTemplate) return;

        const newCard = document.createElement('div');
        newCard.className = 'p-3 mb-2 border border-gray-300 rounded-md relative item-card';
        
        const fieldsHtml = Object.keys(itemTemplate).map(key => {
            const fieldId = `${type}[${newIndex}][${key}]`;
            const label = `<label for="${fieldId}" class="block text-sm font-medium text-gray-700 capitalize">${key.replace(/_/g, ' ')}</label>`;
            return `
                <div class="mb-4">
                    ${label}
                    <input type="text" name="${fieldId}" id="${fieldId}" value="" class="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md">
                </div>
            `;
        }).join('');

        newCard.innerHTML = `
            <button type="button" class="absolute top-2 right-2 text-red-500 remove-item-btn">&times;</button>
            ${fieldsHtml}
        `;
        container.appendChild(newCard);
    }

    if (e.target.classList.contains('remove-item-btn')) {
        e.target.closest('.item-card').remove();
    }
});

saveProfileButton.addEventListener('click', async () => {
    const token = await getAuthToken();
    if (!token) {
        alert('Authentication token not found. Please log in.');
        return;
    }

    const formData = new FormData(profileForm);
    const updatedProfile = {};

    const setNestedValue = (obj, path, value) => {
        const keys = path.replace(/\[(\d+)\]/g, '.$1').split('.');
        let current = obj;
        for (let i = 0; i < keys.length - 1; i++) {
            const key = keys[i];
            const nextKey = keys[i + 1];
            const isNextKeyNumeric = !isNaN(parseInt(nextKey, 10));
            
            if (!current[key]) {
                current[key] = isNextKeyNumeric ? [] : {};
            }
            current = current[key];
        }
        const lastKey = keys[keys.length - 1];
        const index = parseInt(lastKey, 10);
        if (Array.isArray(current) && !isNaN(index)) {
             current[index] = value;
        } else {
            current[lastKey] = value;
        }
    };

    const profileData = {};
    for (const [key, value] of formData.entries()) {
        const path = key.split('.');
        let current = profileData;
        for(let i = 0; i < path.length - 1; i++) {
            const segment = path[i];
            const arrayMatch = segment.match(/(\w+)\[(\d+)\]/);
            if(arrayMatch) {
                const arrayKey = arrayMatch[1];
                const index = arrayMatch[2];
                if(!current[arrayKey]) current[arrayKey] = [];
                if(!current[arrayKey][index]) current[arrayKey][index] = {};
                current = current[arrayKey][index];
            } else {
                if(!current[segment]) current[segment] = {};
                current = current[segment];
            }
        }
        const finalKey = path[path.length - 1];
        if (finalKey.includes('skills') || finalKey.includes('suggested_keywords')) {
             current[finalKey] = value.split(',').map(s => s.trim());
        } else {
            current[finalKey] = value;
        }
    }

    // Clean up null/empty items from arrays
    ['work_experience', 'education'].forEach(key => {
        if(profileData[key]) {
            profileData[key] = profileData[key].filter(item => item && Object.values(item).some(v => v));
        }
    });

    try {
        const response = await fetch('/api/me/profile', {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(profileData)
        });

        if (response.ok) {
            alert('Profile updated successfully!');
            fetchProfile(); // Refresh the profile form
        } else {
            const error = await response.json();
            alert(`Failed to update profile: ${error.detail || response.statusText}`);
        }
    } catch (error) {
        alert(`An error occurred: ${error.message}`);
    }
});

    async function fetchMatchedJobs() {
        matchedJobList.innerHTML = '<p class="text-gray-500">Loading matched jobs...</p>';
        const token = await getAuthToken();
        if (!token) {
            matchedJobList.innerHTML = '<p class="text-red-500">Please log in to view matched jobs.</p>';
            return;
        }

        const status = matchedStatusFilter.value;
        const queryParams = status ? `?status=${status}` : '';

        try {
            const response = await fetch(`/api/matches${queryParams}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const jobs = await response.json();
                renderJobs(jobs, matchedJobList, 'matched');
            } else {
                const error = await response.json();
                matchedJobList.innerHTML = `<p class="text-red-500">Failed to load matched jobs: ${error.detail || response.statusText}</p>`;
            }
        } catch (error) {
            matchedJobList.innerHTML = `<p class="text-red-500">An error occurred: ${error.message}</p>`;
        }
    }

    async function fetchSavedJobs() {
        savedJobList.innerHTML = '<p class="text-gray-500">Loading saved jobs...</p>';
        const token = await getAuthToken();
        if (!token) {
            savedJobList.innerHTML = '<p class="text-red-500">Please log in to view saved jobs.</p>';
            return;
        }

        try {
            const response = await fetch('/api/saved-jobs', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const jobs = await response.json();
                renderJobs(jobs, savedJobList, 'saved');
            } else {
                const error = await response.json();
                savedJobList.innerHTML = `<p class="text-red-500">Failed to load saved jobs: ${error.detail || response.statusText}</p>`;
            }
        } catch (error) {
            savedJobList.innerHTML = `<p class="text-red-500">An error occurred: ${error.message}</p>`;
        }
    }

    function renderJobs(jobs, container, type) {
        container.innerHTML = ''; // Clear previous jobs
        if (jobs.length === 0) {
            container.innerHTML = `<p class="text-gray-500">No ${type} jobs found.</p>`;
            return;
        }

        jobs.forEach(job => {
            const jobCard = jobCardTemplate.content.cloneNode(true);
            const jobDetails = job.job_details || {};
            const evaluation = job.evaluation || {};

            jobCard.querySelector('[data-job-title]').textContent = jobDetails.title || 'N/A';
            jobCard.querySelector('[data-company-name]').textContent = jobDetails.company?.display_name || 'N/A';
            jobCard.querySelector('[data-job-location]').textContent = jobDetails.location?.display_name || 'N/A';
            jobCard.querySelector('[data-job-description]').textContent = jobDetails.description || jobDetails.full_description || 'No description available.';
            
            const matchScoreElement = jobCard.querySelector('[data-match-score]');
            if (matchScoreElement) {
                matchScoreElement.textContent = evaluation.fit_score !== undefined ? evaluation.fit_score : 'N/A';
            }

            const matchExplanationElement = jobCard.querySelector('[data-match-explanation]');
            if (matchExplanationElement) {
                matchExplanationElement.textContent = evaluation.explanation || 'No explanation available.';
            }

            const applyButton = jobCard.querySelector('.apply-button');
            if (applyButton) {
                applyButton.href = jobDetails.redirect_url || '#';
                applyButton.onclick = async (e) => {
                    e.preventDefault();
                    const token = await getAuthToken();
                    if (token) {
                        try {
                            const response = await fetch(`/api/matches/${job.job_id}/apply`, {
                                method: 'POST',
                                headers: {
                                    'Authorization': `Bearer ${token}`,
                                    'Content-Type': 'application/json'
                                }
                            });
                            if (response.ok) {
                                const result = await response.json();
                                window.open(result.application_url, '_blank');
                                fetchMatchedJobs(); // Refresh list
                            } else {
                                const error = await response.json();
                                alert(`Failed to mark as applied: ${error.detail || response.statusText}`);
                            }
                        } catch (error) {
                            alert(`An error occurred: ${error.message}`);
                        }
                    } else {
                        alert('Please log in to apply.');
                    }
                };
            }

            const removeButton = jobCard.querySelector('.remove-button');
            if (removeButton) {
                removeButton.onclick = async () => {
                    const token = await getAuthToken();
                    if (token) {
                        const endpoint = type === 'matched' ? `/api/matches/${job.job_id}` : `/api/saved-jobs/${job.job_id}`;
                        try {
                            const response = await fetch(endpoint, {
                                method: 'DELETE',
                                headers: {
                                    'Authorization': `Bearer ${token}`
                                }
                            });
                            if (response.ok) {
                                if (type === 'matched') fetchMatchedJobs();
                                else fetchSavedJobs();
                            } else {
                                const error = await response.json();
                                alert(`Failed to remove job: ${error.detail || response.statusText}`);
                            }
                        } catch (error) {
                            alert(`An error occurred: ${error.message}`);
                        }
                    } else {
                        alert('Please log in to remove jobs.');
                    }
                };
            }

            const saveButton = jobCard.querySelector('.save-button');
            if (saveButton) {
                if (type === 'saved') { // Hide save button for already saved jobs
                    saveButton.style.display = 'none';
                } else {
                    saveButton.onclick = async () => {
                        const token = await getAuthToken();
                        if (token) {
                            try {
                                const response = await fetch(`/api/matches/${job.job_id}/save`, {
                                    method: 'POST',
                                    headers: {
                                        'Authorization': `Bearer ${token}`,
                                        'Content-Type': 'application/json'
                                    }
                                });
                                if (response.ok) {
                                    alert('Job saved successfully!');
                                    saveButton.disabled = true;
                                    saveButton.textContent = 'Saved';
                                } else {
                                    const error = await response.json();
                                    alert(`Failed to save job: ${error.detail || response.statusText}`);
                                }
                            } catch (error) {
                                alert(`An error occurred: ${error.message}`);
                            }
                        } else {
                            alert('Please log in to save jobs.');
                        }
                    };
                }
            }

            const feedbackLikeButton = jobCard.querySelector('.feedback-like-button');
            const feedbackDislikeButton = jobCard.querySelector('.feedback-dislike-button');

            if (feedbackLikeButton) {
                feedbackLikeButton.onclick = async () => {
                    await sendFeedback(job.job_id, true);
                    fetchMatchedJobs(); // Refresh to show updated status
                };
            }
            if (feedbackDislikeButton) {
                feedbackDislikeButton.onclick = async () => {
                    await sendFeedback(job.job_id, false);
                    fetchMatchedJobs(); // Refresh to show updated status
                };
            }

            container.appendChild(jobCard);
        });
    }

    async function sendFeedback(jobId, feedbackValue) {
        const token = await getAuthToken();
        if (!token) {
            alert('Please log in to submit feedback.');
            return;
        }
        try {
            const response = await fetch(`/api/matches/${jobId}/feedback`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ feedback: feedbackValue })
            });
            if (!response.ok) {
                const error = await response.json();
                alert(`Failed to submit feedback: ${error.detail || response.statusText}`);
            }
        } catch (error) {
            alert(`An error occurred while submitting feedback: ${error.message}`);
        }
    }

    // --- Career Coach WebSocket Logic ---
    let ws;

    function initializeWebSocket() {
        const token = getAuthToken(); // This function already gets the token from cookies
        if (!token) {
            console.error("Authentication token not found. Cannot connect to chat.");
            return;
        }

        ws = new WebSocket(`ws://${window.location.host}/api/chat?token=${token}`);

        ws.onopen = () => {
            console.log("WebSocket connection established.");
        };

        ws.onmessage = (event) => {
            const chatMessages = document.getElementById('chat-messages');
            chatMessages.innerHTML += `<p><strong>Coach:</strong> ${event.data}</p>`;
            chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to bottom
        };

        ws.onclose = () => {
            console.log("WebSocket connection closed.");
        };

        ws.onerror = (error) => {
            console.error("WebSocket error:", error);
        };
    }

    function sendMessage() {
        const input = document.getElementById('chat-input');
        if (ws && ws.readyState === WebSocket.OPEN && input.value) {
            ws.send(input.value);
            const chatMessages = document.getElementById('chat-messages');
            chatMessages.innerHTML += `<p><strong>You:</strong> ${input.value}</p>`;
            input.value = '';
            chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to bottom
        }
    }

    // Initialize WebSocket when the career coach tab is clicked
    if (careerCoachTab) {
        careerCoachTab.addEventListener('click', () => {
            if (!ws || ws.readyState === WebSocket.CLOSED) {
                initializeWebSocket();
            }
        });
    }

    // Attach event listener to the send button
    const sendMessageButton = document.getElementById('sendMessageButton');
    if (sendMessageButton) {
        sendMessageButton.addEventListener('click', sendMessage);
    }
});