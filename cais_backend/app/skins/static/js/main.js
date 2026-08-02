/**
 * CAIS Code Compliance - Main JavaScript
 * Version: 10.0
 */

(function() {
    'use strict';

    // ============================================================
    // DOM Ready
    // ============================================================
    document.addEventListener('DOMContentLoaded', function() {
        console.log('CAIS Code Compliance v10.0 loaded');

        // Initialize components
        initNavbar();
        initNotifications();
        initTooltips();
    });

    // ============================================================
    // Navbar
    // ============================================================
    function initNavbar() {
        const navbar = document.querySelector('.navbar');
        if (!navbar) return;

        // Mobile menu toggle
        const toggle = navbar.querySelector('.navbar-toggle');
        const menu = navbar.querySelector('.navbar-menu');

        if (toggle && menu) {
            toggle.addEventListener('click', function() {
                menu.classList.toggle('open');
                toggle.classList.toggle('active');
            });
        }

        // Close menu on outside click
        document.addEventListener('click', function(e) {
            if (menu && menu.classList.contains('open')) {
                if (!navbar.contains(e.target)) {
                    menu.classList.remove('open');
                    toggle.classList.remove('active');
                }
            }
        });
    }

    // ============================================================
    // Notifications
    // ============================================================
    function initNotifications() {
        const container = document.querySelector('.notification-container');
        if (!container) return;

        // Auto-dismiss notifications after 5 seconds
        const notifications = container.querySelectorAll('.notification');
        notifications.forEach(function(notification) {
            setTimeout(function() {
                notification.classList.add('fade-out');
                setTimeout(function() {
                    notification.remove();
                }, 300);
            }, 5000);
        });
    }

    // ============================================================
    // Tooltips
    // ============================================================
    function initTooltips() {
        const tooltips = document.querySelectorAll('[data-tooltip]');
        tooltips.forEach(function(element) {
            element.addEventListener('mouseenter', function(e) {
                const tooltip = document.createElement('div');
                tooltip.className = 'tooltip';
                tooltip.textContent = element.dataset.tooltip;
                document.body.appendChild(tooltip);

                const rect = element.getBoundingClientRect();
                tooltip.style.left = rect.left + rect.width / 2 - tooltip.offsetWidth / 2 + 'px';
                tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';
                tooltip.style.opacity = '1';
            });

            element.addEventListener('mouseleave', function() {
                const tooltip = document.querySelector('.tooltip');
                if (tooltip) {
                    tooltip.remove();
                }
            });
        });
    }

    // ============================================================
    // Utility Functions
    // ============================================================

    /**
     * Format a date string
     */
    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    /**
     * Truncate text with ellipsis
     */
    function truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    /**
     * Debounce function for performance
     */
    function debounce(func, wait) {
        let timeout;
        return function() {
            const context = this;
            const args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(function() {
                func.apply(context, args);
            }, wait);
        };
    }

    /**
     * Throttle function for performance
     */
    function throttle(func, limit) {
        let inThrottle;
        return function() {
            const context = this;
            const args = arguments;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(function() {
                    inThrottle = false;
                }, limit);
            }
        };
    }

    // ============================================================
    // Expose utilities globally
    // ============================================================
    window.CAIS = {
        version: '10.0',
        formatDate: formatDate,
        truncateText: truncateText,
        debounce: debounce,
        throttle: throttle
    };

})();
