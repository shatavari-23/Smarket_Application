document.addEventListener('DOMContentLoaded', function () {
    const productId = document.body.dataset.productId;
    if (!productId) {
        console.error('Product ID not found on the page.');
        return;
    }

    const stars = document.querySelectorAll('#reviews-section .star');
    const reviewForm = document.getElementById('review-form');
    const reviewText = document.getElementById('review-text');
    const reviewsList = document.getElementById('reviews-list');
    let selectedRating = 0;
    const socket = io.connect(location.protocol + '//' + location.hostname + ':' + location.port);

    // --- Star Rating Interaction ---
    if (reviewForm) {
        stars.forEach(star => {
            star.addEventListener('click', () => {
                selectedRating = parseInt(star.dataset.value);
                updateStars(selectedRating);
            });
        });
    }

    function updateStars(rating) {
        stars.forEach((s, index) => {
            if (index < rating) {
                s.classList.add('fa-solid');
                s.classList.remove('fa-regular');
            } else {
                s.classList.remove('fa-solid');
                s.classList.add('fa-regular');
            }
        });
    }

    // --- Review Rendering ---
    function createReviewElement(review) {
        const wrap = document.createElement('div');
        wrap.className = 'review-item';

        let starsHtml = '';
        for (let i = 1; i <= 5; i++) {
            starsHtml += `<i class="fa-${i <= review.rating ? 'solid' : 'regular'} fa-star"></i>`;
        }

        const userName = review.user ? review.user.name : 'Anonymous';
        wrap.innerHTML = `
            <div class="review-header">
                <strong>${userName}</strong>
                <div class="stars">${starsHtml}</div>
            </div>
            <p>${review.text}</p>`;
        return wrap;
    }

    // --- API and Socket Logic ---
    async function loadReviews() {
        try {
            const response = await fetch(`/api/product/${productId}/reviews`);
            if (!response.ok) throw new Error('Failed to load reviews');
            const reviews = await response.json();
            reviewsList.innerHTML = '';
            if (reviews.length === 0) {
                reviewsList.innerHTML = '<p>No reviews yet. Be the first to write one!</p>';
            } else {
                reviews.forEach(review => {
                    reviewsList.appendChild(createReviewElement(review));
                });
            }
        } catch (error) {
            console.error('Error loading reviews:', error);
            reviewsList.innerHTML = '<p>Could not load reviews at this time.</p>';
        }
    }

    if (reviewForm) {
        reviewForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const text = reviewText.value.trim();
            if (!selectedRating) return alert("Please select a star rating!");
            if (!text) return alert("Please write a review!");

            try {
                const response = await fetch(`/api/product/${productId}/review`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ rating: selectedRating, text: text }),
                });
                const result = await response.json();
                if (!response.ok) throw new Error(result.message || 'Failed to submit review');

                // Reset form - the socket will handle adding the review to the list
                reviewText.value = '';
                selectedRating = 0;
                updateStars(0);

            } catch (error) {
                console.error('Error submitting review:', error);
                alert(`Error: ${error.message}`);
            }
        });
    }

    loadReviews();

    // Listen for new reviews from anyone
    socket.on('new_review', function (data) {
        if (data.product_id == productId) {
            if (reviewsList.querySelector('p')) { // Remove "No reviews yet" message
                reviewsList.innerHTML = '';
            }
            const newReviewEl = createReviewElement(data.review);
            reviewsList.prepend(newReviewEl); // Add new review to the top
        }
    });
});