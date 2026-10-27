
document.addEventListener("DOMContentLoaded", function () {
    const cartButtons = document.querySelectorAll(".product-card button");
    const cartCount = document.getElementById("cart-count");
    const cartItems = document.getElementById("cart-items");
    const cartTotal = document.getElementById("cart-total");
    const clearCartButton = document.getElementById("clear-cart");
    const checkoutButton = document.getElementById("checkout-button");

    let cart = [];

    try {
        cart = JSON.parse(localStorage.getItem("shopEaseCart")) || [];
        if (!Array.isArray(cart)) cart = [];
    } catch (error) {
        console.error("Unable to load cart:", error);
        cart = [];
    }

    // Change the checkout button into an arrow
    checkoutButton.textContent = "→";
    checkoutButton.classList.add("checkout-arrow-button");
    checkoutButton.setAttribute("aria-label", "Continue to checkout");
    checkoutButton.setAttribute("title", "Continue to checkout");

    function updateCart() {
        const totalItems = cart.reduce(function (total, item) {
            return total + item.quantity;
        }, 0);

        const totalPrice = cart.reduce(function (total, item) {
            return total + item.price * item.quantity;
        }, 0);

        cartCount.textContent = totalItems;
        cartTotal.textContent = totalPrice.toLocaleString("en-IN");

        localStorage.setItem("shopEaseCart", JSON.stringify(cart));
        localStorage.setItem("cartCount", totalItems);

        if (cart.length === 0) {
            cartItems.textContent = "Your cart is empty.";
            return;
        }

        cartItems.innerHTML = "";

        cart.forEach(function (item) {
            const product = document.createElement("div");
            product.classList.add("cart-product");

            const name = document.createElement("h3");
            name.textContent = item.name;

            const details = document.createElement("p");
            details.textContent =
                "Price: ₹" + item.price.toLocaleString("en-IN") +
                " | Subtotal: ₹" +
                (item.price * item.quantity).toLocaleString("en-IN");

            // Decrease quantity; remove product when quantity reaches zero
            const decreaseButton = document.createElement("button");
            decreaseButton.textContent = "−";
            decreaseButton.type = "button";
            decreaseButton.setAttribute("aria-label", "Decrease quantity");

            decreaseButton.addEventListener("click", function () {
                item.quantity--;

                if (item.quantity <= 0) {
                    cart = cart.filter(function (cartItem) {
                        return cartItem !== item;
                    });
                }

                updateCart();
            });

            // Quantity number box
            const quantityInput = document.createElement("input");
            quantityInput.type = "number";
            quantityInput.min = "1";
            quantityInput.max = "999";
            quantityInput.step = "1";
            quantityInput.value = item.quantity;
            quantityInput.classList.add("cart-quantity-input");
            quantityInput.setAttribute("aria-label", "Quantity for " + item.name);

            quantityInput.addEventListener("change", function () {
                const newQuantity = Number(quantityInput.value);

                if (!Number.isInteger(newQuantity) || newQuantity < 1) {
                    cart = cart.filter(function (cartItem) {
                        return cartItem !== item;
                    });
                } else {
                    item.quantity = Math.min(newQuantity, 999);
                }

                updateCart();
            });

            // Increase quantity
            const increaseButton = document.createElement("button");
            increaseButton.textContent = "+";
            increaseButton.type = "button";
            increaseButton.setAttribute("aria-label", "Increase quantity");

            increaseButton.addEventListener("click", function () {
                if (item.quantity < 999) {
                    item.quantity++;
                    updateCart();
                }
            });

            product.appendChild(name);
            product.appendChild(details);
            product.appendChild(decreaseButton);
            product.appendChild(quantityInput);
            product.appendChild(increaseButton);

            // No separate Remove button
            cartItems.appendChild(product);
        });
    }

    // Add products to cart
    cartButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            const productCard = button.closest(".product-card");
            const productName = productCard.querySelector("h3").textContent;
            const priceText = productCard.querySelector(".price").textContent;
            const price = Number(priceText.replace(/[^\d.]/g, ""));

            const existingProduct = cart.find(function (item) {
                return item.name === productName;
            });

            if (existingProduct) {
                if (existingProduct.quantity < 999) {
                    existingProduct.quantity++;
                }
            } else {
                cart.push({
                    name: productName,
                    price: price,
                    quantity: 1
                });
            }

            updateCart();
            alert(productName + " added to cart!");
        });
    });

    // Clear the entire cart
    clearCartButton.addEventListener("click", function () {
        if (cart.length === 0) {
            alert("Your cart is already empty.");
            return;
        }

        const confirmClear = confirm(
            "Are you sure you want to remove all products from your cart?"
        );

        if (confirmClear) {
            cart = [];
            updateCart();
        }
    });

    // Navigate to checkout using the arrow button
    checkoutButton.addEventListener("click", function () {
        if (cart.length === 0) {
            alert("Your cart is empty. Please add a product first.");
            return;
        }

        window.location.href = "/checkout";
    });

    updateCart();
});
