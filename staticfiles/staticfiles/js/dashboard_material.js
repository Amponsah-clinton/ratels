/* ============================================
   Material Dashboard Shadcn - Standalone JS
   ============================================ */

(function () {
    'use strict';

    // --- Sidebar ---
    const sidebar = document.getElementById('mdSidebar');
    const overlay = document.getElementById('mdSidebarOverlay');
    const desktopToggle = document.getElementById('mdSidebarToggle');
    const navbarToggle = document.getElementById('mdNavbarSidebarToggle');
    const hamburger = document.getElementById('mdHamburger');
    const isMobile = () => window.innerWidth < 1024;

    function applySidebarState() {
        if (isMobile()) {
            sidebar.classList.remove('collapsed');
            sidebar.classList.remove('mobile-open');
            overlay.classList.remove('active');
        } else {
            sidebar.classList.remove('mobile-open');
            overlay.classList.remove('active');
            const saved = localStorage.getItem('md-sidebar-collapsed');
            if (saved === 'true') {
                sidebar.classList.add('collapsed');
            } else {
                sidebar.classList.remove('collapsed');
            }
        }
    }

    function toggleDesktopSidebar() {
        if (sidebar.classList.contains('collapsed')) {
            sidebar.classList.remove('collapsed');
            localStorage.setItem('md-sidebar-collapsed', 'false');
        } else {
            sidebar.classList.add('collapsed');
            localStorage.setItem('md-sidebar-collapsed', 'true');
        }
    }

    function toggleMobileSidebar() {
        if (sidebar.classList.contains('mobile-open')) {
            sidebar.classList.remove('mobile-open');
            overlay.classList.remove('active');
        } else {
            sidebar.classList.add('mobile-open');
            overlay.classList.add('active');
        }
    }

    function closeMobileSidebar() {
        sidebar.classList.remove('mobile-open');
        overlay.classList.remove('active');
    }

    if (desktopToggle) {
        desktopToggle.addEventListener('click', function () {
            if (isMobile()) {
                toggleMobileSidebar();
            } else {
                toggleDesktopSidebar();
            }
        });
    }

    if (navbarToggle) {
        navbarToggle.addEventListener('click', function () {
            if (isMobile()) {
                toggleMobileSidebar();
            } else {
                toggleDesktopSidebar();
            }
        });
    }

    if (hamburger) {
        hamburger.addEventListener('click', toggleMobileSidebar);
    }

    if (overlay) {
        overlay.addEventListener('click', closeMobileSidebar);
    }

    // Close sidebar on mobile nav click
    var navItems = document.querySelectorAll('.md-nav-item');
    navItems.forEach(function (item) {
        item.addEventListener('click', function () {
            if (isMobile()) {
                closeMobileSidebar();
            }
        });
    });

    window.addEventListener('resize', applySidebarState);
    applySidebarState();

    // --- Account Dropdown ---
    const accountBtn = document.getElementById('mdAccountBtn');
    const accountDropdown = document.getElementById('mdAccountDropdown');

    if (accountBtn && accountDropdown) {
        accountBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            accountDropdown.classList.toggle('open');
        });

        document.addEventListener('click', function (e) {
            if (!accountDropdown.contains(e.target) && !accountBtn.contains(e.target)) {
                accountDropdown.classList.remove('open');
            }
        });
    }

    // --- Initialize Lucide Icons ---
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    // --- Chart.js: Dashboard Revenue Chart ---
    var dashRevenueCanvas = document.getElementById('mdDashboardRevenueChart');
    if (dashRevenueCanvas && typeof Chart !== 'undefined') {
        new Chart(dashRevenueCanvas, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Revenue',
                    data: [185000, 198000, 192000, 225000, 210000, 234567],
                    borderColor: 'rgb(66, 184, 131)',
                    backgroundColor: 'rgba(66, 184, 131, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: 'rgb(66, 184, 131)',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return 'Revenue: $' + (context.parsed.y / 1000).toFixed(0) + 'k';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (value) {
                                return '$' + (value / 1000).toFixed(0) + 'k';
                            }
                        },
                        grid: { color: 'rgba(0,0,0,0.05)' }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

    // --- Chart.js: Reports Revenue Chart ---
    var reportsRevenueCanvas = document.getElementById('mdReportsRevenueChart');
    if (reportsRevenueCanvas && typeof Chart !== 'undefined') {
        new Chart(reportsRevenueCanvas, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct'],
                datasets: [{
                    label: 'Revenue',
                    data: [185000, 198000, 192000, 225000, 210000, 245000, 235000, 260000, 280000, 295000],
                    borderColor: 'rgb(66, 184, 131)',
                    backgroundColor: 'rgba(66, 184, 131, 0.1)',
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: 'rgb(66, 184, 131)',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: function (value) {
                                return '$' + (value / 1000).toFixed(0) + 'k';
                            }
                        },
                        grid: { color: 'rgba(0,0,0,0.05)' }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

    // --- Chart.js: Reports Doughnut Chart ---
    var doughnutCanvas = document.getElementById('mdReportsDoughnutChart');
    if (doughnutCanvas && typeof Chart !== 'undefined') {
        new Chart(doughnutCanvas, {
            type: 'doughnut',
            data: {
                labels: ['Qualified', 'Proposal', 'Negotiation', 'Closed Won'],
                datasets: [{
                    data: [35, 25, 22, 18],
                    backgroundColor: [
                        'rgba(66, 184, 131, 0.9)',
                        'rgba(66, 184, 131, 0.7)',
                        'rgba(66, 184, 131, 0.5)',
                        'rgba(66, 184, 131, 0.3)'
                    ],
                    borderColor: [
                        'rgb(66, 184, 131)',
                        'rgb(66, 184, 131)',
                        'rgb(66, 184, 131)',
                        'rgb(66, 184, 131)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    // --- Navigation Group Toggle (Media Vault submenu) ---
    window.toggleNavGroup = function(button) {
        const group = button.closest('.md-nav-group');
        if (group) {
            group.classList.toggle('expanded');
            // Save state to localStorage
            const isExpanded = group.classList.contains('expanded');
            localStorage.setItem('md-nav-media-vault-expanded', isExpanded);
        }
    };

    // Restore nav group state on page load
    const mediaVaultGroup = document.querySelector('.md-nav-group');
    if (mediaVaultGroup) {
        const savedState = localStorage.getItem('md-nav-media-vault-expanded');
        // Check if we're on a media vault page (from Django template class)
        const isOnMediaPage = mediaVaultGroup.classList.contains('expanded');
        if (savedState === 'true' || isOnMediaPage) {
            mediaVaultGroup.classList.add('expanded');
        }
    }

    // Close sidebar on mobile when clicking submenu items
    var subItems = document.querySelectorAll('.md-nav-subitem');
    subItems.forEach(function (item) {
        item.addEventListener('click', function () {
            if (isMobile()) {
                closeMobileSidebar();
            }
        });
    });

})();
