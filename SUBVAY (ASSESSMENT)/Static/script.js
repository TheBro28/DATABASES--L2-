// Switches between showing the login box or the register box
function showForm(formId) {
    // Hides whichever box is currently showing
    document.querySelectorAll(".form-box").forEach(form => form.classList.remove("active"));
    
    // Shows the one that was clicked on
    document.getElementById(formId).classList.add("active");
}

// Reads the bread/cheese/sauce/topping prices off the page, ready for the price calculator to use
function loadBuilderPrices() {
    const breadData = document.getElementById('bread-prices-data');
    // Skips this on any page that isn't the sandwich builder
    if (!breadData) return;

    window.breadPrices = JSON.parse(breadData.textContent);
    window.cheesePrices = JSON.parse(document.getElementById('cheese-prices-data').textContent);
    window.saucePrices = JSON.parse(document.getElementById('sauce-prices-data').textContent);
    window.toppingPrices = JSON.parse(document.getElementById('topping-prices-data').textContent);
}

// Shows the description for whichever bread or cheese is currently picked
function updateSelectionDescription(type) {
    const select = document.getElementById(type + '-select');
    // Skips this on any page that isn't the sandwich builder
    if (!select) return;

    const selectedId = select.value;

    // Hides every description first
    document.querySelectorAll('.' + type + '-description-block').forEach(block => {
        block.classList.remove('active-description');
    });

    // Shows only the one that matches what's picked
    const activeBlock = document.getElementById(type + '-desc-' + selectedId);
    if (activeBlock) {
        activeBlock.classList.add('active-description');
    }
}

// Works out the running total on the sandwich builder page, without needing to reload the page
function updateBuilderTotal() {
    const breadSelect = document.getElementById('bread-select');
    // Skips this on any page that isn't the sandwich builder
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

    // The "Add to Cart" button stays greyed out until a bread and cheese have both been picked
    document.getElementById('add-to-cart-btn').disabled = !(breadId && cheeseId);
}

// Quietly saves what's been picked so far, so it isn't lost if the customer leaves the page
function syncBuilderSelection() {
    const form = document.getElementById('builder-form');
    if (!form) return;

    fetch('/custom-sandwich/save-progress', {
        method: 'POST',
        body: new FormData(form)
    }).catch(() => {
        // If this quiet save fails, it's not worth bothering the customer about
    });
}

// Runs everything that needs to happen when something changes on the sandwich builder
function handleBuilderChange(type) {
    if (type === 'bread' || type === 'cheese') {
        updateSelectionDescription(type);
    }
    updateBuilderTotal();
    syncBuilderSelection();
}

// Opens the time picker when the clock is clicked, instead of only the tiny text box
function openTimePicker(event) {
    const input = document.getElementById('pickup-time-input');
    if (!input) return;
    // Stops it from opening twice if the click landed on the box itself
    if (event.target === input) return;
    if (input.showPicker) {
        input.showPicker();
    } else {
        input.focus();
    }
}

// Adds up every item in the cart and updates the total shown on the checkout page
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

// Updates a sandwich's quantity on screen straight away, and saves it in the background
function submitQtyForm(input) {
    // Keeps the number between 1 and 99
    let quantity = parseInt(input.value, 10);
    if (isNaN(quantity)) quantity = 1;
    quantity = Math.max(1, Math.min(quantity, 99));
    input.value = quantity;

    const form = input.closest('.qty-form');
    const price = parseFloat(form.dataset.price);

    // Updates this item's own subtotal, hiding it again if there's only 1
    const orderItem = form.closest('.checkout-order-item');
    const subtotalWrapper = orderItem.querySelector('.checkout-order-item-subtotal');
    const subtotalValue = orderItem.querySelector('.subtotal-value');
    if (quantity > 1) {
        subtotalWrapper.style.display = '';
        subtotalValue.textContent = (price * quantity).toFixed(2);
    } else {
        subtotalWrapper.style.display = 'none';
    }

    // Updates the overall cart total too
    updateCartGrandTotal();

    // Saves the new quantity in the background, without reloading the page
    fetch(form.action, {
        method: 'POST',
        body: new FormData(form)
    }).catch(() => {
        // If this quiet save fails, the number on screen still stays correct for now
    });
}

// Handles clicking the + or - buttons next to a sandwich's quantity
function adjustQty(button, delta) {
    const form = button.closest('form');
    const input = form.querySelector('.qty-input');
    let newValue = parseInt(input.value, 10) + delta;
    if (isNaN(newValue)) newValue = 1;
    newValue = Math.max(1, Math.min(newValue, 99));
    input.value = newValue;
    submitQtyForm(input);
}

// Sets everything up correctly when a page first loads
document.addEventListener('DOMContentLoaded', () => {
    loadBuilderPrices();
    updateSelectionDescription('bread');
    updateSelectionDescription('cheese');
    updateBuilderTotal();
});