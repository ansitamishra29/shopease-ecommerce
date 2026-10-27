
document.addEventListener("DOMContentLoaded", function () {
    const checkoutItems = document.getElementById("checkout-items");
    const checkoutTotal = document.getElementById("checkout-total");
    const checkoutForm = document.getElementById("checkout-form");
    const checkoutMessage = document.getElementById("checkout-message");

    // Check that the checkout page elements exist
    if (!checkoutItems || !checkoutTotal || !checkoutForm || !checkoutMessage) {
        console.error("Checkout page elements are missing.");
        return;
    }

    // Load the saved cart
    let cart = [];

    try {
        cart = JSON.parse(localStorage.getItem("shopEaseCart")) || [];
    } catch (error) {
        console.error("Unable to read the saved cart:", error);
    }

    // Display an empty-cart message
    if (!Array.isArray(cart) || cart.length === 0) {
        checkoutItems.textContent = "Your cart is empty.";
        checkoutTotal.textContent = "0";
        checkoutForm.style.display = "none";

        checkoutMessage.textContent =
            "Please return to the homepage and add products to your cart.";

        return;
    }

    // Display cart products and calculate the total
    let totalPrice = 0;
    let validCart = true;

    cart.forEach(function (item) {
        const price = Number(item.price);
        const quantity = Number(item.quantity);

        if (
            !item ||
            typeof item.name !== "string" ||
            !Number.isFinite(price) ||
            !Number.isInteger(quantity) ||
            price < 0 ||
            quantity < 1
        ) {
            validCart = false;
            return;
        }

        const subtotal = price * quantity;
        totalPrice += subtotal;

        const product = document.createElement("p");

        product.textContent =
            item.name + " × " + quantity +
            " — ₹" + subtotal.toLocaleString("en-IN");

        checkoutItems.appendChild(product);
    });

    if (!validCart) {
        checkoutItems.textContent =
            "Your cart contains invalid product information. Please return to the homepage and update your cart.";

        checkoutForm.style.display = "none";
        checkoutTotal.textContent = "0";
        return;
    }

    checkoutTotal.textContent = totalPrice.toLocaleString("en-IN");

    // Submit the order to the Flask backend
    checkoutForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        const customerName =
            document.getElementById("customer-name").value.trim();

        const customerAddress =
            document.getElementById("customer-address").value.trim();

        const customerPhone =
            document.getElementById("customer-phone").value.trim();

        // Validate customer details
        if (!customerName || !customerAddress) {
            checkoutMessage.textContent =
                "Please enter your full name and delivery address.";
            return;
        }

        if (!/^\d{10}$/.test(customerPhone)) {
            checkoutMessage.textContent =
                "Please enter a valid 10-digit phone number.";
            return;
        }

        if (!validCart || cart.length === 0) {
            checkoutMessage.textContent =
                "Your cart is empty or contains invalid items.";
            return;
        }

        const submitButton =
            checkoutForm.querySelector('button[type="submit"]');

        submitButton.disabled = true;

        checkoutMessage.style.display = "block";
        checkoutMessage.style.color = "#333";
        checkoutMessage.style.backgroundColor = "#f0f0f0";
        checkoutMessage.style.padding = "12px";
        checkoutMessage.style.borderRadius = "8px";
        checkoutMessage.textContent = "Saving your order. Please wait...";

        try {
            const response = await fetch("/place-order", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    customer_name: customerName,
                    customer_address: customerAddress,
                    customer_phone: customerPhone,
                    items: cart
                })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(
                    result.message || "Unable to save your order."
                );
            }

            // Show confirmation only after the server confirms success
            checkoutMessage.style.color = "#245c32";
            checkoutMessage.style.backgroundColor = "#e6f7e9";

            checkoutMessage.textContent =
                "Thank you, " + customerName + "! " +
                result.message + " Your Order ID is " +
                result.order_id + ".";

            // Clear the saved cart after successful order creation
            localStorage.removeItem("shopEaseCart");
            localStorage.removeItem("cartCount");

            checkoutForm.reset();
            checkoutForm.style.display = "none";

        } catch (error) {
            console.error("Order submission error:", error);

            checkoutMessage.style.color = "#a12626";
            checkoutMessage.style.backgroundColor = "#fdeaea";

            checkoutMessage.textContent =
                error.message ||
                "Unable to submit your order. Please try again.";
        } finally {
            submitButton.disabled = false;
        }
    });
});
