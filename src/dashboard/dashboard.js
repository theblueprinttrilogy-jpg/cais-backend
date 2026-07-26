// ============================================
// CAIS SOVEREIGN DASHBOARD - MASTER SCRIPT
// M&A Level Dashboard
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    'use strict';

    // ---------- Chart.js Configuration ----------
    const ctx = document.getElementById('trendChart');
    if (ctx) {
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [
                    {
                        label: 'Compliance Rate (%)',
                        data: [94, 96, 95, 97, 98, 97, 99],
                        borderColor: '#D4A84A',
                        backgroundColor: 'rgba(212, 168, 74, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: '#D4A84A',
                    },
                    {
                        label: 'Revenue ($B)',
                        data: [10.2, 10.8, 11.1, 11.5, 11.8, 12.0, 12.4],
                        borderColor: '#4A8AD4',
                        backgroundColor: 'rgba(74, 138, 212, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: '#4A8AD4',
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: '#8A9AB0',
                            font: {
                                family: "'Inter', sans-serif",
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(10, 22, 40, 0.9)',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1,
                        titleColor: '#F0F4F8',
                        bodyColor: '#8A9AB0',
                        cornerRadius: 8,
                        padding: 12
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255,255,255,0.03)'
                        },
                        ticks: {
                            color: '#8A9AB0'
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(255,255,255,0.03)'
                        },
                        ticks: {
                            color: '#8A9AB0'
                        }
                    }
                }
            }
        });

        // Time button switching
        document.querySelectorAll('.time-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                // Update chart data here...
            });
        });
    }

    // ---------- Block Hover Effects ----------
    document.querySelectorAll('.block').forEach(block => {
        block.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.15)';
            this.style.borderColor = '#D4A84A';
        });
        block.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
            this.style.borderColor = '';
        });
    });

    // ---------- KPI Card Click ----------
    document.querySelectorAll('.kpi-card').forEach(card => {
        card.addEventListener('click', function() {
            this.style.transform = 'scale(0.98)';
            setTimeout(() => {
                this.style.transform = '';
            }, 200);
        });
    });

    // ---------- Action Buttons ----------
    document.querySelectorAll('.action-btn').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const icon = this.querySelector('i');
            if (icon) {
                icon.classList.remove('fa-play', 'fa-download', 'fa-redo');
                icon.classList.add('fa-spinner', 'fa-spin');
                setTimeout(() => {
                    icon.classList.remove('fa-spinner', 'fa-spin');
                    icon.classList.add('fa-check');
                    setTimeout(() => {
                        icon.classList.remove('fa-check');
                        icon.classList.add('fa-play');
                    }, 2000);
                }, 1500);
            }
        });
    });

    // ---------- Notification Badge ----------
    document.querySelector('.notification-badge')?.addEventListener('click', function() {
        const badge = this.querySelector('.badge');
        if (badge) {
            badge.style.transform = 'scale(1.5)';
            badge.style.opacity = '0';
            setTimeout(() => {
                badge.textContent = '0';
                badge.style.transform = 'scale(1)';
                badge.style.opacity = '1';
            }, 300);
        }
    });

    // ---------- Settings Button ----------
    document.querySelector('.settings-btn')?.addEventListener('click', function() {
        this.style.transform = 'rotate(180deg)';
        setTimeout(() => {
            this.style.transform = '';
        }, 500);
    });

    // ---------- User Profile ----------
    document.querySelector('.user-profile')?.addEventListener('click', function() {
        // Show user menu (can be expanded)
        console.log('User menu opened');
    });

    // ---------- Real-time Updates ----------
    function updateMetrics() {
        // Simulate real-time updates
        const kpiValues = document.querySelectorAll('.kpi-value');
        kpiValues.forEach(el => {
            const current = parseFloat(el.textContent.replace(/[$,%]/g, ''));
            if (!isNaN(current)) {
                const change = (Math.random() - 0.5) * 0.5;
                const newValue = (current + change);
                if (el.textContent.includes('%')) {
                    el.textContent = newValue.toFixed(1) + '%';
                } else if (el.textContent.includes('$')) {
                    el.textContent = '$' + newValue.toFixed(1) + 'B';
                }
            }
        });
    }

    // Update every 10 seconds
    setInterval(updateMetrics, 10000);

    // ---------- Console Branding ----------
    console.log('%c CAIS Sovereign Dashboard ',
        'background: linear-gradient(135deg, #0A1628, #1A2A4A); color: #D4A84A; font-size: 20px; font-weight: bold; padding: 10px 20px; border-radius: 4px;'
    );
    console.log('%c M&A Level Dashboard v1.0 ',
        'background: #1A2A4A; color: #8A9AB0; font-size: 14px; padding: 4px 12px; border-radius: 4px;'
    );

    console.log('🔍 System Status: Operational');
    console.log('📊 Agents: 4 Active');
    console.log('🔗 WORM Chain: Valid (4 blocks)');
    console.log('✅ All systems nominal');

    // ---------- Export Dashboard Data ----------
    window.exportDashboardData = function() {
        const data = {
            timestamp: new Date().toISOString(),
            metrics: {
                totalValue: '$12.4B',
                complianceRate: '98.7%',
                documents: '2.4K',
                uptime: '99.99%'
            },
            agents: [
                { name: 'PlanInspector', status: 'Active', accuracy: '92%' },
                { name: 'CodeMatcher', status: 'Active', accuracy: '87%' },
                { name: 'ComparatorEngine', status: 'Active', accuracy: '94%' },
                { name: 'DesignerAgent', status: 'Idle', accuracy: 'Ready' }
            ],
            wormChain: {
                blocks: 4,
                integrity: 'Valid',
                breaks: 0
            }
        };
        console.log('📊 Dashboard Data:', data);
        return data;
    };

    console.log('💡 Use window.exportDashboardData() to export current metrics');
});