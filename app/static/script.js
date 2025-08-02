// Dashboard JavaScript Functionality

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all interactive features
    initializeNavigation();
    initializeToggleSwitches();
    initializeThemeToggle();
    initializeSearch();
    initializeNotifications();
    initializeFormHandlers();
    initializeAnimations();
});

// Navigation functionality
function initializeNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all nav items
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });
            
            // Add active class to clicked item
            this.parentElement.classList.add('active');
            
            // Add click animation
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = 'scale(1)';
            }, 150);
        });
    });
}

// Toggle switches functionality
function initializeToggleSwitches() {
    const toggleSwitches = document.querySelectorAll('.toggle-switch');
    
    toggleSwitches.forEach(toggle => {
        toggle.addEventListener('click', function() {
            this.classList.toggle('active');
            
            // Add click animation
            const slider = this.querySelector('.toggle-slider');
            slider.style.transform = this.classList.contains('active') 
                ? 'translateX(24px) scale(1.1)' 
                : 'translateX(0) scale(1.1)';
            
            setTimeout(() => {
                slider.style.transform = this.classList.contains('active') 
                    ? 'translateX(24px)' 
                    : 'translateX(0)';
            }, 150);
            
            // Handle specific toggle actions
            const settingItem = this.closest('.setting-item');
            const settingName = settingItem.querySelector('span').textContent;
            
            switch(settingName) {
                case 'Dark Mode':
                    toggleDarkMode(this.classList.contains('active'));
                    break;
                case 'Notification':
                    toggleNotifications(this.classList.contains('active'));
                    break;
                default:
                    console.log(`${settingName} toggled:`, this.classList.contains('active'));
            }
        });
    });
}

// Theme toggle functionality
function initializeThemeToggle() {
    const themeToggle = document.querySelector('.theme-toggle');
    const darkModeToggle = document.querySelector('.setting-item:has(span:contains("Dark Mode")) .toggle-switch');
    
    themeToggle.addEventListener('click', function() {
        const isDarkMode = document.body.classList.contains('dark-mode');
        toggleDarkMode(!isDarkMode);
        
        // Update the dark mode toggle switch
        if (darkModeToggle) {
            if (!isDarkMode) {
                darkModeToggle.classList.add('active');
            } else {
                darkModeToggle.classList.remove('active');
            }
        }
    });
}

// Dark mode functionality
function toggleDarkMode(enable) {
    if (enable) {
        document.body.classList.add('dark-mode');
        localStorage.setItem('darkMode', 'enabled');
    } else {
        document.body.classList.remove('dark-mode');
        localStorage.setItem('darkMode', 'disabled');
    }
}

// Load saved theme preference
function loadThemePreference() {
    const darkMode = localStorage.getItem('darkMode');
    if (darkMode === 'enabled') {
        document.body.classList.add('dark-mode');
        const darkModeToggle = document.querySelector('.setting-item:has(span:contains("Dark Mode")) .toggle-switch');
        if (darkModeToggle) {
            darkModeToggle.classList.add('active');
        }
    }
}

// Search functionality
function initializeSearch() {
    const searchInput = document.querySelector('.search-input');
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        
        // Add search animation
        this.style.transform = 'scale(1.02)';
        setTimeout(() => {
            this.style.transform = 'scale(1)';
        }, 200);
        
        // Simulate search functionality
        if (searchTerm.length > 2) {
            console.log('Searching for:', searchTerm);
            // Here you would implement actual search logic
        }
    });
    
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            performSearch(this.value);
        }
    });
}

// Perform search
function performSearch(query) {
    if (query.trim() === '') return;
    
    console.log('Performing search for:', query);
    
    // Add visual feedback
    const searchContainer = document.querySelector('.search-container');
    searchContainer.style.transform = 'scale(1.05)';
    setTimeout(() => {
        searchContainer.style.transform = 'scale(1)';
    }, 200);
    
    // Here you would implement actual search results
    showNotification(`Searching for "${query}"...`, 'info');
}

// Notification functionality
function initializeNotifications() {
    const notificationIcon = document.querySelector('.notification-icon');
    
    notificationIcon.addEventListener('click', function() {
        // Add click animation
        this.style.transform = 'scale(1.2)';
        setTimeout(() => {
            this.style.transform = 'scale(1)';
        }, 150);
        
        showNotificationPanel();
    });
}

// Show notification panel
function showNotificationPanel() {
    // Create notification panel if it doesn't exist
    let panel = document.querySelector('.notification-panel');
    
    if (!panel) {
        panel = document.createElement('div');
        panel.className = 'notification-panel';
        panel.innerHTML = `
            <div class="notification-header">
                <h3>Notifications</h3>
                <button class="close-panel">&times;</button>
            </div>
            <div class="notification-list">
                <div class="notification-item">
                    <i class="fas fa-dumbbell"></i>
                    <div class="notification-content">
                        <h4>Workout Reminder</h4>
                        <p>Time for your evening workout session</p>
                        <span class="notification-time">5 min ago</span>
                    </div>
                </div>
                <div class="notification-item">
                    <i class="fas fa-trophy"></i>
                    <div class="notification-content">
                        <h4>Goal Achieved!</h4>
                        <p>You've completed your weekly fitness goal</p>
                        <span class="notification-time">1 hour ago</span>
                    </div>
                </div>
                <div class="notification-item">
                    <i class="fas fa-apple-alt"></i>
                    <div class="notification-content">
                        <h4>Meal Plan Updated</h4>
                        <p>Your nutrition plan has been updated</p>
                        <span class="notification-time">2 hours ago</span>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(panel);
        
        // Add close functionality
        panel.querySelector('.close-panel').addEventListener('click', function() {
            panel.remove();
        });
        
        // Close when clicking outside
        panel.addEventListener('click', function(e) {
            if (e.target === panel) {
                panel.remove();
            }
        });
    }
    
    // Animate panel appearance
    panel.style.opacity = '0';
    panel.style.transform = 'translateY(-20px)';
    setTimeout(() => {
        panel.style.opacity = '1';
        panel.style.transform = 'translateY(0)';
    }, 10);
}

// Form handlers
function initializeFormHandlers() {
    // Newsletter subscription
    const subscribeBtn = document.querySelector('.subscribe-btn');
    const emailInput = document.querySelector('.email-input');
    
    if (subscribeBtn && emailInput) {
        subscribeBtn.addEventListener('click', function() {
            const email = emailInput.value.trim();
            
            if (email && isValidEmail(email)) {
                // Add success animation
                this.style.transform = 'scale(1.1)';
                this.textContent = 'Subscribed!';
                this.style.background = '#059669';
                
                setTimeout(() => {
                    this.style.transform = 'scale(1)';
                    this.textContent = 'Subscribe';
                    this.style.background = '#10b981';
                    emailInput.value = '';
                }, 2000);
                
                showNotification('Successfully subscribed to newsletter!', 'success');
            } else {
                showNotification('Please enter a valid email address', 'error');
                emailInput.focus();
            }
        });
        
        emailInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                subscribeBtn.click();
            }
        });
    }
    
    // Logout button
    const logoutBtn = document.querySelector('.logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function() {
            if (confirm('Are you sure you want to log out?')) {
                // Add logout animation
                this.style.transform = 'scale(1.1)';
                this.textContent = 'Logging out...';
                
                setTimeout(() => {
                    showNotification('Logged out successfully', 'info');
                    // Here you would redirect to login page
                }, 1000);
            }
        });
    }
    
    // Upgrade button
    const upgradeBtn = document.querySelector('.upgrade-btn');
    if (upgradeBtn) {
        upgradeBtn.addEventListener('click', function() {
            // Add upgrade animation
            this.style.transform = 'scale(1.1)';
            setTimeout(() => {
                this.style.transform = 'scale(1)';
            }, 150);
            
            showNotification('Redirecting to premium plans...', 'info');
            // Here you would redirect to upgrade page
        });
    }
}

// Animation initialization
function initializeAnimations() {
    // Intersection Observer for scroll animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    // Observe all cards
    const cards = document.querySelectorAll('.user-info-card, .newsletter-card, .account-section, .weight-tracking, .settings-section, .music-provider, .fitness-star');
    cards.forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(30px)';
        card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(card);
    });
    
    // Stagger animation for weight entries
    const weightEntries = document.querySelectorAll('.weight-entry');
    weightEntries.forEach((entry, index) => {
        entry.style.opacity = '0';
        entry.style.transform = 'translateX(-20px)';
        entry.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
        
        setTimeout(() => {
            entry.style.opacity = '1';
            entry.style.transform = 'translateX(0)';
        }, index * 100);
    });
}

// Utility functions
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `toast-notification ${type}`;
    notification.innerHTML = `
        <div class="toast-content">
            <i class="fas ${getNotificationIcon(type)}"></i>
            <span>${message}</span>
        </div>
        <button class="toast-close">&times;</button>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        removeNotification(notification);
    }, 3000);
    
    // Manual close
    notification.querySelector('.toast-close').addEventListener('click', () => {
        removeNotification(notification);
    });
}

function removeNotification(notification) {
    notification.classList.remove('show');
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 300);
}

function getNotificationIcon(type) {
    switch(type) {
        case 'success': return 'fa-check-circle';
        case 'error': return 'fa-exclamation-circle';
        case 'warning': return 'fa-exclamation-triangle';
        default: return 'fa-info-circle';
    }
}

function toggleNotifications(enabled) {
    if (enabled) {
        showNotification('Notifications enabled', 'success');
    } else {
        showNotification('Notifications disabled', 'info');
    }
}

// Weight tracking functionality
function addWeightEntry(weight, date = new Date()) {
    const weightEntries = document.querySelector('.weight-entries');
    const lastEntry = weightEntries.querySelector('.weight-entry');
    const lastWeight = lastEntry ? parseFloat(lastEntry.querySelector('.weight').textContent) : 0;
    const change = weight - lastWeight;
    
    const entry = document.createElement('div');
    entry.className = 'weight-entry';
    entry.innerHTML = `
        <div class="entry-info">
            <span class="date">${formatDate(date)}</span>
            <span class="weight">${weight} kg</span>
        </div>
        <div class="entry-change ${change >= 0 ? 'positive' : 'negative'}">
            <span class="time">${formatTime(date)}</span>
            <span class="change">${change >= 0 ? '+' : ''}${change.toFixed(1)} kg</span>
            <i class="fas fa-arrow-${change >= 0 ? 'up' : 'down'}"></i>
        </div>
    `;
    
    weightEntries.insertBefore(entry, weightEntries.firstChild);
    
    // Animate new entry
    entry.style.opacity = '0';
    entry.style.transform = 'translateY(-20px)';
    setTimeout(() => {
        entry.style.opacity = '1';
        entry.style.transform = 'translateY(0)';
    }, 10);
}

function formatDate(date) {
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    if (date.toDateString() === today.toDateString()) {
        return 'Today';
    } else if (date.toDateString() === yesterday.toDateString()) {
        return 'Yesterday';
    } else {
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric' 
        });
    }
}

function formatTime(date) {
    return date.toLocaleTimeString('en-US', { 
        hour: 'numeric', 
        minute: '2-digit',
        hour12: false 
    });
}

// Load theme preference on page load
loadThemePreference();

// Add smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add keyboard navigation support
document.addEventListener('keydown', function(e) {
    // ESC key to close panels
    if (e.key === 'Escape') {
        const panel = document.querySelector('.notification-panel');
        if (panel) {
            panel.remove();
        }
    }
    
    // Ctrl/Cmd + K for search focus
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.querySelector('.search-input');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }
});

// Add resize handler for responsive behavior
window.addEventListener('resize', function() {
    // Handle responsive navigation
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    
    if (window.innerWidth <= 768) {
        sidebar.style.position = 'relative';
        sidebar.style.width = '100%';
        mainContent.style.marginLeft = '0';
    } else {
        sidebar.style.position = 'fixed';
        sidebar.style.width = '280px';
        mainContent.style.marginLeft = '280px';
    }
});

// Initialize responsive behavior on load
window.dispatchEvent(new Event('resize'));

