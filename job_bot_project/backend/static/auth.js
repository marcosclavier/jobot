document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    const jobListDiv = document.getElementById('job-list');
    const statusFilter = document.getElementById('statusFilter');

    // Redirect to login if no token on dashboard page
    if (window.location.pathname === '/static/index.html' && !token) {
        window.location.href = '/static/login.html';
        return;
    }

    // --- Helper function to fetch and display job matches ---
    async function fetchAndDisplayJobMatches(status = '') {
        if (!token) {
            console.log('No token found, cannot fetch job matches.');
            return;
        }
        jobListDiv.innerHTML = '<p>Loading job matches...</p>';
        try {
            let url = '/api/matches';
            if (status) {
                url += `?status=${status}`;
            }
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            if (response.ok) {
                const matches = await response.json();
                renderJobMatches(matches);
            } else {
                const error = await response.json();
                jobListDiv.innerHTML = `<p class="text-red-600">Error loading job matches: ${error.detail}</p>`;
                console.error('Error fetching job matches:', error.detail);
            }
        } catch (error) {
            jobListDiv.innerHTML = `<p class="text-red-600">Network error: ${error.message}</p>`;
            console.error('Network error fetching job matches:', error);
        }
    }

    // --- Helper function to render job matches ---
    function renderJobMatches(matches) {
        jobListDiv.innerHTML = ''; // Clear previous matches
        if (matches.length === 0) {
            jobListDiv.innerHTML = '<p>No job matches found for the selected filter.</p>';
            return;
        }

        matches.forEach(job => {
            const jobCard = document.createElement('div');
            jobCard.className = 'job-card bg-white p-6 rounded-lg shadow-md border border-gray-200';
            
            const jobDetails = job.job_details || {};
            const evaluation = job.evaluation || {};

            const fitScoreColor = evaluation.fit_score >= 7 ? 'text-green-600' : (evaluation.fit_score >= 4 ? 'text-yellow-600' : 'text-red-600');
            const applicationStatus = job.application_status || 'pending';
            const feedbackIcon = job.user_feedback === true ? '👍' : (job.user_feedback === false ? '👎' : '');

            jobCard.innerHTML = `
                <h3 class="text-xl font-semibold text-gray-800 mb-2">${jobDetails.title || 'N/A'} at ${jobDetails.company?.display_name || 'N/A'}</h3>
                <p class="text-gray-600 mb-1"><strong>Location:</strong> ${jobDetails.location?.display_name || 'N/A'}</p>
                <p class="text-gray-600 mb-1"><strong>Posted:</strong> ${jobDetails.created || 'N/A'}</p>
                <p class="text-gray-600 mb-1"><strong>Status:</strong> <span class="capitalize">${applicationStatus}</span> ${feedbackIcon}</p>
                <p class="text-gray-700 mb-2"><strong>Fit Score:</strong> <span class="${fitScoreColor} font-bold">${evaluation.fit_score || 'N/A'}/10</span></p>
                <p class="text-gray-700 mb-4"><strong>Summary:</strong> ${evaluation.summary || 'No summary available.'}</p>
                
                <div class="tooltip mb-4">
                    <button class="bg-gray-200 hover:bg-gray-300 text-gray-800 font-bold py-1 px-3 rounded text-sm">View Full Description</button>
                    <span class="tooltiptext">${jobDetails.full_description || jobDetails.description || 'No full description available.'}</span>
                </div>

                <div class="flex space-x-2">
                    <button class="apply-button bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded" data-job-id="${job.job_id}">Apply</button>
                    <button class="remove-button bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded" data-job-id="${job.job_id}">Remove</button>
                    <button class="feedback-button-up bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded" data-job-id="${job.job_id}" data-feedback="true">👍</button>
                    <button class="feedback-button-down bg-yellow-500 hover:bg-yellow-600 text-white font-bold py-2 px-4 rounded" data-job-id="${job.job_id}" data-feedback="false">👎</button>
                </div>
            `;
            jobListDiv.appendChild(jobCard);
        });

        // Attach event listeners to newly rendered buttons
        attachJobButtonListeners();
    }

    // --- Attach event listeners for job action buttons ---
    function attachJobButtonListeners() {
        document.querySelectorAll('.apply-button').forEach(button => {
            button.onclick = async (e) => {
                const jobId = e.target.dataset.jobId;
                const response = await fetch(`/api/matches/${jobId}/apply`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    }
                });
                if (response.ok) {
                    const data = await response.json();
                    alert(data.message);
                    window.open(data.application_url, '_blank'); // Open in new tab
                    fetchAndDisplayJobMatches(statusFilter.value); // Refresh list
                } else {
                    const error = await response.json();
                    alert(`Error applying: ${error.detail}`);
                }
            };
        });

        document.querySelectorAll('.remove-button').forEach(button => {
            button.onclick = async (e) => {
                const jobId = e.target.dataset.jobId;
                if (confirm('Are you sure you want to remove this job match?')) {
                    const response = await fetch(`/api/matches/${jobId}`, {
                        method: 'DELETE',
                        headers: {
                            'Authorization': `Bearer ${token}`
                        }
                    });
                    if (response.ok) {
                        alert('Job match removed successfully.');
                        fetchAndDisplayJobMatches(statusFilter.value); // Refresh list
                    } else {
                        const error = await response.json();
                        alert(`Error removing: ${error.detail}`);
                    }
                }
            };
        });

        document.querySelectorAll('.feedback-button-up, .feedback-button-down').forEach(button => {
            button.onclick = async (e) => {
                const jobId = e.target.dataset.jobId;
                const feedbackValue = e.target.dataset.feedback === 'true'; // Convert string to boolean
                const response = await fetch(`/api/matches/${jobId}/feedback`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ feedback: feedbackValue })
                });
                if (response.ok) {
                    alert('Feedback submitted successfully!');
                    fetchAndDisplayJobMatches(statusFilter.value); // Refresh list
                } else {
                    const error = await response.json();
                    alert(`Error submitting feedback: ${error.detail}`);
                }
            };
        });
    }

    // --- Event Listeners for main page elements ---

    // Registration Form (only if on register.html)
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            if (response.ok) {
                window.location.href = '/static/login.html';
            } else {
                const error = await response.json();
                document.getElementById('error-message').textContent = error.detail;
            }
        });
    }

    // Login Form (only if on login.html)
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({
                    'username': email,
                    'password': password
                })
            });
            if (response.ok) {
                const data = await response.json();
                localStorage.setItem('token', data.access_token);
                window.location.href = '/static/index.html';
            } else {
                const error = await response.json();
                document.getElementById('error-message').textContent = error.detail;
            }
        });
    }

    // CV Upload (only if on index.html)
    const uploadButton = document.getElementById('uploadButton');
    if (uploadButton) {
        uploadButton.addEventListener('click', async () => {
            const cvFile = document.getElementById('cvFile').files[0];
            if (!cvFile) {
                document.getElementById('uploadStatus').textContent = 'Please select a file.';
                return;
            }
            const formData = new FormData();
            formData.append('file', cvFile);
            const response = await fetch('/api/cv-upload', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });
            if (response.ok) {
                document.getElementById('uploadStatus').textContent = 'CV uploaded successfully!';
            } else {
                const error = await response.json();
                document.getElementById('uploadStatus').textContent = `Error: ${error.detail}`;
            }
        });
    }

    // Run Job Matching (only if on index.html)
    const runJobMatchingButton = document.getElementById('runJobMatchingButton');
    if (runJobMatchingButton) {
        runJobMatchingButton.addEventListener('click', async () => {
            document.getElementById('jobMatchingStatus').textContent = 'Initiating job matching...';
            const response = await fetch('/api/run-job-matching', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            if (response.ok) {
                const data = await response.json();
                document.getElementById('jobMatchingStatus').textContent = data.message;
                fetchAndDisplayJobMatches(statusFilter.value); // Refresh after triggering
            } else {
                const error = await response.json();
                document.getElementById('jobMatchingStatus').textContent = `Error: ${error.detail}`;
            }
        });
    }

    // Logout (only if on index.html)
    const logoutButton = document.getElementById('logoutButton');
    if (logoutButton) {
        logoutButton.addEventListener('click', () => {
            localStorage.removeItem('token');
            window.location.href = '/static/login.html';
        });
    }

    // Status Filter (only if on index.html)
    if (statusFilter) {
        statusFilter.addEventListener('change', () => {
            fetchAndDisplayJobMatches(statusFilter.value);
        });
    }

    // Initial fetch of job matches when the dashboard loads
    if (window.location.pathname === '/static/index.html' && token) {
        fetchAndDisplayJobMatches();
    }
});
