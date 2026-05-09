document.addEventListener("DOMContentLoaded", function () {
    const stars = document.querySelectorAll(".rating .star");
    let selectedRating = 0;

    stars.forEach((star) => {
        star.addEventListener("click", function () {
            selectedRating = this.dataset.value;
            stars.forEach((s) => {
                s.classList.remove("selected", "fa-solid");
                s.classList.add("fa-regular");
            });
            this.classList.add("selected", "fa-solid");
            this.classList.remove("fa-regular");
            let next = this.nextElementSibling;
            while (next) {
                next.classList.add("selected", "fa-solid");
                next.classList.remove("fa-regular");
                next = next.nextElementSibling;
            }
        });
    });

    const feedbackForm = document.getElementById("feedback-form");
    if (feedbackForm) {
        feedbackForm.addEventListener("submit", async function (e) {
            e.preventDefault();
            const submitBtn = this.querySelector(".btn-submit");
            submitBtn.disabled = true;
            submitBtn.textContent = "Submitting...";

            const feedbackText = document.getElementById("feedback-text").value;

            if (selectedRating === 0) {
                showToast("Please select a rating.", "error");
                submitBtn.disabled = false;
                submitBtn.textContent = "Submit Feedback";
                return;
            }

            try {
                const response = await fetch("/feedback", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        rating: selectedRating,
                        feedback_text: feedbackText,
                    }),
                });

                const result = await response.json();
                showToast(result.message, response.ok ? "success" : "error");

                if (response.ok) {
                    setTimeout(() => {
                        window.location.reload(); // Reload to show the new feedback in history
                    }, 2000);
                } else {
                    submitBtn.disabled = false;
                    submitBtn.textContent = "Submit Feedback";
                }
            } catch (error) {
                showToast("An error occurred. Please try again.", "error");
                submitBtn.disabled = false;
                submitBtn.textContent = "Submit Feedback";
            }
        });
    }
});