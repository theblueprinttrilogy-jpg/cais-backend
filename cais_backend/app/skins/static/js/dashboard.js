/**
 * CAIS Code Compliance - Dashboard JavaScript
 * Version: 10.0
 */

(function() {
    'use strict';

    // ============================================================
    // DOM Ready
    // ============================================================
    document.addEventListener('DOMContentLoaded', function() {
        console.log('Dashboard initialized');

        // Initialize dashboard components
        initStats();
        initCharts();
        initActivityStream();
        initAutoRefresh();
    });

    // ============================================================
    // Stats
    // ============================================================
    function initStats() {
        const stats = document.querySelectorAll('.stat-value');
        stats.forEach(function(stat) {
            const target = parseInt(stat.dataset.target);
            if (target && !isNaN(target)) {
                animateNumber(stat, target);
            }
        });
    }

    /**
     * Animate number counting
     */
    function animateNumber(element, target) {
        const duration = 1000;
        const start = 0;
        const startTime = performance.now();

        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const current = Math.floor(progress * target);

            element.textContent = current;

            if (progress < 1) {
                requestAnimationFrame(update);
            } else {
                element.textContent = target;
            }
        }

        requestAnimationFrame(update);
    }

    // ============================================================
    // Charts
    // ============================================================
    function initCharts() {
        // Violation chart bars animation
        const bars = document.querySelectorAll('.chart-bar');
        bars.forEach(function(bar) {
            const targetWidth = bar.dataset.targetWidth;
            if (targetWidth) {
                setTimeout(function() {
                    bar.style.width = targetWidth + '%';
                }, 300);
            }
        });
    }

    // ============================================================
    // Activity Stream
    // ============================================================
    function initActivityStream() {
        const container = document.querySelector('.activity-list');
        if (!container) return;

        // Auto-scroll to new activities
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length > 0) {
                    const lastItem = container.lastElementChild;
                    if (lastItem) {
                        lastItem.scrollIntoView({ behavior: 'smooth', block: 'end' });
                    }
                }
            });
        });

        observer.observe(container, { childList: true });
    }

    // ============================================================
    // Auto Refresh
    // ============================================================
    function initAutoRefresh() {
        const refreshInterval = 30000; // 30 seconds
        const dashboardData = document.querySelector('.dashboard-container');

        if (!dashboardData) return;

        setInterval(function() {
            refreshDashboard();
        }, refreshInterval);
    }

    /**
     * Refresh dashboard data
     */
    function refreshDashboard() {
        fetch('/api/v1/dashboard/stats')
            .then(function(response) {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.json();
            })
            .then(function(data) {
                updateDashboard(data);
            })
            .catch(function(error) {
                console.warn('Dashboard refresh failed:', error);
            });
    }

    /**
     * Update dashboard with new data
     */
    function updateDashboard(data) {
        if (!data || !data.data) return;

        const stats = data.data;

        // Update stat values
        const statElements = document.querySelectorAll('.stat-value');
        statElements.forEach(function(el) {
            const key = el.dataset.key;
            if (key && stats[key] !== undefined) {
                animateNumber(el, stats[key]);
            }
        });

        // Update activity log
        if (stats.recent_activities) {
            const activityList = document.querySelector('.activity-list');
            if (activityList) {
                // Add new activities
                stats.recent_activities.forEach(function(activity) {
                    const item = document.createElement('div');
                    item.className = 'activity-item';
                    item.innerHTML = `
                        <span class="activity-time">${activity.time}</span>
                        <span class="activity-type ${activity.type}">${activity.type}</span>
                        <span class="activity-message">${activity.message}</span>
                    `;
                    activityList.appendChild(item);
                });
            }
        }
    }

    // ============================================================
    // Export functions for debugging
    // ============================================================
    window.CAIS_DASHBOARD = {
        refresh: refreshDashboard,
        update: updateDashboard
    };

})();
