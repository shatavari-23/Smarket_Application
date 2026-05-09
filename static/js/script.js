const body = document.body;

let isLoggedIn = false;
let userRole = null;

// ===================================
// UI HELPER FUNCTIONS
// ===================================
function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toast-container') || document.createElement('div');
    if (!toastContainer.id) {
        toastContainer.id = 'toast-container';
        document.body.appendChild(toastContainer);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// ===================================
// CART HELPER FUNCTIONS
// ===================================
async function getCart() {
    if (isLoggedIn && userRole === 'buyer') {
        try {
            const response = await fetch('/api/cart/get');
            if (response.ok) {
                const data = await response.json();
                return data;
            } else {
                console.error('Failed to fetch cart:', response.status, response.statusText);
            }
        } catch (e) {
            console.error('Error fetching cart:', e);
        }
    }
    // fallback to localStorage for non-logged-in users
    try {
        const cart = JSON.parse(localStorage.getItem('cart')) || [];
        return cart.filter(item => item !== null && item !== undefined);
    } catch (e) {
        console.error("Failed to parse cart data from localStorage", e);
        return [];
    }
}

async function saveCart(cart) {
    if (isLoggedIn && userRole === 'buyer') {
        // no need, as it's in DB
    } else {
        localStorage.setItem('cart', JSON.stringify(cart));
    }
    await updateCartCount();
}

async function updateCartCount() {
    const cart = await getCart();
    const cartCountElement = document.getElementById('cart-count');
    if (cartCountElement) {
        const totalItems = cart.reduce((sum, item) => sum + item.qty, 0);
        cartCountElement.textContent = totalItems;
        cartCountElement.style.display = totalItems > 0 ? 'flex' : 'none'; // Correctly hides/shows badge
    }
}

window.addToCart = async function (product) {
    if (!isLoggedIn) {
        showToast("Please log in to add to cart.", "error");
        return;
    }
    const productToAdd = { ...product, image: `/static/${product.image}` };
    if (isLoggedIn && userRole === 'buyer') {
        try {
            showToast("Adding to cart...", "info");
            const response = await fetch('/api/cart/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ product_id: product.id, quantity: 1 })
            });
            if (!response.ok) {
                const error = await response.json();
                showToast(error.message || 'Failed to add to cart', 'error');
                return;
            }
        } catch (e) {
            alert('Error adding to cart');
            return;
        }
    } else {
        const cart = await getCart();
        const existingProductIndex = cart.findIndex(item => item.id === productToAdd.id);

        if (existingProductIndex > -1) {
            cart[existingProductIndex].qty += 1;
        } else {
            cart.push({ ...productToAdd, qty: 1 });
        }
        await saveCart(cart);
    }
    await updateCartCount();
    showToast("Product added to cart!");
};

window.updateQuantity = async function (productId, newQty) {
    if (!isLoggedIn) {
        showToast("Please log in to modify cart.", "error");
        return;
    }
    if (isLoggedIn && userRole === 'buyer') {
        try {
            const response = await fetch('/api/cart/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ product_id: productId, quantity: newQty })
            });
            if (!response.ok) {
                const error = await response.json();
                showToast(error.message || 'Failed to update cart', 'error');
                return;
            }
        } catch (e) {
            showToast('Error updating cart', 'error');
            return;
        }
    } else {
        let cart = await getCart();
        const itemIndex = cart.findIndex(item => item.id === productId);

        if (itemIndex > -1) {
            if (newQty > 0) {
                cart[itemIndex].qty = newQty;
            } else {
                cart.splice(itemIndex, 1);
            }
            await saveCart(cart);
        }
    }
    await renderCart();
    await updateCartCount();
    await renderOrderSummary();
};

window.removeFromCart = async function (productId) {
    if (!isLoggedIn) {
        showToast("Please log in to modify cart.", "error");
        return;
    }
    showToast("Removing from cart...", "info");
    if (isLoggedIn && userRole === 'buyer') {
        try {
            const response = await fetch('/api/cart/remove', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ product_id: productId })
            });
            if (response.ok) {
                showToast("Product removed from cart.");
            } else {
                const error = await response.json();
                showToast(error.message || 'Failed to remove from cart', 'error');
                return;
            }
        } catch (e) {
            showToast('Error removing from cart', 'error');
            return;
        }
    } else {
        // This part is for non-logged-in users, which is not the primary flow.
        showToast("Product removed from cart.");
    }
    await renderCart();
    await updateCartCount();
    await renderOrderSummary();
};

window.renderCart = async function () {
    const cartItemsList = document.getElementById('cart-items-list');
    if (!cartItemsList) return;

    const cart = await getCart();
    cartItemsList.innerHTML = '';
    let subtotal = 0;

    if (cart.length === 0) {
        cartItemsList.innerHTML = '<p class="empty-cart-message">Your cart is empty.</p>';
        document.getElementById('cart-subtotal').textContent = `₹0.00`;
        document.getElementById('cart-total').textContent = `₹0.00`;
        return;
    }

    cart.forEach(item => {
        const itemPrice = item.price * item.qty;
        subtotal += itemPrice;
        const cartItemCard = document.createElement('div');
        cartItemCard.classList.add('cart-item-card');
        cartItemCard.dataset.productId = item.id;

        cartItemCard.innerHTML = `
            <div class="item-image">
                <img src="${item.image}" alt="${item.name}">
            </div>
            <div class="item-details">
                <h4>${item.name}</h4>
                <p>₹${item.price.toFixed(2)} each</p>
                <div class="item-quantity-controls">
                    <button class="quantity-btn decrease-qty" data-product-id="${item.id}">-</button>
                    <input type="text" value="${item.qty}" class="item-quantity" readonly>
                    <button class="quantity-btn increase-qty" data-product-id="${item.id}">+</button>
                </div>
            </div>
            <span class="item-price">₹${itemPrice.toFixed(2)}</span>
            <button class="item-remove-btn" data-product-id="${item.id}">
                <i class="fa-solid fa-trash"></i>
            </button>
        `;
        cartItemsList.appendChild(cartItemCard);
    });

    const shipping = 0.00;
    const total = subtotal + shipping;
    document.getElementById('cart-subtotal').textContent = `₹${subtotal.toFixed(2)}`;
    document.getElementById('cart-total').textContent = `₹${total.toFixed(2)}`;
};

window.renderOrderSummary = async function () {
    const orderItemsList = document.getElementById('order-items-list');
    const subtotalPriceSpan = document.getElementById('subtotal-price');
    const totalPriceSpan = document.getElementById('total-price');

    if (!orderItemsList || !subtotalPriceSpan || !totalPriceSpan) return;

    const cart = await getCart();
    orderItemsList.innerHTML = '';
    let subtotal = 0;

    if (cart.length === 0) {
        orderItemsList.innerHTML = '<li>Your cart is empty.</li>';
        subtotalPriceSpan.textContent = `₹0.00`;
        totalPriceSpan.textContent = `₹0.00`;
        return;
    }

    cart.forEach(item => {
        const listItem = document.createElement('li');
        listItem.classList.add('order-item');
        const itemPrice = item.price * item.qty;
        subtotal += itemPrice;

        listItem.innerHTML = `
            <div class="order-item-info">
                <img src="${item.image}" alt="${item.name}">
                <span>${item.name} (x${item.qty})</span>
            </div>
            <span>₹${itemPrice.toFixed(2)}</span>
        `;
        orderItemsList.appendChild(listItem);
    });

    const shipping = 0.00;
    const total = subtotal + shipping;
    subtotalPriceSpan.textContent = `₹${subtotal.toFixed(2)}`;
    totalPriceSpan.textContent = `₹${total.toFixed(2)}`;
};

// ===================================
// WISHLIST HELPER FUNCTIONS
// ===================================
async function getWishlist() {
    if (isLoggedIn && userRole === 'buyer') {
        try {
            const response = await fetch('/api/wishlist/get');
            if (response.ok) {
                const data = await response.json();
                return data;
            } else {
                console.error('Failed to fetch wishlist:', response.status, response.statusText);
            }
        } catch (e) {
            console.error('Error fetching wishlist:', e);
        }
    }
    // fallback to localStorage for non-logged-in users
    try {
        const wishlist = JSON.parse(localStorage.getItem('wishlist')) || [];
        return wishlist.filter(item => item !== null && item !== undefined);
    } catch (e) {
        console.error("Failed to parse wishlist data from localStorage", e);
        return [];
    }
}

async function saveWishlist(wishlist) {
    if (isLoggedIn && userRole === 'buyer') {
        // no need, as it's in DB
    } else {
        const uniqueWishlist = wishlist.filter(
            (item, index, self) => item && item.id && index === self.findIndex(p => p.id === item.id)
        );
        localStorage.setItem('wishlist', JSON.stringify(uniqueWishlist));
    }
    await updateWishlistCount();
}

async function updateWishlistCount() {
    const wishlist = await getWishlist();
    const wishlistCountElement = document.getElementById('wishlist-count');
    if (wishlistCountElement) {
        wishlistCountElement.textContent = wishlist.length;
        wishlistCountElement.style.display = wishlist.length > 0 ? 'flex' : 'none'; // Correctly hides/shows badge
    }
}

window.toggleWishlist = async function (product) {
    if (!isLoggedIn) {
        showToast("Please log in to add to wishlist.", "error");
        return;
    }
    if (!product || !product.id) return;
    const productToStore = { ...product, image: `/static/${product.image}` };
    if (isLoggedIn && userRole === 'buyer') {
        // Check if already in wishlist
        const wishlist = await getWishlist();
        const isInWishlist = wishlist.some(item => item.id == product.id);
        if (isInWishlist) {
            showToast("Removing from wishlist...", "info");
            try {
                const response = await fetch('/api/wishlist/remove', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ product_id: product.id })
                });
                if (!response.ok) {
                    throw new Error('Failed to remove from wishlist');
                }
                showToast("Removed from wishlist!");
            } catch (e) {
                showToast('Error removing from wishlist', 'error');
            }
        } else {
            showToast("Adding to wishlist...", "info");
            try {
                const response = await fetch('/api/wishlist/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ product_id: product.id })
                });
                if (!response.ok) {
                    const data = await response.json();
                    if (data.message !== 'Already in wishlist') {
                        showToast(data.message || 'Failed to add to wishlist', 'error');
                    }
                }
                showToast("Added to wishlist!");
            } catch (e) {
                showToast('Error adding to wishlist', 'error');
            }
        }
    } else {
        let wishlist = await getWishlist();
        const existsIndex = wishlist.findIndex(item => item.id === productToStore.id);

        if (existsIndex > -1) {
            wishlist.splice(existsIndex, 1);
            showToast("Removed from wishlist!");
        } else {
            wishlist.push(productToStore);
            showToast("Added to wishlist!");
        }
        await saveWishlist(wishlist);
    }
    await initWishlistIcons(); // Refresh icons after any change
    await updateWishlistCount();
};

window.removeFromWishlist = async function (productId) {
    if (!isLoggedIn) {
        showToast("Please log in to modify wishlist.", "error");
        return;
    }
    if (isLoggedIn && userRole === 'buyer') {
        try {
            const response = await fetch('/api/wishlist/remove', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ product_id: productId })
            });
            if (!response.ok) {
                throw new Error('Failed to remove from wishlist');
            }
        } catch (e) {
            showToast('Error removing from wishlist', 'error');
            return;
        }
    }
    await renderWishlist();
    showToast("Removed from wishlist.");
    await updateCartCount();
    await updateWishlistCount();
};

async function renderWishlist() {
    const wishlist = await getWishlist();
    const container = document.getElementById('wishlist-items-container');

    if (!container) return;
    container.innerHTML = '';

    if (wishlist.length === 0) {
        container.innerHTML = '<p id="wishlist-empty-message">Your wishlist is currently empty.</p>';
    } else {
        wishlist.forEach(item => {
            const card = document.createElement('div');
            card.className = 'wishlist-item-card';
            card.innerHTML = `
                <a class="wishlist-product-link" href="/product/${item.id}">
                    <img src="${item.image}" alt="${item.name}">
                    <div class="item-details">
                        <h4>${item.name}</h4>
                        <p>₹${item.price}</p>
                    </div>
                </a>
                <div class="wishlist-actions">
                    <button class="btn product-cart-btn"
                        data-product-id="${item.id}"
                        data-product-name="${item.name}"
                        data-product-price="${item.price}"
                        data-product-image="${item.image.replace('/static/', '')}"
                        data-product-category="${item.category}">
                        <i class="fa-solid fa-cart-shopping"></i>Add to Cart
                    </button>
                    <button class="btn btn-remove" data-product-id="${item.id}">
                        <i class="fa-solid fa-trash"></i>Remove
                    </button>
                </div>
            `;
            container.appendChild(card);
            // Make the entire card clickable except when clicking on action buttons
            card.addEventListener('click', (e) => {
                // If the click originated inside the actions area or on a button, don't navigate
                if (e.target.closest('.wishlist-actions') || e.target.closest('.btn')) return;
                const link = card.querySelector('.wishlist-product-link');
                if (link) {
                    // Use location.href to navigate to the product page
                    window.location.href = link.href;
                }
            });
        });
    }
    await updateWishlistCount();
}

async function initWishlistIcons() {
    const wishlist = await getWishlist();
    document.querySelectorAll('.wishlist-btn').forEach(btn => {
        const productBox = btn.closest('.product-box, .product-details');
        if (!productBox) return;
        const cartBtn = productBox.querySelector('.product-cart-btn');
        if (!cartBtn) return;
        const productId = cartBtn.dataset.productId;
        if (wishlist.find(item => item.id == productId)) {
            btn.innerHTML = `<i class="fa-solid fa-heart" style="color: #e63946;"></i>`; // Filled heart
        } else {
            btn.innerHTML = `<i class="fa-regular fa-heart"></i>`;
        }
    });
}

// ===================================
// AUTHENTICATION HELPER FUNCTIONS
// ===================================
async function checkUserSession() {
    try {
        const response = await fetch('/api/session-check');
        const data = await response.json();
        isLoggedIn = data.logged_in;
        userRole = data.logged_in ? data.user.role : null;
        updateUserNav(data);
    } catch (error) {
        console.error('Session check failed:', error);
        isLoggedIn = false;
        userRole = null;
        updateUserNav({ logged_in: false });
    }
    await updateCartCount(); // Refresh counts on session check
    await updateWishlistCount(); // Refresh counts on session check
    await updateNotificationCount(); // Refresh notification count on session check
}
async function updateNotificationCount(showToastOnLogin = false) {
    try {
        if (!isLoggedIn) return;
        const response = await fetch('/api/notifications');
        if (!response.ok) return;
        const notifications = await response.json();
        const unreadCount = notifications.filter(n => !n.is_read).length;
        const countElement = document.getElementById('notification-count');
        if (countElement) {
            countElement.textContent = unreadCount;
            countElement.style.display = unreadCount > 0 ? 'flex' : 'none';
        }

        if (showToastOnLogin && unreadCount > 0) {
            const message = `You have ${unreadCount} unread notification${unreadCount > 1 ? 's' : ''}.`;
            showToast(message, 'info');
        }
    } catch (error) { console.error("Error updating notification count:", error); }
}
function updateUserNav(userData) {
    const userNav = document.getElementById('user-nav-placeholder');
    if (!userNav) return;

    if (userData.logged_in) {
        const user = userData.user;
        const role = user.role;
        let dashboardLink = '';
        if (role === 'admin') {
            dashboardLink = '<a href="/admin-dashboard">Admin Dashboard</a>';
        } else if (role === 'seller') {
            dashboardLink = '<a href="/seller-dashboard">Seller Dashboard</a>';
        }
        // For buyer, no dashboard link

        userNav.innerHTML = `
            <div class="nav-user logged-in">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512">
                    <path d="M224 256A128 128 0 1 0 224 0a128 128 0 1 0 0 256zm-45.7 48C79.8 304 0 383.8 0 482.3C0 498.7 13.3 512 29.7 512H418.3c16.4 0 29.7-13.3 29.7-29.7c0-98.5-79.8-178.3-179.3-178.3H178.3z"/>
                </svg>
                <span>Hi, ${user.name}</span>
                <div class="user-dropdown" style="display: none;">
                    ${dashboardLink}
                    <a href="/profile">Profile</a>
                    <a href="/my-orders">My Orders</a>
                    <a href="/logout">Logout</a>
                </div>
            </div>
        `;
        const navUser = document.querySelector('.nav-user');
        if (navUser) {
            navUser.classList.add('logged-in');
        }
    } else {
        userNav.innerHTML = `
            <a href="javascript:void(0);" class="nav-user">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512">
                    <path d="M224 256A128 128 0 1 0 224 0a128 128 0 1 0 0 256zm-45.7 48C79.8 304 0 383.8 0 482.3C0 498.7 13.3 512 29.7 512H418.3c16.4 0 29.7-13.3 29.7-29.7c0-98.5-79.8-178.3-179.3-178.3H178.3z"/>
                </svg>
            </a>
        `;
        const navUser = document.querySelector('.nav-user');
        if (navUser) {
            navUser.classList.remove('logged-in');
        }
    }
}



// ===================================
// MAIN SCRIPT LOGIC
// ===================================

// Add a pageshow event listener to handle browser back/forward cache (bfcache).
// This ensures that when a user navigates back to a page, the data is refreshed.
window.addEventListener('pageshow', function (event) {
    // The 'persisted' property is true if the page is being restored from the cache.
    if (event.persisted) {
        // Re-run the session check to update all dynamic user data like cart/wishlist counts.
        checkUserSession();
    }
});


document.addEventListener('DOMContentLoaded', async function () {
    // General UI setup
    const searchBar = document.querySelector('.search-bar');
    const formElement = document.querySelector('.form');

    // Initial state setup
    // Ensure we know the user's session first so wishlist/cart init reads the correct source (DB vs localStorage)
    await checkUserSession();
    await initWishlistIcons();

    // After logout, the user is redirected to '/?logout=true'.
    // This checks for the query parameter and shows the login form.
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('logout')) {
        document.querySelector('.form').classList.add('login-active');
    }

    document.addEventListener('click', function (event) {
        console.log("Click event triggered");
        const navUser = document.querySelector('.nav-user');
        const dropdown = document.querySelector('.user-dropdown');

        if (navUser && navUser.classList.contains('logged-in') && navUser.contains(event.target)) {
            console.log("User greeting clicked");
            if (dropdown) {
                dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
            }
        } else if (dropdown && dropdown.style.display === 'block' && !event.target.closest('.nav-user')) {
            console.log("Clicked outside dropdown");
            dropdown.style.display = 'none';
        }
    });

    // Show login form on page load if not logged in
    if (!isLoggedIn) {
        formElement.classList.add('login-active');
        body.style.overflow = 'hidden';
    }

    // --- Header Fix on Scroll ---
    const header = document.querySelector('header');
    window.addEventListener('scroll', function () {
        if (!window.location.pathname.includes('/chat')) {
            if (window.scrollY > 50) {
                header.classList.add('header-fix');
            } else {
                header.classList.remove('header-fix');
            }
        }
    });

    // --- Global Click Handler for dynamic and static elements ---
    document.addEventListener('click', function (event) {
        const target = event.target;

        // Add to Cart
        const addToCartBtn = target.closest('.product-cart-btn');
        if (addToCartBtn) {
            event.preventDefault();
            const product = {
                id: addToCartBtn.dataset.productId,
                name: addToCartBtn.dataset.productName,
                price: parseFloat(addToCartBtn.dataset.productPrice),
                image: addToCartBtn.dataset.productImage,
                category: addToCartBtn.dataset.productCategory
            };
            if (window.addToCart) window.addToCart(product);
        }

        // Toggle Wishlist
        const wishlistBtn = target.closest('.wishlist-btn');
        if (wishlistBtn) {
            event.preventDefault();
            const productBox = wishlistBtn.closest('.product-box, .product-details');
            if (!productBox) return;
            const cartBtn = productBox.querySelector('.product-cart-btn');
            if (!cartBtn) return;
            const product = {
                id: cartBtn.dataset.productId,
                name: cartBtn.dataset.productName,
                price: parseFloat(cartBtn.dataset.productPrice),
                image: cartBtn.dataset.productImage.replace('/static/', ''), // Ensure clean path
                category: cartBtn.dataset.productCategory
            };
            if (window.toggleWishlist) window.toggleWishlist(product);
        }
        // Buy Now
        const buyNowBtn = target.closest('.btn-buy-now');
        if (buyNowBtn) {
            event.preventDefault();
            if (!isLoggedIn) {
                showToast("Please log in to buy now.", "error");
                return;
            }
            const product = {
                id: buyNowBtn.dataset.productId,
                name: buyNowBtn.dataset.productName,
                price: parseFloat(buyNowBtn.dataset.productPrice),
                image: buyNowBtn.dataset.productImage,
                category: buyNowBtn.dataset.productCategory
            };
            if (window.addToCart) window.addToCart(product);
            window.location.href = '/checkout';
        }

        // Search Bar
        if (target.closest('.nav-search')) {
            searchBar.classList.add('search-bar-active');
            body.style.overflow = 'hidden';
        } else if (target.closest('.search-cancel')) {
            searchBar.classList.remove('search-bar-active');
            body.style.overflow = 'auto';
        }

        // Remove from Wishlist
        const removeBtn = target.closest('.btn-remove');
        if (removeBtn) {
            event.preventDefault();
            const productId = removeBtn.dataset.productId;
            if (window.removeFromWishlist) window.removeFromWishlist(productId);
        }

        // Login/Signup Forms
        if (!isLoggedIn && (target.closest('.nav-user') || target.closest('.already-account'))) {
            formElement.classList.add('login-active');
            formElement.classList.remove('signup-active');
            body.style.overflow = 'hidden';
        } else if (target.closest('.sign-up-btn')) {
            formElement.classList.remove('login-active');
            formElement.classList.add('signup-active');
        } else if (target.closest('.form-cancel')) {
            formElement.classList.remove('login-active', 'signup-active');
            body.style.overflow = 'auto';
        }
    });

    // --- Page-Specific Logic ---

    // Cart Page
    if (window.location.pathname.includes('/cart')) {
        (async () => { await renderCart(); })();
        const cartItemsList = document.getElementById('cart-items-list');
        if (cartItemsList) {
            cartItemsList.addEventListener('click', (event) => {
                const target = event.target;
                const productCard = target.closest('.cart-item-card');
                if (!productCard) return;
                const productId = productCard.dataset.productId;
                const currentQty = parseInt(productCard.querySelector('.item-quantity').value);
                if (target.classList.contains('increase-qty')) updateQuantity(productId, currentQty + 1);
                else if (target.classList.contains('decrease-qty')) updateQuantity(productId, currentQty - 1);
                else if (target.closest('.item-remove-btn')) removeFromCart(productId);
            });
        }
        const cartPageCheckoutBtn = document.getElementById('checkout-btn');
        if (cartPageCheckoutBtn) {
            cartPageCheckoutBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                if (!isLoggedIn) {
                    showToast("Please log in to proceed to checkout.", "error");
                    return;
                }
                const cart = await getCart();
                if (cart.length > 0) window.location.href = '/checkout';
                else showToast('Your cart is empty.', 'error');
            });
        }
    }

    // Checkout Page
    if (window.location.pathname.includes('/checkout')) {
        if (!isLoggedIn) {
            showToast("Please log in to proceed with payment.", "error");
            window.location.href = '/';
            return;
        }
        (async () => { await renderOrderSummary(); })();
        // Payment form logic can be added here
    }

    // Wishlist Page
    if (window.location.pathname.includes('/wishlist')) {
        await renderWishlist();
    }

    // --- Authentication Form Handlers ---
    const loginFormElement = document.querySelector('.login-form form');
    if (loginFormElement) {
        loginFormElement.addEventListener('submit', async function (e) {
            e.preventDefault();
            const email = e.target.email.value;
            const password = e.target.password.value;
            const response = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const result = await response.json();
            if (response.ok) {
                showToast(result.message);
                sessionStorage.setItem('justLoggedIn', 'true');
                window.location.href = result.redirect;
            } else {
                showToast(result.message, 'error');
            }
        });
    }

    const signupFormElement = document.querySelector('.signup-form form');
    if (signupFormElement) {
        signupFormElement.addEventListener('submit', async function (e) {
            e.preventDefault();
            const fullname = e.target.Fullname.value;
            const email = e.target.email.value;
            const password = e.target.password.value;
            const selectedRole = document.getElementById('signup-role').value;
            const response = await fetch('/signup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fullname, email, password, role: selectedRole })
            });
            const result = await response.json();
            showToast(result.message, response.ok ? 'success' : 'error');
            if (response.ok) {
                // Switch to login form
                formElement.classList.add('login-active');
                formElement.classList.remove('signup-active');
            }
        });
    }

    const searchForm = document.querySelector('.search-input');
    if (searchForm) {
        searchForm.addEventListener('submit', function (e) {
            e.preventDefault();
            // Try to find the search input by common names, fallback to first text/search input
            let input = e.target.querySelector('input[name="q"]') || e.target.querySelector('input[name="search"]') || e.target.querySelector('input[type="search"]') || e.target.querySelector('input[type="text"]');
            const query = input ? (input.value || '').trim() : '';
            if (query) {
                window.location.href = `/search?q=${encodeURIComponent(query)}`;
            }
        });
    }
});

document.addEventListener('DOMContentLoaded', function () {
    // This needs to be outside the main DOMContentLoaded to be accessible by other scripts if needed
    var socket = io.connect('http://' + location.hostname + ':' + location.port);

    socket.on('connect', function () {
        console.log('Socket.IO connected for real-time updates!');
    });

    // Listen for new notifications in real-time
    socket.on('new_notification', function (notification) {
        console.log('New notification received:', notification);

        // Show a toast message
        showToast(notification.message, 'info');

        // Update the notification count in the header
        const countElement = document.getElementById('notification-count');
        if (countElement) {
            const currentCount = parseInt(countElement.textContent) || 0;
            countElement.textContent = currentCount + 1;
            countElement.style.display = 'flex';
        }
    });
});

document.addEventListener('DOMContentLoaded', function () {
    if (sessionStorage.getItem('justLoggedIn') === 'true') {
        sessionStorage.removeItem('justLoggedIn');
        // The checkUserSession will call updateNotificationCount, let's tell it to show the toast
        updateNotificationCount(true);
    }
});