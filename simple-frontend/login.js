// Login page functionality
document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    const loginBtn = document.querySelector('.login-btn');
    
    // Check if user is already logged in
    const userData = localStorage.getItem('fallDetectionUser');
    if (userData) {
        // Auto-redirect if already logged in
        setTimeout(() => {
            window.location.href = 'index.html';
        }, 1000);
        return;
    }
    
    // Handle form submission
    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(loginForm);
        const username = formData.get('username').trim();
        const phone = formData.get('phone').trim();
        const camera = formData.get('camera');
        const darkMode = formData.get('darkMode') === 'on';
        
        // Validate inputs
        if (!username || username.length < 2) {
            showError('Please enter a valid name (at least 2 characters)');
            return;
        }
        
        // Validate Indian phone number (10 digits, starting with 6-9)
        const cleanPhone = phone.replace(/\D/g, ''); // Remove any non-digits
        console.log('Phone validation:', { original: phone, cleaned: cleanPhone, length: cleanPhone.length });
        
        const phoneRegex = /^[6-9][0-9]{9}$/;
        if (!cleanPhone || cleanPhone.length !== 10) {
            showError('Please enter exactly 10 digits for your mobile number');
            return;
        }
        
        if (!phoneRegex.test(cleanPhone)) {
            showError('Mobile number must start with 6, 7, 8, or 9');
            return;
        }
        
        // Show loading state
        loginBtn.classList.add('loading');
        loginBtn.textContent = 'Logging in...';
        
        // Save user data
        const userData = {
            username: username,
            phone: phone,
            camera: camera,
            darkMode: darkMode,
            loginTime: new Date().toISOString()
        };
        
        localStorage.setItem('fallDetectionUser', JSON.stringify(userData));
        
        // Simulate login process
        setTimeout(() => {
            showSuccess('Login successful! Redirecting...');
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 1500);
        }, 1000);
    });
    
    // Indian phone number formatting and validation
    const phoneInput = document.getElementById('phone');
    phoneInput.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, ''); // Remove non-digits
        
        // Limit to 10 digits
        if (value.length > 10) {
            value = value.slice(0, 10);
        }
        
        // Don't format with spaces - keep it as plain 10 digits for better UX
        e.target.value = value;
        
        // Real-time validation feedback
        const cleanValue = value.replace(/\s/g, '');
        const isValidLength = cleanValue.length === 10;
        const isValidStart = /^[6-9]/.test(cleanValue);
        const isValid = isValidLength && isValidStart && /^[6-9][0-9]{9}$/.test(cleanValue);
        
        if (cleanValue.length > 0) {
            if (isValid) {
                phoneInput.style.borderColor = '#48bb78';
                phoneInput.style.boxShadow = '0 0 0 3px rgba(72, 187, 120, 0.1)';
            } else {
                phoneInput.style.borderColor = '#f56565';
                phoneInput.style.boxShadow = '0 0 0 3px rgba(245, 101, 101, 0.1)';
            }
        } else {
            phoneInput.style.borderColor = '#e2e8f0';
            phoneInput.style.boxShadow = 'none';
        }
    });
    
    // Dark mode preview
    const darkModeCheckbox = document.getElementById('darkMode');
    darkModeCheckbox.addEventListener('change', function() {
        if (this.checked) {
            document.body.style.background = 'linear-gradient(135deg, #2d3748 0%, #1a202c 100%)';
            document.querySelector('.login-card').style.background = 'rgba(45, 55, 72, 0.95)';
            document.querySelector('.login-card').style.color = 'white';
        } else {
            document.body.style.background = 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)';
            document.querySelector('.login-card').style.background = 'rgba(255, 255, 255, 0.95)';
            document.querySelector('.login-card').style.color = '#4a5568';
        }
    });
});

// Utility functions
function showError(message) {
    showNotification(message, 'error');
}

function showSuccess(message) {
    showNotification(message, 'success');
}

function showNotification(message, type) {
    // Remove existing notifications
    const existing = document.querySelector('.notification');
    if (existing) {
        existing.remove();
    }
    
    // Create notification
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-icon">${type === 'error' ? '❌' : '✅'}</span>
            <span class="notification-message">${message}</span>
        </div>
    `;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'error' ? '#fed7d7' : '#c6f6d5'};
        color: ${type === 'error' ? '#c53030' : '#2f855a'};
        padding: 15px 20px;
        border-radius: 10px;
        border: 2px solid ${type === 'error' ? '#f56565' : '#48bb78'};
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        z-index: 1000;
        animation: slideInRight 0.3s ease;
        max-width: 300px;
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }
    }, 3000);
}

// Add CSS animations for notifications
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(100%);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes slideOutRight {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100%);
        }
    }
    
    .notification-content {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .notification-icon {
        font-size: 1.2em;
    }
    
    .notification-message {
        font-weight: 500;
    }
`;
document.head.appendChild(style);