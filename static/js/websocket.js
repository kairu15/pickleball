/**
 * PickleSphere WebSocket Client
 * 
 * Manage WebSocket connections for:
 * - Real-time notifications
 * - Live match scoring
 * - Court availability updates
 * 
 * Usage:
 *   // Connect to notifications
 *   PickleSphereWS.connectNotifications();
 * 
 *   // Connect to match scoring
 *   PickleSphereWS.connectMatchScore(matchId);
 * 
 *   // Connect to court availability
 *   PickleSphereWS.connectCourtAvailability();
 */
const PickleSphereWS = (function() {
    'use strict';

    // Store active connections
    const connections = {
        notifications: null,
        matchScore: null,
        courtAvailability: null,
    };

    // Reconnection settings
    const RECONNECT_DELAY = 3000; // 3 seconds
    const MAX_RECONNECT_ATTEMPTS = 10;
    let reconnectAttempts = {};

    // Callback storage
    const callbacks = {
        onNotification: [],
        onUnreadCount: [],
        onScoreUpdate: [],
        onMatchState: [],
        onCourtUpdate: [],
        onCourtAvailability: [],
        onError: [],
        onConnectionChange: [],
    };

    /**
     * Get the WebSocket protocol (ws:// or wss://)
     */
    function getProtocol() {
        return window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    }

    /**
     * Build WebSocket URL
     */
    function buildURL(path) {
        return `${getProtocol()}${window.location.host}${path}`;
    }

    /**
     * Trigger all callbacks for a given event type
     */
    function trigger(event, data) {
        if (callbacks[event]) {
            callbacks[event].forEach(function(cb) {
                try { cb(data); } catch(e) { console.error('WS callback error:', e); }
            });
        }
    }

    /**
     * Fire a connection change event
     */
    function fireConnectionChange(type, status) {
        trigger('onConnectionChange', { type: type, status: status });
    }

    /**
     * Attempt to reconnect a WebSocket connection
     */
    function attemptReconnect(type, connectFn) {
        if (!reconnectAttempts[type]) reconnectAttempts[type] = 0;
        reconnectAttempts[type]++;

        if (reconnectAttempts[type] > MAX_RECONNECT_ATTEMPTS) {
            console.warn(`WS [${type}]: Max reconnect attempts reached.`);
            fireConnectionChange(type, 'failed');
            return;
        }

        const delay = RECONNECT_DELAY * Math.min(reconnectAttempts[type], 5);
        // WS reconnecting silently

        setTimeout(function() {
            connectFn();
        }, delay);
    }

    /**
     * Create and setup a WebSocket connection
     */
    function createConnection(type, url, handlers) {
        // Close existing connection if any
        if (connections[type]) {
            try { connections[type].close(); } catch(e) {}
            connections[type] = null;
        }

        const ws = new WebSocket(url);
        connections[type] = ws;

        ws.onopen = function() {
            reconnectAttempts[type] = 0;
            fireConnectionChange(type, 'connected');
        };

        ws.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                if (handlers[data.type]) {
                    handlers[data.type](data);
                }
            } catch(e) {
                console.error(`WS [${type}]: Parse error`, e);
            }
        };

        ws.onclose = function(event) {
            connections[type] = null;
            fireConnectionChange(type, 'disconnected');

            // Don't reconnect on intentional close (4000+ codes)
            if (event.code < 4000) {
                attemptReconnect(type, function() {
                    createConnection(type, url, handlers);
                });
            }
        };

        ws.onerror = function(error) {
            console.error(`WS [${type}]: Error`, error);
            trigger('onError', { type: type, error: error });
        };

        return ws;
    }

    /**
     * Send data through a WebSocket connection
     */
    function send(type, data) {
        const ws = connections[type];
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(data));
            return true;
        }
        return false;
    }

    // ==================== PUBLIC API ====================

    return {
        // ==================== NOTIFICATIONS ====================

        /**
         * Connect to the real-time notification stream
         */
        connectNotifications: function() {
            const url = buildURL('/ws/notifications/');
            createConnection('notifications', url, {
                'notification': function(data) {
                    trigger('onNotification', data);
                    trigger('onUnreadCount', { count: data.unread_count || 0 });

                    // Update notification badge
                    const badge = document.querySelector('.notification-badge');
                    if (badge) {
                        if (data.unread_count > 0) {
                            badge.textContent = data.unread_count;
                            badge.style.display = '';
                        } else {
                            badge.style.display = 'none';
                        }
                    }

                    // Show a toast notification
                    showNotificationToast(data);
                },
                'unread_count': function(data) {
                    trigger('onUnreadCount', data);
                },
                'pong': function() {},
            });
        },

        /**
         * Register callback for new notifications
         */
        onNotification: function(callback) {
            callbacks.onNotification.push(callback);
        },

        /**
         * Register callback for unread count changes
         */
        onUnreadCount: function(callback) {
            callbacks.onUnreadCount.push(callback);
        },

        /**
         * Mark a notification as read via WebSocket
         */
        markAsRead: function(notificationId) {
            return send('notifications', {
                action: 'mark_read',
                notification_id: notificationId,
            });
        },

        /**
         * Mark all notifications as read
         */
        markAllAsRead: function() {
            return send('notifications', {
                action: 'mark_all_read',
            });
        },

        // ==================== MATCH SCORING ====================

        /**
         * Connect to a match's live scoring stream
         */
        connectMatchScore: function(matchId) {
            const url = buildURL(`/ws/match/${matchId}/score/`);
            createConnection('matchScore', url, {
                'match_state': function(data) {
                    trigger('onMatchState', data);
                },
                'score_update': function(data) {
                    trigger('onScoreUpdate', data);
                },
                'error': function(data) {
                    trigger('onError', data);
                },
                'pong': function() {},
            });
        },

        /**
         * Register callback for score updates
         */
        onScoreUpdate: function(callback) {
            callbacks.onScoreUpdate.push(callback);
        },

        /**
         * Register callback for initial match state
         */
        onMatchState: function(callback) {
            callbacks.onMatchState.push(callback);
        },

        /**
         * Update match score (team scores via the current game)
         */
        updateScore: function(team1Score, team2Score, status) {
            return send('matchScore', {
                action: 'update_score',
                team1_score: team1Score,
                team2_score: team2Score,
                status: status,
            });
        },

        /**
         * Request current match state
         */
        requestMatchState: function() {
            return send('matchScore', {
                action: 'get_state',
            });
        },

        // ==================== COURT AVAILABILITY ====================

        /**
         * Connect to the system-wide court availability stream
         */
        connectCourtAvailability: function() {
            const url = buildURL('/ws/courts/availability/');
            createConnection('courtAvailability', url, {
                'courts_availability': function(data) {
                    trigger('onCourtAvailability', data);
                },
                'court_update': function(data) {
                    trigger('onCourtUpdate', data);
                },
                'pong': function() {},
            });
        },

        /**
         * Register callback for court availability data
         */
        onCourtAvailability: function(callback) {
            callbacks.onCourtAvailability.push(callback);
        },

        /**
         * Register callback for individual court updates
         */
        onCourtUpdate: function(callback) {
            callbacks.onCourtUpdate.push(callback);
        },

        /**
         * Refresh court availability data
         */
        refreshCourts: function() {
            return send('courtAvailability', {
                action: 'refresh',
            });
        },

        // ==================== GENERAL ====================

        /**
         * Register a connection status change callback
         */
        onConnectionChange: function(callback) {
            callbacks.onConnectionChange.push(callback);
        },

        /**
         * Register an error callback
         */
        onError: function(callback) {
            callbacks.onError.push(callback);
        },

        /**
         * Disconnect all WebSocket connections
         */
        disconnectAll: function() {
            Object.keys(connections).forEach(function(type) {
                if (connections[type]) {
                    try { connections[type].close(4000); } catch(e) {}
                    connections[type] = null;
                }
            });
        },

        /**
         * Check if a connection type is open
         */
        isConnected: function(type) {
            return connections[type] && connections[type].readyState === WebSocket.OPEN;
        },
    };
})();

/**
 * Show a toast notification for incoming WebSocket notifications
 */
function showNotificationToast(data) {
    // Find the toast container
    let container = document.getElementById('wsToastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'wsToastContainer';
        container.className = 'floating-toast-container';
        container.style.cssText = 'top: 80px !important;';
        document.body.appendChild(container);
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.className = 'floating-toast';
    toast.style.cssText = 'animation: slideInRight 0.3s ease;';
    toast.setAttribute('role', 'alert');

    const typeColors = {
        'success': '#28a745',
        'error': '#dc3545',
        'warning': '#ffc107',
        'info': '#17a2b8',
    };

    const typeIcons = {
        'success': 'fa-check-circle',
        'error': 'fa-exclamation-circle',
        'warning': 'fa-exclamation-triangle',
        'info': 'fa-info-circle',
    };

    const color = typeColors[data.notification_type] || '#17a2b8';
    const icon = typeIcons[data.notification_type] || 'fa-info-circle';

    toast.innerHTML = `
        <div class="floating-toast-icon" style="color: ${color};">
            <i class="fas ${icon}"></i>
        </div>
        <div class="floating-toast-content">
            <strong>${escapeHtml(data.title || 'Notification')}</strong><br>
            <small>${escapeHtml(data.message || '')}</small>
        </div>
        <button type="button" class="floating-toast-close" onclick="this.closest('.floating-toast').remove()">
            <i class="fas fa-times"></i>
        </button>
    `;

    container.appendChild(toast);

    // Auto-dismiss after 5 seconds
    setTimeout(function() {
        if (toast.parentElement) {
            toast.classList.add('hiding');
            setTimeout(function() { toast.remove(); }, 300);
        }
    }, 5000);
}

/**
 * Simple HTML escape helper
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Auto-initialize notification WebSocket connection when DOM is ready
// Safe: the script only loads for authenticated users via {% if user.is_authenticated %} in base.html
// The NotificationConsumer rejects unauthenticated connections with code 4001 (no reconnect)
document.addEventListener('DOMContentLoaded', function() {
    PickleSphereWS.connectNotifications();
});
