// Sidebar Toggle
document.addEventListener('DOMContentLoaded', () => {
    const menuToggle = document.getElementById('menu-toggle');
    if (menuToggle) {
        menuToggle.addEventListener('click', (e) => {
            e.preventDefault();
            document.getElementById('wrapper').classList.toggle('toggled');
        });
    }

    // Dynamically set user info in header
    populateHeaderUser();
});

/**
 * Populates the header with user info from localStorage.
 */
function populateHeaderUser() {
    try {
        const userData = JSON.parse(localStorage.getItem('userData'));
        if (userData) {
            document.getElementById('header-username').textContent = `${userData.first_name} ${userData.last_name}`;
            if (userData.profile && userData.profile.avatar) {
                document.getElementById('header-avatar').src = userData.profile.avatar;
            }
        }
    } catch (e) {
        console.error("Could not parse user data from localStorage", e);
    }
}

/**
 * A central API client for all HRMaster fetch requests.
 * Handles token authentication, JSON content-type, and global error handling.
 */
const hrApi = {
    async _fetch(endpoint, options = {}) {
        const token = localStorage.getItem('authToken');
        
        const defaultHeaders = {
            'Content-Type': 'application/json',
            'X-CSRFToken': '{{ csrf_token }}', // For session auth if needed
        };

        if (token) {
            defaultHeaders['Authorization'] = `Token ${token}`;
        }

        options.headers = { ...defaultHeaders, ...options.headers };

        try {
            const response = await fetch(`/api/${endpoint}`, options);

            if (response.status === 401 || response.status === 403) {
                // Token is invalid or expired
                localStorage.removeItem('authToken');
                localStorage.removeItem('userData');
                window.location.href = '/api-auth/login/'; // Redirect to login
                return;
            }

            if (!response.ok) {
                // Try to parse error message from API
                let errorData;
                try {
                    errorData = await response.json();
                } catch (e) {
                    throw new Error(`HTTP error ${response.status}`);
                }
                
                // Find the most specific error message
                const message = errorData.detail || errorData.error || 
                              (errorData.non_field_errors ? errorData.non_field_errors[0] : null) || 
                              'An API error occurred.';
                throw new Error(message);
            }

            if (response.status === 204) { // No Content
                return null;
            }
            
            return await response.json();

        } catch (error) {
            console.error(`[hrApi Error] ${options.method || 'GET'} /api/${endpoint}:`, error);
            throw error; // Re-throw for local handling
        }
    },

    get(endpoint, options = {}) {
        return this._fetch(endpoint, { ...options, method: 'GET' });
    },

    post(endpoint, body, options = {}) {
        return this._fetch(endpoint, { ...options, method: 'POST', body: JSON.stringify(body) });
    },

    patch(endpoint, body, options = {}) {
        return this._fetch(endpoint, { ...options, method: 'PATCH', body: JSON.stringify(body) });
    },
    
    put(endpoint, body, options = {}) {
        return this._fetch(endpoint, { ...options, method: 'PUT', body: JSON.stringify(body) });
    },

    delete(endpoint, options = {}) {
        return this._fetch(endpoint, { ...options, method: 'DELETE' });
    }
};

/**
 * Displays a Bootstrap toast notification.
 * @param {string} message - The message to display.
 * @param {string} type - 'success', 'danger', or 'info'
 */
function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;

    const toastId = 'toast-' + Math.random().toString(36).substr(2, 9);
    
    let icon;
    let bgClass;
    
    if (type === 'danger') {
        icon = '<i class="fas fa-times-circle me-2"></i>';
        bgClass = 'bg-danger';
    } else if (type === 'info') {
        icon = '<i class="fas fa-info-circle me-2"></i>';
        bgClass = 'bg-info';
    } else {
        icon = '<i class="fas fa-check-circle me-2"></i>';
        bgClass = 'bg-success';
    }

    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body">
                    ${icon}
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;
    
    toastContainer.innerHTML += toastHtml;
    
    const toastEl = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
    
    toastEl.addEventListener('hidden.bs.toast', () => {
        toastEl.remove();
    });
    
    toast.show();
}