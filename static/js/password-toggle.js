document.addEventListener('DOMContentLoaded', function () {
    // Select all elements with the class 'toggle-password'
    const togglePasswordIcons = document.querySelectorAll('.toggle-password');

    togglePasswordIcons.forEach(icon => {
        icon.addEventListener('click', function () {
            // Get the previous sibling element, which should be the password input
            const passwordInput = this.previousElementSibling;
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);

            // Toggle the eye icon class between 'fa-eye' and 'fa-eye-slash'
            this.classList.toggle('fa-eye');
            this.classList.toggle('fa-eye-slash');
        });
    });
});