// SECURITY: Prevent double form submission and add basic CSRF token check (if token present)
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Prevent double submit
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                if (submitButton.disabled) {
                    e.preventDefault();
                    return false;
                }
                submitButton.classList.add('loading');
                submitButton.disabled = true;
            }
            // CSRF token check (if present)
            const csrf = form.querySelector('input[name="csrf_token"]');
            if (csrf && !csrf.value) {
                e.preventDefault();
                alert('Security check failed: missing CSRF token.');
                return false;
            }
        });
    });
});
// (Removed duplicate) Form submission loading state is handled in the security block above.

// File upload preview
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('screenshot');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const preview = document.createElement('img');
                    preview.src = e.target.result;
                    preview.style.maxWidth = '100%';
                    preview.style.marginTop = '10px';
                    
                    const previewContainer = document.getElementById('preview');
                    if (previewContainer) {
                    // Prevent XSS: Remove any existing children safely
                    while (previewContainer.firstChild) {
                        previewContainer.removeChild(previewContainer.firstChild);
                    }
                    // Only append the image element, never use innerHTML with user data
                    previewContainer.appendChild(preview);
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    }
});

// Dynamic interest calculation (by days)
document.addEventListener('DOMContentLoaded', function() {
    const amountInput = document.getElementById('amount');
    const durationDaysInput = document.getElementById('duration_days');
    const interestRateSpan = document.getElementById('interestRate');
    const expectedReturnSpan = document.getElementById('expectedReturn');

    function calculateReturn() {
        if (amountInput && durationDaysInput && interestRateSpan && expectedReturnSpan) {
            const P = parseFloat(amountInput.value) || 0;
            const T = parseFloat(durationDaysInput.value) || 0; // Use raw duration as T
            const R = parseFloat(interestRateSpan.textContent) || 0;
            // Simple interest: Interest = (P * R * T) / 100
            const interest = (P * R * T) / 100;
            expectedReturnSpan.textContent = interest.toFixed(2);
        }
    }

    if (amountInput && durationDaysInput) {
        amountInput.addEventListener('input', calculateReturn);
        durationDaysInput.addEventListener('input', calculateReturn);
    }
});

// Filter form date validation
document.addEventListener('DOMContentLoaded', function() {
    const startDate = document.getElementById('start_date');
    const endDate = document.getElementById('end_date');
    
    if (startDate && endDate) {
        startDate.addEventListener('change', function() {
            endDate.min = startDate.value;
        });
        
        endDate.addEventListener('change', function() {
            startDate.max = endDate.value;
        });
    }
});
