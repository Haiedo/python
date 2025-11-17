// Expense Splitter - Main JavaScript
// API Handler and Utilities

// Auto-detect API base URL
// Use window.location.origin to automatically detect the server address
// This works whether accessing via localhost, IP address, or domain name
const API_BASE_URL = `${window.location.origin}/api`;

// Auth Token Management
const AuthToken = {
    get: () => localStorage.getItem('access_token'),
    set: (token) => localStorage.setItem('access_token', token),
    remove: () => localStorage.removeItem('access_token'),
    isAuthenticated: () => !!localStorage.getItem('access_token')
};

// API Client
class APIClient {
    constructor(baseURL) {
        this.baseURL = baseURL;
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const token = AuthToken.get();

        const headers = {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` }),
            ...options.headers
        };

        const config = {
            ...options,
            headers
        };

        try {
            showLoading();
            const response = await fetch(url, config);

            // Always hide loading after response
            hideLoading();

            const data = await response.json();

            if (!response.ok) {
                if (response.status === 401) {
                    AuthToken.remove();
                    window.location.href = '/login';
                    return;
                }
                throw new Error(data.error || 'Request failed');
            }

            return data;
        } catch (error) {
            // Ensure loading is hidden even if error occurs
            hideLoading();
            throw error;
        }
    }

    get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }

    post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }
}

const api = new APIClient(API_BASE_URL);

// Auth API
const AuthAPI = {
    login: (username, password) => api.post('/auth/login', { username, password }),
    register: (userData) => api.post('/auth/register', userData),
    getProfile: () => api.get('/auth/profile'),
    updateProfile: (data) => api.put('/auth/profile', data),
    changePassword: (data) => api.post('/auth/change-password', data),
    logout: () => {
        AuthToken.remove();
        window.location.href = '/login';
    }
};

// Groups API
const GroupsAPI = {
    getAll: () => api.get('/groups'),
    getById: (id) => api.get(`/groups/${id}`),
    create: (data) => api.post('/groups', data),
    update: (id, data) => api.put(`/groups/${id}`, data),
    delete: (id) => api.delete(`/groups/${id}`),
    searchUsers: (query) => api.get(`/groups/search-users?q=${encodeURIComponent(query)}`),
    addMember: (groupId, userId, role) => api.post(`/groups/${groupId}/members`, { user_id: userId, role }),
    removeMember: (groupId, userId) => api.delete(`/groups/${groupId}/members/${userId}`),
    updateMemberRole: (groupId, userId, role) => api.put(`/groups/${groupId}/members/${userId}/role`, { role }),
    leave: (groupId) => api.post(`/groups/${groupId}/leave`)
};

// Expenses API
const ExpensesAPI = {
    getAll: (groupId = null, status = null) => {
        let endpoint = '/expenses?';
        if (groupId) endpoint += `group_id=${groupId}&`;
        if (status) endpoint += `status=${status}`;
        return api.get(endpoint);
    },
    getById: (id) => api.get(`/expenses/${id}`),
    create: (data) => api.post('/expenses', data),
    update: (id, data) => api.put(`/expenses/${id}`, data),
    delete: (id) => api.delete(`/expenses/${id}`),
    approve: (id) => api.post(`/expenses/${id}/approve`),
    reject: (id) => api.post(`/expenses/${id}/reject`)
};

// Payments API
const PaymentsAPI = {
    getBalances: (groupId) => api.get(`/groups/${groupId}/balances`),
    getSettlements: (groupId) => api.get(`/groups/${groupId}/settlements`),
    getMyDebts: (groupId) => api.get(`/groups/${groupId}/my-debts`),
    create: (data) => api.post('/payments', data),
    createVNPay: (data) => api.post('/payments/vnpay-create', data),
    getAll: (groupId = null) => {
        let endpoint = '/payments';
        if (groupId) endpoint += `?group_id=${groupId}`;
        return api.get(endpoint);
    },
    approve: (id) => api.post(`/payments/${id}/approve`),
    reject: (id) => api.post(`/payments/${id}/reject`)
};

// Dashboard API
const DashboardAPI = {
    getStats: () => api.get('/dashboard'),
    getExpensesByCategory: () => api.get('/dashboard/expenses-by-category'),
    getRecentActivity: () => api.get('/dashboard/recent-activity'),
    getExpenseTrend: () => api.get('/dashboard/expense-trend')
};

// Admin API
const AdminAPI = {
    getDashboard: () => api.get('/admin/dashboard'),
    getCategories: () => api.get('/admin/categories'),
    createCategory: (data) => api.post('/admin/categories', data),
    updateCategory: (id, data) => api.put(`/admin/categories/${id}`, data),
    deleteCategory: (id) => api.delete(`/admin/categories/${id}`)
};

// UI Utilities
let loadingCount = 0;
let loadingTimeout = null;

function showLoading() {
    loadingCount++;

    // Clear any existing timeout
    if (loadingTimeout) {
        clearTimeout(loadingTimeout);
    }

    // Only create overlay if it doesn't exist
    if (!document.getElementById('loading-overlay')) {
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.id = 'loading-overlay';
        overlay.innerHTML = '<div class="spinner-border text-light" role="status"></div>';
        document.body.appendChild(overlay);
    }

    // Safety timeout - force hide after 30 seconds
    loadingTimeout = setTimeout(() => {
        forceHideLoading();
    }, 30000);
}

function hideLoading() {
    loadingCount--;

    // Only remove overlay when all requests are done
    if (loadingCount <= 0) {
        forceHideLoading();
    }
}

function forceHideLoading() {
    loadingCount = 0;
    if (loadingTimeout) {
        clearTimeout(loadingTimeout);
        loadingTimeout = null;
    }
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

function showSuccess(message) {
    showToast(message, 'success');
}

function showError(message) {
    showToast(message, 'danger');
}

function showToast(message, type = 'info') {
    const toastContainer = getOrCreateToastContainer();

    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show`;
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 5000);
}

function getOrCreateToastContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        document.body.appendChild(container);
    }
    return container;
}

// Format utilities
function formatCurrency(amount, currency = 'VND') {
    if (currency === 'VND') {
        return new Intl.NumberFormat('vi-VN', {
            style: 'currency',
            currency: 'VND'
        }).format(amount);
    }
    return `${amount.toLocaleString()} ${currency}`;
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('vi-VN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
}

function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('vi-VN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Protected page check
function checkAuth() {
    if (!AuthToken.isAuthenticated()) {
        window.location.href = '/login';
        return false;
    }
    return true;
}

// Logout function
function logout() {
    if (confirm('Are you sure you want to logout?')) {
        AuthAPI.logout();
    }
}

// Initialize tooltips and popovers (Bootstrap)
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
