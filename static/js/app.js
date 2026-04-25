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

    /* Auto-dismiss flash messages after 5s */
    document.querySelectorAll('[data-auto-dismiss]').forEach(el => {
        setTimeout(() => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(-10px)';
            setTimeout(() => el.remove(), 300);
        }, 5000);
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
