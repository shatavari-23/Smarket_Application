document.addEventListener('DOMContentLoaded', function () {
    if (window.location.pathname.includes('/chat-histories')) {
        fetchChatHistories();
    }
});

async function fetchChatHistories() {
    const container = document.querySelector('.chat-histories-list');
    if (!container) return;

    try {
        const response = await fetch('/api/conversations');
        const conversations = await response.json();

        container.innerHTML = '';
        if (conversations.length === 0) {
            container.innerHTML = '<div class="no-chat-histories"><p>No chat histories yet.</p></div>';
        } else {
            conversations.forEach(conversation => {
                const conversationElement = createChatHistoryElement(conversation);
                container.appendChild(conversationElement);
            });
        }
    } catch (error) {
        console.error('Failed to fetch chat histories:', error);
        container.innerHTML = '<div class="no-chat-histories"><p>Could not load chat histories.</p></div>';
    }
}

function createChatHistoryElement(conversation) {
    const conversationDiv = document.createElement('div');
    conversationDiv.className = 'chat-history-item';
    conversationDiv.dataset.conversationId = conversation.id;

    const lastMessage = conversation.last_message_content || 'No messages yet.';
    const timestamp = conversation.last_message_timestamp ? formatTimeAgo(new Date(conversation.last_message_timestamp)) : '';

    conversationDiv.innerHTML = `
        <div class="chat-history-info" onclick="window.location.href='/chat/${conversation.id}'">
            <strong>${conversation.other_user_name}</strong> - ${conversation.product_name}<br>
            <small>${lastMessage} ${timestamp ? '(' + timestamp + ')' : ''}</small>
            ${conversation.unread_count > 0 ? `<span class="unread-count">${conversation.unread_count} unread</span>` : ''}
        </div>
        <button class="chat-history-delete-btn" data-conversation-id="${conversation.id}">Delete</button>
    `;

    return conversationDiv;
}

async function deleteChatHistory(conversationId) {
    try {
        const response = await fetch(`/api/conversations/${conversationId}`, { method: 'DELETE' }); // Corrected from POST to DELETE
        if (response.ok) {
            // Remove the element from the DOM
            const element = document.querySelector(`[data-conversation-id="${conversationId}"]`);
            if (element) {
                element.remove();
            }
            showToast('Chat history deleted.', 'success');

            // If no more conversations, show the empty message
            if (document.querySelectorAll('.chat-history-item').length === 0) {
                fetchChatHistories();
            } else {
                const error = await response.json();
                showToast(error.message || 'Failed to delete chat history.', 'error');
            }
        }
    } catch (error) {
        console.error('Failed to delete chat history:', error);
        showToast('An error occurred while deleting the chat.', 'error');
    }
}

// Add event listener for delete buttons
document.addEventListener('click', function (event) {
    if (event.target.classList.contains('chat-history-delete-btn')) {
        const conversationId = event.target.dataset.conversationId;
        if (confirm('Are you sure you want to delete this chat history?')) {
            deleteChatHistory(conversationId);
        }
    }
});

function formatTimeAgo(date) {
    const now = new Date();
    const diffInSeconds = Math.floor((now - date) / 1000);

    if (diffInSeconds < 60) return 'Just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
    if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)} days ago`;
    return date.toLocaleDateString();
}
