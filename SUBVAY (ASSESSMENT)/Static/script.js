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

// Opens time picker when the clock is clicked
function openTimePicker(event) {
    const input = document.getElementById('pickup-time-input');
    if (!input) return;
    // Avoids double-triggering if the time picker is already open
    if (event.target === input) return;
    if (input.showPicker) {
        input.showPicker();
    } else {
        input.focus();
    }
}

// Adds up every item's price x quantity currently shown on the checkout page and updates the Cart Total
function updateCartGrandTotal() {
    let total = 0;
    document.querySelectorAll('.qty-form').forEach(form => {
        const price = parseFloat(form.dataset.price);
        const qty = parseInt(form.querySelector('.qty-input').value, 10);
        if (!isNaN(price) && !isNaN(qty)) {
            total += price * qty;
        }
    });
    const totalEl = document.getElementById('cart-total-value');
    if (totalEl) {
        totalEl.textContent = '$' + total.toFixed(2);
    }
}

// Updates the quantity on screen instantly and saves it to the server in the background
function submitQtyForm(input) {
    // Validates the qty is between 1 and 99 and updates the input field to match
    let quantity = parseInt(input.value, 10);
    if (isNaN(quantity)) quantity = 1;
    quantity = Math.max(1, Math.min(quantity, 99));
    input.value = quantity;

    const form = input.closest('.qty-form');
    const price = parseFloat(form.dataset.price);

    // Updates the subtotal for this item on screen, hiding it if the quantity is 1
    const orderItem = form.closest('.checkout-order-item');
    const subtotalWrapper = orderItem.querySelector('.checkout-order-item-subtotal');
    const subtotalValue = orderItem.querySelector('.subtotal-value');
    if (quantity > 1) {
        subtotalWrapper.style.display = '';
        subtotalValue.textContent = (price * quantity).toFixed(2);
    } else {
        subtotalWrapper.style.display = 'none';
    }

    // Recalculates the overall Cart Total across every item on the page
    updateCartGrandTotal();

    // Saves the new quantity to the session in the background
    fetch(form.action, {
        method: 'POST',
        body: new FormData(form)
    }).catch(() => {
        // A failed background save shouldn't interrupt the quantity shown on screen
    });
}

// Increases or decreases a quantity input by 1, thens sends to submitQtyForm to update and save it
function adjustQty(button, delta) {
    const form = button.closest('form');
    const input = form.querySelector('.qty-input');
    let newValue = parseInt(input.value, 10) + delta;
    if (isNaN(newValue)) newValue = 1;
    newValue = Math.max(1, Math.min(newValue, 99));
    input.value = newValue;
    submitQtyForm(input);
}

// Restores correct details on screen if the user navigates back to the checkout page after leaving it
document.addEventListener('DOMContentLoaded', () => {
    loadBuilderPrices();
    updateSelectionDescription('bread');
    updateSelectionDescription('cheese');
    updateBuilderTotal();
});