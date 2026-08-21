// Switches visibility between different forms on the screen
function showForm(formId) {
    // Find all form boxes on the page and hide them by removing their 'active' status
    document.querySelectorAll(".form-box").forEach(form => form.classList.remove("active"));
    
    // Find the specific form that was clicked and unhide it by adding the 'active' status back
    document.getElementById(formId).classList.add("active");
}
