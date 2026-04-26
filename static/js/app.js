/* ─── Sidebar toggle & mobile menu ─── */
document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.getElementById('sidebar');
    const mobileBtn = document.getElementById('mobileMenuBtn');

    if (mobileBtn && sidebar) {
        mobileBtn.addEventListener('click', () => sidebar.classList.toggle('open'));
        document.addEventListener('click', (e) => {
            if (sidebar.classList.contains('open') && !sidebar.contains(e.target) && e.target !== mobileBtn) {
                sidebar.classList.remove('open');
            }
        });
    }

    /* Auto-dismiss flash messages after 5s (except password messages) */
    document.querySelectorAll('[data-auto-dismiss]').forEach(el => {
        setTimeout(() => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(-10px)';
            setTimeout(() => el.remove(), 300);
        }, 5000);
    });

    /* Check for password in flash messages and show modal */
    document.querySelectorAll('.flash-password').forEach(flash => {
        const text = flash.querySelector('.flash-text').textContent;
        const match = text.match(/Temporary password:\s*(\S+)/i);
        if (match) {
            const password = match[1];
            const message = text.split('Temporary password:')[0].trim();
            showPasswordModal(message, password);
            // Remove the flash message since we're showing modal
            flash.remove();
        }
    });

    /* Drag-and-drop on upload zones */
    document.querySelectorAll('.upload-zone').forEach(zone => {
        const input = zone.querySelector('input[type="file"]');
        zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); });
        zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
        zone.addEventListener('drop', e => {
            e.preventDefault();
            zone.classList.remove('dragover');
            if (input && e.dataTransfer.files.length) {
                input.files = e.dataTransfer.files;
                zone.querySelector('.upload-text').textContent = e.dataTransfer.files[0].name;
            }
        });
        zone.addEventListener('click', () => { if (input) input.click(); });
        if (input) {
            input.addEventListener('change', () => {
                if (input.files.length) {
                    zone.querySelector('.upload-text').textContent = input.files[0].name;
                }
            });
        }
    });
});

/* ─── Password Modal Functions ─── */
function showPasswordModal(message, password) {
    const modal = document.getElementById('passwordModal');
    const modalMessage = document.getElementById('modalMessage');
    const modalPassword = document.getElementById('modalPassword');
    
    if (modal && modalMessage && modalPassword) {
        modalMessage.textContent = message;
        modalPassword.value = password;
        modal.style.display = 'flex';
        
        // Select the password text for easy copying
        modalPassword.select();
    }
}

function closePasswordModal() {
    const modal = document.getElementById('passwordModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function copyPasswordFromModal() {
    const passwordInput = document.getElementById('modalPassword');
    if (passwordInput) {
        passwordInput.select();
        document.execCommand('copy');
        
        // Show feedback
        const btn = event.target;
        const originalText = btn.textContent;
        btn.textContent = '✅ Copied!';
        btn.style.backgroundColor = '#10b981';
        
        setTimeout(() => {
            btn.textContent = originalText;
            btn.style.backgroundColor = '';
        }, 2000);
    }
}

function copyPasswordFromFlash(button) {
    const flashText = button.parentElement.querySelector('.flash-text').textContent;
    const match = flashText.match(/Temporary password:\s*(\S+)/i);
    
    if (match) {
        const password = match[1];
        
        // Create temporary input to copy
        const tempInput = document.createElement('input');
        tempInput.value = password;
        document.body.appendChild(tempInput);
        tempInput.select();
        document.execCommand('copy');
        document.body.removeChild(tempInput);
        
        // Show feedback
        const originalText = button.textContent;
        button.textContent = '✅ Copied!';
        button.style.backgroundColor = '#10b981';
        
        setTimeout(() => {
            button.textContent = originalText;
            button.style.backgroundColor = '';
        }, 2000);
    }
}

/* Close modal when clicking outside */
document.addEventListener('click', (e) => {
    const modal = document.getElementById('passwordModal');
    if (modal && e.target === modal) {
        // Don't allow closing by clicking outside - must click button
        // closePasswordModal();
    }
});
