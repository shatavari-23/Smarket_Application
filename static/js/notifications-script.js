async function updateNotificationCount() {
    try {
        const response = await fetch('/api/notifications');
        if (!response.ok) return;
        const notifications = await response.json();
        const unreadCount = notifications.filter(n => !n.is_read).length;

        const countElement = document.getElementById('notification-count');
        if (countElement) {
            countElement.textContent = unreadCount;
            countElement.style.display = unreadCount > 0 ? 'flex' : 'none'; // 'flex' to match CSS
        }
    } catch (error) {
        console.error("Error updating notification count:", error);
    }
}

async function markNotificationAsRead(notificationId) {
    await fetch(`/api/notifications/read/${notificationId}`, { method: 'POST' });
}

async function removeNotification(notificationId) {
    await fetch(`/api/notifications/delete/${notificationId}`, { method: 'POST' });
}

async function markAllNotificationsAsRead() {
    await fetch('/api/notifications/read/all', { method: 'POST' });
}

const socket = io.connect(location.protocol + '//' + location.hostname + ':' + location.port);

document.addEventListener('DOMContentLoaded', function () {

    // Initialize notifications on page load if on the notifications page
    if (window.location.pathname.includes('/notifications')) {
        fetchAllNotifications();
    }
    updateNotificationCount();

    // Setup event listeners for the notifications page
    setupNotificationEventListeners();

    // Periodically update all "time ago" timestamps
    setInterval(updateTimestamps, 60000); // Update every minute
});

async function fetchAllNotifications() {
    const container = document.querySelector('.notifications-list');
    if (!container) return;

    try {
        const response = await fetch('/api/notifications');
        const notifications = await response.json();

        container.innerHTML = '';
        if (notifications.length === 0) {
            container.innerHTML = '<div class="no-notifications"><p>No notifications yet.</p></div>';
        } else {
            notifications.forEach(notification => {
                const notificationElement = createNotificationElement(notification);
                container.appendChild(notificationElement);
            });
        }
    } catch (error) {
        console.error('Failed to fetch notifications:', error);
        container.innerHTML = '<div class="no-notifications"><p>Could not load notifications.</p></div>';
    }
}

function createNotificationElement(notification) {
    const notificationDiv = document.createElement('div');
    notificationDiv.className = `notification-item ${notification.is_read ? '' : 'unread'}`;
    notificationDiv.dataset.notificationId = notification.id;

    // Add redirect URL if it exists
    if (notification.redirect_url) {
        notificationDiv.dataset.redirectUrl = notification.redirect_url;
        notificationDiv.style.cursor = 'pointer';
    }

    const timeAgo = formatTimeAgo(new Date(notification.timestamp));

    // Get appropriate icon based on notification type
    const iconClass = getNotificationIcon(notification.type);

    notificationDiv.innerHTML = `
      <div class="notification-header">
        <div class="notification-icon">
            <i class="${iconClass}"></i>
        </div>
        <div class="notification-content">
            <h4>${notification.title}</h4>
            <p>${notification.message}</p>
            <span class="notification-time" data-timestamp="${notification.timestamp}">${timeAgo}</span>
        </div>
      </div>
      <div class="notification-actions">
          ${!notification.is_read ? '<button class="btn-mark-read">Mark as Read</button>' : ''}
          <button class="btn-remove-notification">Remove</button>
      </div>
    `;

    return notificationDiv;
}

function getNotificationIcon(type) {
    const icons = {
        'Product Sold!': 'fas fa-dollar-sign',
        'Low Stock Warning': 'fas fa-exclamation-triangle',
        'Product Approved!': 'fas fa-check-circle',
        'Product Update': 'fas fa-info-circle', // For rejection
        'New Arrival!': 'fas fa-tshirt',
        'New Seller Registered': 'fas fa-user-plus',
        'New Product for Approval': 'fas fa-inbox',
        'default': 'fas fa-bell',
    };
    return icons[type] || icons['default'];
}

function formatTimeAgo(date) {
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);

    if (diffInSeconds < 60) return 'Just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
    if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)} days ago`;
    return date.toLocaleDateString();
}

function updateTimestamps() {
    const timeElements = document.querySelectorAll('.notification-time');
    timeElements.forEach(element => {
        const timestamp = element.dataset.timestamp;
        if (timestamp) {
            element.textContent = formatTimeAgo(new Date(timestamp));
        }
    });
}
function setupNotificationEventListeners() {
    const notificationsContainer = document.querySelector('.notifications-list');

    if (!notificationsContainer) return;

    // Event delegation for notification actions
    notificationsContainer.addEventListener('click', async function (event) {
        const notificationItem = event.target.closest('.notification-item');
        if (!notificationItem) return;

        const notificationId = parseInt(notificationItem.dataset.notificationId);
        const redirectUrl = notificationItem.dataset.redirectUrl;

        // Handle main click for redirection
        if (redirectUrl && !event.target.closest('button')) {
            window.location.href = redirectUrl;
            return;
        }

        // Handle mark as read button
        if (event.target.classList.contains('btn-mark-read')) {
            await markNotificationAsRead(notificationId);
            event.target.style.display = 'none';
            notificationItem.classList.replace('unread', 'read');
            updateNotificationCount();
        }

        // Handle remove button
        if (event.target.classList.contains('btn-remove-notification')) {
            await removeNotification(notificationId);
            notificationItem.remove();
            if (document.querySelectorAll('.notification-item').length === 0) {
                fetchAllNotifications(); // Re-render if no notifications left
            }
            updateNotificationCount();
        }
    });

    // Handle load more button
    const loadMoreBtn = document.getElementById('load-more-btn');
    if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', function () {
            // For demo purposes, just show a message
            alert('Load more functionality would be implemented here for pagination.');
        });
    }

    // Handle mark all as read button (if you want to add one)
    const markAllReadBtn = document.getElementById('mark-all-read-btn');
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', async function () {
            try {
                await markAllNotificationsAsRead();
                await fetchAllNotifications(); // Re-fetch and render all notifications
                updateNotificationCount();
            } catch (error) {
                console.error("Failed to mark all as read:", error);
            }
        });
    }

    // Socket.IO listener for real-time notifications
    // This socket is now local to this script.
    // Ensure script.js also has its own socket instance.
    socket.on('new_notification', function (notification) {
        console.log('Received new notification on notifications page:', notification);

        // If on the notifications page, add it to the top of the list
        if (window.location.pathname.includes('/notifications')) {
            const container = document.querySelector('.notifications-list');
            if (container) {
                const notificationElement = createNotificationElement(notification);
                container.prepend(notificationElement);
            }
        }

        // Update the count badge everywhere
        updateNotificationCount();
    });
}
