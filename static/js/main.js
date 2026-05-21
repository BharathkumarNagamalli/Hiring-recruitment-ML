// ===================== TOAST =====================
function showToast(message, type = 'info') {
    const el = document.getElementById('toastEl');
    const body = document.getElementById('toastBody');
    if (!el || !body) return;

    body.textContent = message;
    el.className = 'toast align-items-center border-0 text-white';
    const bgMap = {
        success: 'bg-success',
        danger: 'bg-danger',
        warning: 'bg-warning text-dark',
        info: 'bg-info text-dark'
    };
    el.classList.add(bgMap[type] || 'bg-info');

    const toast = new bootstrap.Toast(el, {delay: 3500});
    toast.show();
}

// ===================== ACTIVE NAV =====================
document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;
    document.querySelectorAll('.navbar .nav-link').forEach(link => {
        link.classList.remove('active');
        const href = link.getAttribute('href');
        if (href === path || (path.startsWith(href) && href !== '/')) {
            link.classList.add('active');
        }
        if (path === '/' && href === '/') {
            link.classList.add('active');
        }
    });
});

// ===================== SCORE BAR ANIMATION =====================
function animateProgressBars() {
    document.querySelectorAll('.progress-bar').forEach(bar => {
        const width = bar.style.width;
        bar.style.width = '0%';
        setTimeout(() => {
            bar.style.transition = 'width 1s ease';
            bar.style.width = width;
        }, 100);
    });
}

document.addEventListener('DOMContentLoaded', animateProgressBars);

// ===================== CONFIRM BEFORE DOWNLOAD =====================
document.querySelectorAll('a[href*="download"]').forEach(link => {
    link.addEventListener('click', () => {
        showToast('Preparing CSV download...', 'info');
    });
});