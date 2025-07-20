document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');

    // Registration Form
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

    // Login Form
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

    // CV Upload
    const uploadButton = document.getElementById('uploadButton');
    if (uploadButton) {
        console.log('Upload button found.');
        if (!token) {
            console.log('No token found, redirecting to login.');
            window.location.href = '/static/login.html';
            return;
        }
        console.log('Token found. Attaching click listener to upload button.');
        uploadButton.addEventListener('click', async () => {
            console.log('Upload button clicked.');
            const cvFile = document.getElementById('cvFile').files[0];
            if (!cvFile) {
                document.getElementById('uploadStatus').textContent = 'Please select a file.';
                console.log('No file selected.');
                return;
            }
            console.log('File selected:', cvFile.name);
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
                console.log('CV upload successful.');
            } else {
                const error = await response.json();
                document.getElementById('uploadStatus').textContent = `Error: ${error.detail}`;
                console.error('CV upload failed:', error.detail);
            }
        });
    }

    // Run Job Matching
    const runJobMatchingButton = document.getElementById('runJobMatchingButton');
    if (runJobMatchingButton) {
        if (!token) {
            window.location.href = '/static/login.html';
            return;
        }
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
            } else {
                const error = await response.json();
                document.getElementById('jobMatchingStatus').textContent = `Error: ${error.detail}`;
            }
        });
    }

    // Logout
    const logoutButton = document.getElementById('logoutButton');
    if (logoutButton) {
        logoutButton.addEventListener('click', () => {
            localStorage.removeItem('token');
            window.location.href = '/static/login.html';
        });
    }
});
