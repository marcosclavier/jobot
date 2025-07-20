document.addEventListener('DOMContentLoaded', () => {
    const logoutButton = document.getElementById('logoutButton');
    const uploadButton = document.getElementById('uploadButton');
    const cvFile = document.getElementById('cvFile');
    const uploadStatus = document.getElementById('uploadStatus');
    const runJobMatchingButton = document.getElementById('runJobMatchingButton');
    const jobMatchingStatus = document.getElementById('jobMatchingStatus');
    const matchedStatusFilter = document.getElementById('matchedStatusFilter');
    const matchedJobList = document.getElementById('matched-job-list');
    const savedJobList = document.getElementById('saved-job-list');
    const jobCardTemplate = document.getElementById('job-card-template');

    // Tab switching logic
    const matchedJobsTab = document.getElementById('matched-jobs-tab');
    const savedJobsTab = document.getElementById('saved-jobs-tab');
    const matchedJobsContent = document.getElementById('matched-jobs');
    const savedJobsContent = document.getElementById('saved-jobs');

    function switchTab(tabName) {
        if (tabName === 'matched') {
            matchedJobsTab.classList.add('border-blue-600', 'text-blue-600');
            matchedJobsTab.classList.remove('hover:text-gray-600', 'hover:border-gray-300');
            matchedJobsContent.classList.remove('hidden');
            
            savedJobsTab.classList.remove('border-blue-600', 'text-blue-600');
            savedJobsTab.classList.add('hover:text-gray-600', 'hover:border-gray-300');
            savedJobsContent.classList.add('hidden');
            fetchMatchedJobs();
        } else if (tabName === 'saved') {
            savedJobsTab.classList.add('border-blue-600', 'text-blue-600');
            savedJobsTab.classList.remove('hover:text-gray-600', 'hover:border-gray-300');
            savedJobsContent.classList.remove('hidden');

            matchedJobsTab.classList.remove('border-blue-600', 'text-blue-600');
            matchedJobsTab.classList.add('hover:text-gray-600', 'hover:border-gray-300');
            matchedJobsContent.classList.add('hidden');
            fetchSavedJobs();
        }
    }

    matchedJobsTab.addEventListener('click', () => switchTab('matched'));
    savedJobsTab.addEventListener('click', () => switchTab('saved'));

    // Initial tab load
    switchTab('matched');

    logoutButton.addEventListener('click', () => {
        document.cookie = "access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/";
        window.location.href = '/login';
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

    async function getAuthToken() {
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

    // Initial fetch of matched jobs when the dashboard loads
    fetchMatchedJobs();

    // --- Function to check for an existing profile on page load ---
    async function checkForExistingProfile() {
        const token = await getAuthToken();
        if (!token) return; // No token, no profile

        try {
            const response = await fetch('/api/me/profile', {
                method: 'GET',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const profile = await response.json();
                // Profile exists, update the UI
                uploadStatus.textContent = `Profile for ${profile.name} is loaded. Upload a new CV to update.`;
                uploadButton.disabled = false;
                uploadButton.textContent = 'Update Profile';
                uploadButton.classList.remove('bg-gray-400', 'cursor-not-allowed');
                uploadButton.classList.add('bg-blue-600', 'hover:bg-blue-700');
                cvFile.disabled = false;

            } else if (response.status === 404) {
                // Profile does not exist, do nothing. The user needs to upload.
                console.log('No profile found for user. CV upload is required.');
            }
        } catch (error) {
            console.error('Error checking for profile:', error);
        }
    }

    // Call the new function on page load
    checkForExistingProfile();
});