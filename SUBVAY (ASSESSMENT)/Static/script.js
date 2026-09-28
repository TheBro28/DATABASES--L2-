// Switches visibility between different forms on the screen
function showForm(formId) {
    // Find all form boxes on the page and hide them by removing their 'active' status
    document.querySelectorAll(".form-box").forEach(form => form.classList.remove("active"));
    
    // Find the specific form that was clicked and unhide it by adding the 'active' status back
    document.getElementById(formId).classList.add("active");
}

// Reads the ingredient price data out of the JSON script blocks and stores it for the price calculator
function loadBuilderPrices() {
    const breadData = document.getElementById('bread-prices-data');
    // Stops here on any page that doesn't have the sandwich builder on it
    if (!breadData) return;

    window.breadPrices = JSON.parse(breadData.textContent);
    window.cheesePrices = JSON.parse(document.getElementById('cheese-prices-data').textContent);
    window.saucePrices = JSON.parse(document.getElementById('sauce-prices-data').textContent);
    window.toppingPrices = JSON.parse(document.getElementById('topping-prices-data').textContent);
}

// Shows the description for whichever bread/cheese option is currently picked in the dropdown
function updateSelectionDescription(type) {
    const select = document.getElementById(type + '-select');
    // Stops here on any page that doesn't have the sandwich builder on it
    if (!select) return;

    const selectedId = select.value;

    // Hides every description block of this type first
    document.querySelectorAll('.' + type + '-description-block').forEach(block => {
        block.classList.remove('active-description');
    });

    // Reveals only the one matching the current dropdown value
    const activeBlock = document.getElementById(type + '-desc-' + selectedId);
    if (activeBlock) {
        activeBlock.classList.add('active-description');
    }
}

// Recalculates the running total from whatever is currently selected, without a page reload
function updateBuilderTotal() {
    const breadSelect = document.getElementById('bread-select');
    // Stops here on any page that doesn't have the sandwich builder on it
    if (!breadSelect) return;

    let total = 0;

    const breadId = breadSelect.value;
    if (breadId && window.breadPrices[breadId] !== undefined) {
        total += window.breadPrices[breadId];
    }

    const cheeseSelect = document.getElementById('cheese-select');
    const cheeseId = cheeseSelect.value;
    if (cheeseId && window.cheesePrices[cheeseId] !== undefined) {
        total += window.cheesePrices[cheeseId];
    }

    document.querySelectorAll('input[name="sauces"]:checked').forEach(checkbox => {
        total += window.saucePrices[checkbox.value];
    });

    document.querySelectorAll('input[name="toppings"]:checked').forEach(checkbox => {
        total += window.toppingPrices[checkbox.value];
    });

    document.getElementById('builder-total-value').textContent = total.toFixed(2);

    // Add to Cart stays disabled until a bread and a cheese have both been chosen
    document.getElementById('add-to-cart-btn').disabled = !(breadId && cheeseId);
}

// Saves the current selection into the session background workspace slot
function syncBuilderSelection() {
    const form = document.getElementById('builder-form');
    if (!form) return;

    fetch('/custom-sandwich/save-progress', {
        method: 'POST',
        body: new FormData(form)
    }).catch(() => {
        // A failed background save shouldn't interrupt the price shown on screen
    });
}

// Runs everything that needs to happen whenever a builder field changes
function handleBuilderChange(type) {
    if (type === 'bread' || type === 'cheese') {
        updateSelectionDescription(type);
    }
    updateBuilderTotal();
    syncBuilderSelection();
}

// Restores the correct description and total on page load if choices were carried over from the session
document.addEventListener('DOMContentLoaded', () => {
    loadBuilderPrices();
    updateSelectionDescription('bread');
    updateSelectionDescription('cheese');
    updateBuilderTotal();
});
