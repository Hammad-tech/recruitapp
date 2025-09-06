// Recruitment Automation System - Frontend JavaScript

// Global variables
let dashboardRefreshInterval;
let notificationCount = 0;

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    try {
        initializeApp();
    } catch (error) {
        console.error('Error initializing application:', error);
    }
});

// Cleanup when page is unloaded
window.addEventListener('beforeunload', function() {
    if (dashboardRefreshInterval) {
        clearInterval(dashboardRefreshInterval);
        dashboardRefreshInterval = null;
    }
});

// Main initialization function
function initializeApp() {
    try {
        initializeFeatherIcons();
        initializeTooltips();
        initializeFileUpload();
        initializeFormValidation();
        initializeSearchAndFilter();
        initializeNotifications();
        
        // Page-specific initializations
        if (isPage('dashboard')) {
            initializeDashboard();
        }
        
        if (isPage('candidates')) {
            initializeCandidatesPage();
        }
        
        if (isPage('jobs')) {
            initializeJobsPage();
        }
    } catch (error) {
        console.error('Error in initializeApp:', error);
    }
}

// Utility Functions
function isPage(pageName) {
    return document.body.classList.contains(`page-${pageName}`) || 
           window.location.pathname.includes(pageName);
}

function initializeFeatherIcons() {
    try {
        if (typeof feather !== 'undefined') {
            feather.replace();
        } else {
            console.warn('Feather icons library not loaded');
        }
    } catch (error) {
        console.error('Error initializing Feather icons:', error);
    }
}

function initializeTooltips() {
    try {
        // Initialize Bootstrap tooltips
        if (typeof bootstrap !== 'undefined') {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        } else {
            console.warn('Bootstrap library not loaded');
        }
    } catch (error) {
        console.error('Error initializing tooltips:', error);
    }
}

// Dashboard Functions
function initializeDashboard() {
    startDashboardRefresh();
    initializeQuickActions();
    loadRecentActivity();
}

function startDashboardRefresh() {
    // Clear any existing interval to prevent duplicates
    if (dashboardRefreshInterval) {
        clearInterval(dashboardRefreshInterval);
    }
    
    // Refresh dashboard stats every 30 seconds
    dashboardRefreshInterval = setInterval(refreshDashboardStats, 30000);
    
    // Stop refresh when page is hidden (performance optimization)
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            if (dashboardRefreshInterval) {
                clearInterval(dashboardRefreshInterval);
                dashboardRefreshInterval = null;
            }
        } else {
            // Only start if not already running
            if (!dashboardRefreshInterval) {
                dashboardRefreshInterval = setInterval(refreshDashboardStats, 30000);
            }
        }
    });
}

function refreshDashboardStats() {
    // Don't refresh if page is hidden
    if (document.hidden) {
        return;
    }
    
    fetch('/api/stats')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data && typeof data === 'object') {
                updateDashboardStats(data);
                updateLastRefreshTime();
            } else {
                throw new Error('Invalid data format received');
            }
        })
        .catch(error => {
            console.error('Error refreshing dashboard stats:', error);
            // Don't show notification on every refresh failure to avoid spam
            // Only show if it's been more than 5 minutes since last error
            const now = Date.now();
            if (!window.lastDashboardError || (now - window.lastDashboardError) > 300000) {
                showNotification('Dashboard refresh failed - will retry automatically', 'warning');
                window.lastDashboardError = now;
            }
        });
}

function updateDashboardStats(data) {
    // Validate data to prevent NaN errors
    if (!data || typeof data !== 'object') {
        console.warn('Invalid dashboard data received:', data);
        return;
    }
    
    // Check if data has the expected structure
    if (data.success && data.stats) {
        // Data is in the correct format from /api/stats
        const stats = data.stats;
        const elements = {
            'total-jobs': stats.total_jobs || 0,
            'total-candidates': stats.total_candidates || 0,
            'new-candidates': stats.new_candidates || 0,
            'high-matches': stats.high_matches || 0
        };
        
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                // Ensure value is a valid number
                const numericValue = parseInt(value) || 0;
                const currentValue = parseInt(element.textContent) || 0;
                
                // Only animate if we have valid numbers
                if (!isNaN(numericValue) && !isNaN(currentValue)) {
                    animateCounter(element, currentValue, numericValue);
                } else {
                    // Fallback: just update the text directly
                    element.textContent = numericValue;
                }
            }
        });
    } else {
        // Fallback: try direct access (for backward compatibility)
        const elements = {
            'total-jobs': data.total_jobs || 0,
            'total-candidates': data.total_candidates || 0,
            'new-candidates': data.new_candidates || 0,
            'high-matches': data.high_matches || 0
        };
        
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                const numericValue = parseInt(value) || 0;
                element.textContent = numericValue;
            }
        });
        
        console.warn('Dashboard data structure unexpected, using fallback:', data);
    }
}

function animateCounter(element, start, end) {
    // Validate inputs to prevent NaN errors
    if (isNaN(start) || isNaN(end)) {
        console.warn('Invalid counter values:', { start, end });
        element.textContent = end || 0;
        return;
    }
    
    // Ensure we have valid numbers
    start = parseInt(start) || 0;
    end = parseInt(end) || 0;
    
    const duration = 1000; // 1 second
    const increment = (end - start) / (duration / 16); // 60 FPS
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
            element.textContent = end;
            clearInterval(timer);
        } else {
            element.textContent = Math.floor(current);
        }
    }, 16);
}

function updateLastRefreshTime() {
    const element = document.getElementById('last-updated');
    if (element) {
        element.textContent = new Date().toLocaleString();
    }
}

// Safe function to update dashboard numbers
function safeUpdateDashboardNumber(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        const numericValue = parseInt(value) || 0;
        if (!isNaN(numericValue)) {
            element.textContent = numericValue;
        } else {
            element.textContent = '0';
            console.warn(`Invalid value for ${elementId}:`, value);
        }
    }
}

function initializeQuickActions() {
    // Add click handlers for quick action buttons
    const quickActions = document.querySelectorAll('[data-quick-action]');
    quickActions.forEach(button => {
        button.addEventListener('click', function() {
            const action = this.dataset.quickAction;
            handleQuickAction(action);
        });
    });
}

function handleQuickAction(action) {
    switch (action) {
        case 'refresh':
            refreshDashboardStats();
            showNotification('Dashboard refreshed', 'success');
            break;
        case 'export':
            exportData();
            break;
        default:
            console.log('Unknown quick action:', action);
    }
}

function loadRecentActivity() {
    fetch('/api/recent_activity')
        .then(response => response.json())
        .then(data => {
            updateRecentActivity(data);
        })
        .catch(error => {
            console.error('Error loading recent activity:', error);
        });
}

function updateRecentActivity(activities) {
    const container = document.getElementById('recent-activity');
    if (!container) return;
    
    if (activities.length === 0) {
        container.innerHTML = '<p class="text-muted">No recent activity</p>';
        return;
    }
    
    const html = activities.map(activity => `
        <div class="d-flex align-items-center mb-2">
            <div class="flex-grow-1">
                <small class="text-muted">${formatActivityTime(activity.timestamp)}</small>
                <div>${activity.message}</div>
            </div>
            ${activity.url ? `<a href="${activity.url}" class="btn btn-sm btn-outline-primary">View</a>` : ''}
        </div>
    `).join('');
    
    container.innerHTML = html;
}

function formatActivityTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return `${Math.floor(diff / 86400000)}d ago`;
}

// File Upload Functions
function initializeFileUpload() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        setupFileUploadHandlers(input);
    });
}

function setupFileUploadHandlers(input) {
    const dropZone = input.closest('.file-upload-area') || input.parentElement;
    
    // Drag and drop handlers
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('dragover'), false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('dragover'), false);
    });
    
    dropZone.addEventListener('drop', (e) => handleFileDrop(e, input), false);
    
    // File input change handler
    input.addEventListener('change', () => handleFileSelect(input));
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function handleFileDrop(e, input) {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        input.files = files;
        handleFileSelect(input);
    }
}

function handleFileSelect(input) {
    const files = input.files;
    if (files.length === 0) return;
    
    const file = files[0];
    
    // Validate file
    if (!isValidFile(file)) {
        showNotification('Invalid file type. Please select a PDF, DOC, DOCX, or TXT file.', 'error');
        input.value = '';
        return;
    }
    
    if (file.size > 16 * 1024 * 1024) { // 16MB
        showNotification('File too large. Maximum size is 16MB.', 'error');
        input.value = '';
        return;
    }
    
    // Update UI to show selected file
    updateFileUploadUI(input, file);
}

function isValidFile(file) {
    const allowedTypes = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain'
    ];
    
    const allowedExtensions = ['.pdf', '.doc', '.docx', '.txt'];
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    
    return allowedTypes.includes(file.type) || allowedExtensions.includes(fileExtension);
}

function updateFileUploadUI(input, file) {
    const container = input.closest('.file-upload-container') || input.parentElement;
    const feedback = container.querySelector('.file-upload-feedback') || 
                    document.createElement('div');
    
    feedback.className = 'file-upload-feedback mt-2';
    feedback.innerHTML = `
        <div class="alert alert-success">
            <i data-feather="file" class="me-2"></i>
            <strong>${file.name}</strong> (${formatFileSize(file.size)})
            <button type="button" class="btn btn-sm btn-outline-danger ms-2" onclick="clearFileSelection('${input.id}')">
                <i data-feather="x"></i>
            </button>
        </div>
    `;
    
    if (!container.querySelector('.file-upload-feedback')) {
        container.appendChild(feedback);
    }
    
    // Reinitialize feather icons
    feather.replace();
}

function clearFileSelection(inputId) {
    const input = document.getElementById(inputId);
    if (input) {
        input.value = '';
        const feedback = input.closest('.file-upload-container')?.querySelector('.file-upload-feedback');
        if (feedback) {
            feedback.remove();
        }
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Form Validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('form[novalidate]');
    forms.forEach(form => {
        form.addEventListener('submit', handleFormSubmit, false);
    });
}

function handleFormSubmit(event) {
    const form = event.target;
    
    if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
        
        // Show validation errors
        const firstInvalid = form.querySelector(':invalid');
        if (firstInvalid) {
            firstInvalid.focus();
            showNotification('Please check the form for errors', 'error');
        }
    }
    
    form.classList.add('was-validated');
}

// Search and Filter
function initializeSearchAndFilter() {
    const searchInputs = document.querySelectorAll('[data-search]');
    searchInputs.forEach(input => {
        let timeout;
        input.addEventListener('input', function() {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                performSearch(this.value, this.dataset.search);
            }, 300);
        });
    });
}

function performSearch(query, target) {
    // This would typically make an AJAX request to filter results
    console.log(`Searching ${target} for: ${query}`);
}

// Candidates Page Functions
function initializeCandidatesPage() {
    initializeCandidateFilters();
    initializeBulkActions();
}

function initializeCandidateFilters() {
    const filterButtons = document.querySelectorAll('[data-filter]');
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            const filter = this.dataset.filter;
            applyCandidateFilter(filter);
        });
    });
}

function applyCandidateFilter(filter) {
    // Update URL with filter parameter
    const url = new URL(window.location);
    if (filter) {
        url.searchParams.set('status', filter);
    } else {
        url.searchParams.delete('status');
    }
    window.location.href = url.toString();
}

function initializeBulkActions() {
    const selectAllCheckbox = document.getElementById('select-all-candidates');
    const candidateCheckboxes = document.querySelectorAll('.candidate-checkbox');
    const bulkActionButton = document.getElementById('bulk-action-button');
    
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            candidateCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
            updateBulkActionButton();
        });
    }
    
    candidateCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateBulkActionButton);
    });
}

function updateBulkActionButton() {
    const selectedCheckboxes = document.querySelectorAll('.candidate-checkbox:checked');
    const bulkActionButton = document.getElementById('bulk-action-button');
    
    if (bulkActionButton) {
        if (selectedCheckboxes.length > 0) {
            bulkActionButton.style.display = 'inline-block';
            bulkActionButton.textContent = `Actions (${selectedCheckboxes.length})`;
        } else {
            bulkActionButton.style.display = 'none';
        }
    }
}

// Jobs Page Functions
function initializeJobsPage() {
    initializeJobFilters();
    initializeJobActions();
}

function initializeJobFilters() {
    const statusFilters = document.querySelectorAll('[data-job-status]');
    statusFilters.forEach(filter => {
        filter.addEventListener('click', function() {
            const status = this.dataset.jobStatus;
            filterJobsByStatus(status);
        });
    });
}

function filterJobsByStatus(status) {
    const rows = document.querySelectorAll('tbody tr');
    rows.forEach(row => {
        const statusBadge = row.querySelector('.badge');
        if (!status || statusBadge.textContent.toLowerCase().includes(status.toLowerCase())) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

function initializeJobActions() {
    const toggleButtons = document.querySelectorAll('[data-job-toggle]');
    toggleButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const jobId = this.dataset.jobToggle;
            toggleJobStatus(jobId, this);
        });
    });
}

function toggleJobStatus(jobId, button) {
    // Show loading state
    const originalText = button.innerHTML;
    button.innerHTML = '<i data-feather="loader" class="spin"></i>';
    button.disabled = true;
    
    // Make request to toggle job status
    fetch(`/jobs/${jobId}/toggle`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => {
        if (response.ok) {
            // Reload page to show updated status
            window.location.reload();
        } else {
            throw new Error('Failed to toggle job status');
        }
    })
    .catch(error => {
        console.error('Error toggling job status:', error);
        showNotification('Failed to update job status', 'error');
        
        // Restore button
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

// Notification System
function initializeNotifications() {
    // Check for new notifications every 60 seconds
    setInterval(checkForNotifications, 60000);
}

function checkForNotifications() {
    // This would typically check for new high-scoring matches or other important events
    fetch('/api/notifications')
        .then(response => response.json())
        .then(data => {
            if (data.notifications && data.notifications.length > 0) {
                data.notifications.forEach(notification => {
                    showNotification(notification.message, notification.type);
                });
            }
        })
        .catch(error => {
            console.error('Error checking notifications:', error);
        });
}

function showNotification(message, type = 'info', duration = 5000) {
    const alertClass = type === 'error' ? 'danger' : type;
    const alertHtml = `
        <div class="alert alert-${alertClass} alert-dismissible fade show notification-alert" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Find or create notification container
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        container.className = 'position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    // Add notification
    const alertElement = document.createElement('div');
    alertElement.innerHTML = alertHtml;
    container.appendChild(alertElement.firstElementChild);
    
    // Auto-dismiss after duration
    if (duration > 0) {
        setTimeout(() => {
            const alert = container.querySelector('.notification-alert');
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, duration);
    }
}

// Export Functions
function exportData() {
    const currentPage = window.location.pathname;
    let exportType = 'general';
    
    if (currentPage.includes('candidates')) {
        exportType = 'candidates';
    } else if (currentPage.includes('jobs')) {
        exportType = 'jobs';
    }
    
    showNotification('Preparing export...', 'info');
    
    // This would typically make a request to generate and download the export
    setTimeout(() => {
        showNotification('Export feature coming soon!', 'info');
    }, 1000);
}

// Utility Functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Error Handling
window.addEventListener('error', function(e) {
    console.error('JavaScript error:', e.error);
    showNotification('An unexpected error occurred', 'error');
});

// Cleanup
window.addEventListener('beforeunload', function() {
    if (dashboardRefreshInterval) {
        clearInterval(dashboardRefreshInterval);
    }
});

// Export for use in other scripts
window.RecruitmentApp = {
    showNotification,
    refreshDashboardStats,
    exportData,
    formatFileSize,
    debounce,
    throttle
};
