document.addEventListener('DOMContentLoaded', function () {
    // Seller dashboard logic
    if (document.getElementById('product-upload-form')) {
        const uploadSection = document.getElementById('upload-product');
        const productUploadForm = document.getElementById('product-upload-form');
        const formHeading = uploadSection.querySelector('h3');
        const uploadBtn = document.getElementById('upload-btn');
        const cancelBtn = document.getElementById('cancel-edit-btn');
        const productIdInput = document.getElementById('product-id');
        const productImageInput = document.getElementById('product-image');

        productUploadForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            const productId = document.getElementById('product-id').value;
            const isEditing = !!productId;

            // FormData will now correctly pick up all fields due to the 'name' attributes in the HTML
            const submissionData = new FormData(productUploadForm);

            const url = isEditing ? `/edit_product/${productId}` : '/add_product';

            try {
                const response = await fetch(url, {
                    method: 'POST',
                    body: submissionData
                });

                const result = await response.json();

                if (response.ok) {
                    alert(result.message);
                    if (isEditing) {
                        resetUploadForm();
                    } else {
                        productUploadForm.reset();
                    }
                    loadMyProducts();
                } else {
                    alert(result.message || 'An error occurred.');
                }
            } catch (error) {
                console.error('Error uploading product:', error);
                alert('An error occurred while uploading the product.');
            }
        });

        cancelBtn.addEventListener('click', resetUploadForm);

        let allProductsData = []; // Store products data to use for editing
        async function loadMyProducts() {
            try {
                const response = await fetch('/my_products');
                if (!response.ok) {
                    const result = await response.json();
                    alert(result.message);
                    return;
                }

                allProductsData = await response.json(); // Store for later
                const products = allProductsData;
                const productList = document.getElementById('product-list');
                productList.innerHTML = '';

                if (products.length === 0) {
                    productList.innerHTML = '<p>You have not uploaded any products yet.</p>';
                    return;
                }

                products.forEach(product => {
                    const productCard = document.createElement('div');
                    productCard.classList.add('product-card');
                    productCard.innerHTML = `
                        <img src="/static/${product.image}" alt="${product.name}">
                        <div class="product-info">
                            <h4>${product.name}</h4>
                            <p class="price">₹${product.price.toFixed(2)}</p>
                            <p>Status: <span class="status-${product.status.toLowerCase()}">${product.status}</span></p>
                            <p>Stock: ${product.stock}</p>
                            <button class="edit-btn" data-id="${product.id}">Edit</button>
                            <button class="delete-btn" data-id="${product.id}">Delete</button>
                        </div>
                    `;
                    productList.appendChild(productCard);
                });
            } catch (error) {
                console.error('Error loading products:', error);
                alert('An error occurred while loading your products.');
            }
        }

        loadMyProducts();

        async function loadMyOrders() {
            try {
                const response = await fetch('/seller_orders');
                if (!response.ok) {
                    const result = await response.json();
                    alert(result.message);
                    return;
                }

                const orders = await response.json();
                const ordersList = document.getElementById('orders-list');
                ordersList.innerHTML = '';

                if (orders.length === 0) {
                    ordersList.innerHTML = '<p>You have no orders yet.</p>';
                    return;
                }

                orders.forEach(order => {
                    const orderItem = document.createElement('div');
                    orderItem.classList.add('order-item');
                    orderItem.innerHTML = `
                        <div class="order-header">
                            <h3>Order #${order.id}</h3>
                            <span class="order-status ${order.status.toLowerCase()}">${order.status}</span>
                        </div>
                        <div class="order-details">
                            <div class="order-detail">
                                <strong>Buyer:</strong> <span>${order.buyer_name}</span>
                            </div>
                            <div class="order-detail">
                                <strong>Date:</strong> <span>${new Date(order.date).toLocaleDateString()}</span>
                            </div>
                            <div class="order-detail">
                                <strong>Total:</strong> <span>₹${order.total.toFixed(2)}</span>
                            </div>
                            ${order.tracking_number ? `
                            <div class="order-detail tracking-info">
                                <strong>Tracking:</strong> <span>${order.tracking_number}</span>
                            </div>
                            ` : ''}
                        </div>
                        <div class="order-items">
                            <h4>Items:</h4>
                            ${order.items.map(item => `
                                <div class="order-item-summary">
                                    <img src="${item.image}" alt="${item.name}">
                                    <div class="item-info">
                                        <h5>${item.name}</h5>
                                        <p>Quantity: ${item.quantity}</p>
                                        <p>Price: ₹${item.price.toFixed(2)}</p>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                        <div class="order-total">
                            <strong>Total: ₹${order.total.toFixed(2)}</strong>
                        </div>
                        <div class="order-actions">
                            <select class="order-status-select" data-order-id="${order.id}">
                                <option value="Processing" ${order.status === 'Processing' ? 'selected' : ''}>Processing</option>
                                <option value="Shipped" ${order.status === 'Shipped' ? 'selected' : ''}>Shipped</option>
                                <option value="Delivered" ${order.status === 'Delivered' ? 'selected' : ''}>Delivered</option>
                            </select>
                            <button class="btn-update-status" data-order-id="${order.id}">Update Status</button>
                        </div>
                    `;
                    ordersList.appendChild(orderItem);
                });
            } catch (error) {
                console.error('Error loading orders:', error);
                alert('An error occurred while loading your orders.');
            }
        }

        if (document.getElementById('orders-list')) {
            loadMyOrders();

            // tracking number input removed; no change handler needed for it
            document.getElementById('orders-list').addEventListener('change', (e) => {
                // keep placeholder in case other change handlers are added later
            });

            document.getElementById('orders-list').addEventListener('click', async (e) => {
                if (e.target.classList.contains('btn-update-status')) {
                    const orderId = e.target.dataset.orderId;
                    const selectElement = document.querySelector(`.order-status-select[data-order-id="${orderId}"]`);
                    const newStatus = selectElement.value;
                    try {
                        const response = await fetch(`/update_order_status/${orderId}`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({ status: newStatus })
                        });

                        const result = await response.json();
                        alert(result.message);

                        if (response.ok) {
                            loadMyOrders(); // Reload orders to show the updated status
                        }
                    } catch (error) {
                        console.error('Error updating order status:', error);
                    }
                }
            });
        }

        // Add event listener for edit and delete buttons
        document.addEventListener('click', async (e) => {
            if (e.target.classList.contains('edit-btn')) {
                const productId = e.target.dataset.id;
                handleEditClick(productId);
            }
            if (e.target.classList.contains('delete-btn')) {
                const productId = e.target.dataset.id;
                if (confirm('Are you sure you want to delete this product?')) {
                    try {
                        const response = await fetch(`/delete_product/${productId}`, {
                            method: 'POST'
                        });
                        const result = await response.json();
                        alert(result.message);
                        if (response.ok) {
                            loadMyProducts(); // Reload products after deletion
                        }
                    } catch (error) {
                        console.error('Error deleting product:', error);
                        alert('An error occurred while deleting the product.');
                    }
                }
            }
        });

        function handleEditClick(productId) {
            const product = allProductsData.find(p => p.id == productId);
            if (!product) return;

            // Populate the form
            document.getElementById('product-id').value = product.id;
            document.getElementById('product-name').value = product.name;
            document.getElementById('product-price').value = product.price;
            document.getElementById('product-category').value = product.category;
            document.getElementById('product-description').value = product.description;
            document.getElementById('product-stock').value = product.stock;
            productImageInput.required = false; // Image is not required for an update

            // Change UI to "edit mode"
            formHeading.textContent = `Editing: ${product.name}`;
            uploadBtn.textContent = 'Save Changes';
            cancelBtn.style.display = 'inline-block';

            // Scroll to the form
            uploadSection.scrollIntoView({ behavior: 'smooth' });
        }

        function resetUploadForm() {
            formHeading.textContent = 'Upload New Product';
            uploadBtn.textContent = 'Upload Product';
            cancelBtn.style.display = 'none';
            productUploadForm.reset();
            document.getElementById('product-id').value = '';
            productImageInput.required = true;
        }

    }

    // Admin dashboard logic
    if (document.getElementById('pending-products-table')) {
        async function loadPendingProducts() {
            try {
                const response = await fetch('/pending_products');
                const products = await response.json();
                const tableBody = document.querySelector('#pending-products-table tbody');
                tableBody.innerHTML = '';

                products.forEach(product => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${product.id}</td>
                        <td>${product.name}</td>
                        <td>${product.category}</td>
                        <td>${product.seller_id}</td>
                        <td>
                            <button class="action-btn approve" data-id="${product.id}">Approve</button>
                            <button class="action-btn reject" data-id="${product.id}">Reject</button>
                        </td>
                    `;
                    tableBody.appendChild(row);
                });
            } catch (error) {
                console.error('Error loading pending products:', error);
            }
        }

        async function loadAllProducts(sellerId = null) {
            const allProductsHeading = document.querySelector('#manage-products h3');
            try {
                let url = '/all_products';
                if (sellerId) {
                    const seller = (await (await fetch('/all_sellers')).json()).find(s => s.id == sellerId);
                    allProductsHeading.textContent = `Products by ${seller ? seller.name : 'Seller ' + sellerId}`;
                } else {
                    allProductsHeading.textContent = 'Manage All Products';
                }
                const response = await fetch(url);
                const products = await response.json();
                const tableBody = document.querySelector('#all-products-table tbody');
                tableBody.innerHTML = '';

                products.forEach(product => {
                    if (sellerId && product.seller_id != sellerId) return;

                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${product.id}</td>
                        <td>${product.name}</td>
                        <td>${product.category}</td>
                        <td>${product.seller_id}</td>
                        <td><span class="status-${product.status.toLowerCase()}">${product.status}</span></td>
                        <td>
                            <button class="action-btn reject admin-delete-product" data-id="${product.id}">Remove</button>
                        </td>
                    `;
                    tableBody.appendChild(row);
                });
            } catch (error) {
                console.error('Error loading all products:', error);
            }
        }

        document.getElementById('pending-products-table').addEventListener('click', async (e) => {
            if (e.target.classList.contains('approve')) {
                const productId = e.target.dataset.id;
                const response = await fetch(`/approve_product/${productId}`, { method: 'POST' });
                const result = await response.json();
                alert(result.message);
                loadPendingProducts();
                loadAllProducts();
            } else if (e.target.classList.contains('reject')) {
                const productId = e.target.dataset.id;
                const response = await fetch(`/reject_product/${productId}`, { method: 'POST' });
                const result = await response.json();
                alert(result.message);
                loadPendingProducts();
                loadAllProducts();
            }
        });

        document.getElementById('all-products-table').addEventListener('click', async (e) => {
            if (e.target.classList.contains('admin-delete-product')) {
                const productId = e.target.dataset.id;
                if (confirm(`Are you sure you want to permanently remove product #${productId}? This cannot be undone.`)) {
                    const response = await fetch(`/admin/delete_product/${productId}`, { method: 'POST' });
                    const result = await response.json();
                    alert(result.message);
                    if (response.ok) {
                        loadPendingProducts();
                        loadAllProducts();
                    }
                }
            }
        });

        async function loadSellers() {
            try {
                const response = await fetch('/all_sellers');
                const sellers = await response.json();
                const tableBody = document.querySelector('#seller-table tbody');
                tableBody.innerHTML = '';

                sellers.forEach(seller => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${seller.id}</td>
                        <td>${seller.name}</td>
                        <td><span class="status-approved">Active</span></td>
                        <td>
                            <button class="action-btn view" data-id="${seller.id}">View</button>
                        </td>
                    `;
                    tableBody.appendChild(row);
                });
            } catch (error) {
                console.error('Error loading sellers:', error);
            }
        }

        document.getElementById('seller-table').addEventListener('click', (e) => {
            if (e.target.classList.contains('view')) {
                const sellerId = e.target.dataset.id;
                loadAllProducts(sellerId);
            }
        });

        async function loadBuyers() {
            try {
                const response = await fetch('/all_buyers');
                const buyers = await response.json();
                const tableBody = document.querySelector('#buyer-table tbody');
                tableBody.innerHTML = '';

                buyers.forEach(buyer => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${buyer.id}</td>
                        <td>${buyer.name}</td>
                        <td>${buyer.email}</td>
                        <td>
                            <button class="action-btn view" data-id="${buyer.id}">View Orders</button>
                        </td>
                    `;
                    tableBody.appendChild(row);
                });
            } catch (error) {
                console.error('Error loading buyers:', error);
            }
        }

        async function loadFeedback() {
            try {
                const response = await fetch('/api/admin/feedback');
                const feedbacks = await response.json();
                const tableBody = document.querySelector('#feedback-table tbody');
                tableBody.innerHTML = '';

                if (feedbacks.length === 0) {
                    tableBody.innerHTML = '<tr><td colspan="6">No feedback has been submitted yet.</td></tr>';
                    return;
                }

                feedbacks.forEach(f => {
                    const row = document.createElement('tr');
                    let stars = '';
                    for (let i = 1; i <= 5; i++) {
                        stars += `<i class="fas fa-star ${i <= f.rating ? 'star-filled' : 'star-empty'}"></i>`;
                    }

                    row.innerHTML = `
                        <td>${f.user_name}</td>
                        <td><span class="status-${f.user_role}">${f.user_role}</span></td>
                        <td>${stars}</td>
                        <td class="feedback-text-cell">${f.feedback_text}</td>
                        <td>${new Date(f.timestamp).toLocaleDateString()}</td>
                        <td>
                            ${f.admin_reply
                            ? `<div class="replied-info">Replied on ${new Date(f.replied_at).toLocaleDateString()}<br><button class="action-btn view-reply" data-reply="${f.admin_reply}">View</button></div>`
                            : `<button class="action-btn reply-feedback" data-id="${f.id}" data-user="${f.user_name}" data-text="${f.feedback_text}">Reply</button>`
                        }
                        </td>
                    `;
                    tableBody.appendChild(row);
                });

                // Re-attach event listeners for the new buttons
                document.querySelectorAll('.reply-feedback').forEach(btn => btn.addEventListener('click', openReplyModal));
                document.querySelectorAll('.view-reply').forEach(btn => btn.addEventListener('click', (e) => {
                    alert(`Admin Reply:\n\n${e.target.dataset.reply}`);
                }));

            } catch (error) {
                console.error('Error loading feedback:', error);
            }
        }

        loadPendingProducts();
        loadAllProducts();
        loadSellers();
        loadBuyers();
        loadDashboardOverview();
        initializeAdminReports();
        loadFeedback();

        // Feedback Reply Modal Logic
        const modal = document.getElementById('feedback-reply-modal');
        const closeBtn = modal.querySelector('.close-btn');
        const replyForm = document.getElementById('feedback-reply-form');

        function openReplyModal(event) {
            const btn = event.target;
            document.getElementById('modal-feedback-id').value = btn.dataset.id;
            document.getElementById('modal-user-name').textContent = btn.dataset.user;
            document.getElementById('modal-feedback-text').textContent = btn.dataset.text;
            document.getElementById('modal-reply-text').value = ''; // Clear previous reply
            modal.classList.remove('hidden');
        }

        function closeReplyModal() {
            modal.classList.add('hidden');
        }

        closeBtn.addEventListener('click', closeReplyModal);
        window.addEventListener('click', (event) => {
            if (event.target == modal) {
                closeReplyModal();
            }
        });

        replyForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const feedbackId = document.getElementById('modal-feedback-id').value;
            const replyText = document.getElementById('modal-reply-text').value;
            const submitBtn = replyForm.querySelector('button[type="submit"]');

            submitBtn.disabled = true;
            submitBtn.textContent = 'Sending...';

            try {
                const response = await fetch(`/api/admin/feedback/reply/${feedbackId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ reply_text: replyText })
                });
                const result = await response.json();
                alert(result.message);
                if (response.ok) {
                    closeReplyModal();
                    loadFeedback(); // Refresh the feedback list
                }
            } catch (error) {
                console.error('Error sending reply:', error);
                alert('An error occurred while sending the reply.');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Send Reply';
            }
        });
    }

    function initializeAdminReports() {
        // Check if we are on the admin dashboard and the report containers exist
        if (!document.getElementById('monthly-sales-chart')) return;

        loadMonthlySalesReport();
        loadProductPerformanceReport();
        loadDailySalesReport(); // Initial load for the last 30 days
        loadPaymentDetailsReport();

        document.getElementById('filter-daily-sales-btn').addEventListener('click', () => {
            const startDate = document.getElementById('daily-sales-start').value;
            const endDate = document.getElementById('daily-sales-end').value;
            loadDailySalesReport(startDate, endDate);
        });
    }

    async function loadDashboardOverview() {
        if (!document.getElementById('metric-total-sales')) return;

        try {
            const response = await fetch('/api/reports/dashboard-overview');
            const data = await response.json();

            // 1. Populate Overview Cards
            const metrics = data.overview_metrics;
            document.getElementById('metric-total-sales').textContent = `₹${metrics.total_sales.toFixed(2)}`;
            document.getElementById('metric-total-orders').textContent = metrics.total_orders;
            document.getElementById('metric-avg-order-value').textContent = `₹${metrics.average_order_value.toFixed(2)}`;
            document.getElementById('metric-active-listings').textContent = metrics.active_listings;
            document.getElementById('metric-total-sellers').textContent = metrics.total_sellers;
            document.getElementById('metric-total-buyers').textContent = metrics.total_buyers;

            // 2. Render Peak Purchasing Times Chart
            const peakHoursCtx = document.getElementById('peak-hours-chart').getContext('2d');
            const hoursData = data.customer_behaviour.peak_purchasing_times;
            const peakLabels = Array.from({ length: 24 }, (_, i) => `${i}:00`);
            const peakValues = Array(24).fill(0);
            hoursData.forEach(d => { peakValues[d.hour] = d.orders; });

            new Chart(peakHoursCtx, {
                type: 'bar',
                data: {
                    labels: peakLabels,
                    datasets: [{
                        label: 'Number of Orders',
                        data: peakValues,
                        backgroundColor: 'rgba(255, 159, 64, 0.6)',
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
            });

            // 3. Render Seller Performance Chart
            const sellerPerfCtx = document.getElementById('seller-performance-chart').getContext('2d');
            const sellerData = data.performance_tracking.seller_performance;
            new Chart(sellerPerfCtx, {
                type: 'bar',
                data: {
                    labels: sellerData.map(s => s.seller_name),
                    datasets: [{
                        label: 'Average Rating (out of 5)',
                        data: sellerData.map(s => s.avg_rating),
                        backgroundColor: 'rgba(153, 102, 255, 0.6)',
                    }]
                },
                options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, scales: { x: { beginAtZero: true, max: 5 } } }
            });

            // 4. Render Platform Growth Chart
            const growthCtx = document.getElementById('platform-growth-chart').getContext('2d');
            const growthData = data.platform_growth.monthly_new_users;
            new Chart(growthCtx, {
                type: 'line',
                data: {
                    labels: growthData.map(g => g.period),
                    datasets: [{ label: 'New Users', data: growthData.map(g => g.new_users), borderColor: 'rgba(75, 192, 192, 1)', tension: 0.1 }]
                },
                options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } }
            });

        } catch (error) {
            console.error('Error loading dashboard overview:', error);
        }
    }

    async function loadMonthlySalesReport() {
        try {
            const response = await fetch('/api/reports/monthly-sales');
            const data = await response.json();
            const ctx = document.getElementById('monthly-sales-chart').getContext('2d');

            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.map(d => d.month),
                    datasets: [{
                        label: 'Monthly Sales (₹)',
                        data: data.map(d => d.sales),
                        backgroundColor: 'rgba(54, 162, 235, 0.6)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: true } },
                }
            });
        } catch (error) {
            console.error('Error loading monthly sales report:', error);
        }
    }

    async function loadProductPerformanceReport() {
        try {
            const response = await fetch('/api/reports/product-performance');
            const data = await response.json();
            const ctx = document.getElementById('product-performance-chart').getContext('2d');

            new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: data.map(d => d.product_name),
                    datasets: [{
                        label: 'Units Sold',
                        data: data.map(d => d.units_sold),
                        backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40'],
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'top' } },
                }
            });
        } catch (error) {
            console.error('Error loading product performance report:', error);
        }
    }

    let dailySalesChart = null; // Variable to hold the chart instance

    async function loadDailySalesReport(startDate, endDate) {
        let url = '/api/reports/daily-sales';
        if (startDate && endDate) {
            url += `?start_date=${startDate}&end_date=${endDate}`;
        }

        try {
            const response = await fetch(url);
            const data = await response.json();
            const ctx = document.getElementById('daily-sales-chart').getContext('2d');

            // If a chart instance already exists, destroy it before creating a new one
            if (dailySalesChart) {
                dailySalesChart.destroy();
            }

            const chartTitle = (startDate && endDate) ? `Daily Sales` : 'Daily Sales (Last 30 Days)';

            dailySalesChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.map(d => d.date),
                    datasets: [{
                        label: 'Daily Sales',
                        data: data.map(d => d.sales),
                        backgroundColor: 'rgba(75, 192, 192, 0.6)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: '#e9e9e9',
                                drawBorder: false,
                            }
                        },
                        x: {
                            grid: {
                                display: false, // Hide vertical grid lines
                            }
                        }
                    },
                    plugins: {
                        title: { display: true, text: chartTitle, font: { size: 16 } },
                        legend: { display: false } // Hide legend as there's only one dataset
                    },
                }
            });
        } catch (error) {
            console.error('Error loading daily sales report:', error);
        }
    }

    async function loadPaymentDetailsReport() {
        try {
            const response = await fetch('/api/reports/payment-details');
            const payments = await response.json();
            const tableBody = document.querySelector('#payment-report-table tbody');

            if (!tableBody) return;
            tableBody.innerHTML = '';

            if (payments.length === 0) {
                tableBody.innerHTML = '<tr><td colspan="7">No payment records found.</td></tr>';
                return;
            }

            payments.forEach(p => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${p.payment_id}</td>
                    <td>${p.order_id}</td>
                    <td>${p.user_name}</td>
                    <td>₹${p.amount.toFixed(2)}</td>
                    <td><span class="status-approved">${p.payment_method.toUpperCase()}</span></td>
                    <td><span class="status-${p.status.toLowerCase()}">${p.status}</span></td>
                    <td>${p.payment_date !== 'N/A' ? new Date(p.payment_date).toLocaleString() : 'N/A'}</td>
                `;
                tableBody.appendChild(row);
            });
        } catch (error) {
            console.error('Error loading payment details report:', error);
        }
    }
});