document.addEventListener("DOMContentLoaded", function () {
    if (document.querySelectorAll('.alert-danger').length > 0) {
        var errorModal = new bootstrap.Modal(document.getElementById('errorModal'));
        errorModal.show();
    }
});

