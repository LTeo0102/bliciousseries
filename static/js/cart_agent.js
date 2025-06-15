document.addEventListener("DOMContentLoaded", () => {
    const userId = localStorage.getItem("user_id");
    const cartKey = `cart_agent_${userId}`;
    let cart = JSON.parse(localStorage.getItem(cartKey) || "[]");
    const tbody = document.getElementById("cart-body");
    const tfoot = document.getElementById("cart-summary-row");

    function updateCartDisplay() {
        tbody.innerHTML = "";
        let fullTotal = 0;

        cart.forEach((item, index) => {
            const itemTotal = item.price * item.quantity;
            fullTotal += itemTotal;
            const row = document.createElement("tr");
            row.innerHTML = `
                <td><input type="checkbox" class="select-item" data-index="${index}" checked></td>
                <td>${item.name}</td>
                <td>RM ${item.price.toFixed(2)}</td>
                <td>
                    <div class="quantity-buttons">
                        <button type="button" onclick="changeQuantity(${index}, -1)">−</button>
                        <input type="number" min="1" value="${item.quantity}" data-index="${index}" class="quantity-input">
                        <button type="button" onclick="changeQuantity(${index}, 1)">+</button>
                    </div>
                </td>
                <td>RM ${itemTotal.toFixed(2)}</td>
                <td><button type="button" onclick="deleteItem(${index})">🗑️</button></td>
            `;
            tbody.appendChild(row);
        });

        tfoot.innerHTML = `
            <tr>
                <td colspan="4"><strong>Cart Total</strong><br><small>(All items in cart)</small></td>
                <td colspan="2">
                    <div id="cart-total">RM 0.00</div>
                    <div><strong>Selected:</strong> <span id="selected-total">RM 0.00</span></div>
                </td>
            </tr>
        `;
        updateTotal();
    }

    function updateTotal() {
        const checkboxes = document.querySelectorAll(".select-item");
        let selectedTotal = 0;
        let cartTotal = 0;

        cart.forEach(item => {
            cartTotal += item.price * item.quantity;
        });

        checkboxes.forEach(cb => {
            if (cb.checked) {
                const idx = parseInt(cb.dataset.index);
                const item = cart[idx];
                selectedTotal += item.price * item.quantity;
            }
        });

        document.getElementById("cart-total").textContent = "RM " + cartTotal.toFixed(2);
        document.getElementById("selected-total").textContent = "RM " + selectedTotal.toFixed(2);
    }

    window.changeQuantity = function(index, delta) {
        cart[index].quantity = Math.max(1, cart[index].quantity + delta);
        localStorage.setItem(cartKey, JSON.stringify(cart));
        updateCartDisplay();
        updateCartBadge();
    };

    window.deleteItem = function(index) {
        cart.splice(index, 1);
        localStorage.setItem(cartKey, JSON.stringify(cart));
        updateCartDisplay();
        updateCartBadge();
    };

    tbody.addEventListener("input", function(e) {
        if (e.target.classList.contains("quantity-input")) {
            const index = parseInt(e.target.dataset.index);
            let newQty = parseInt(e.target.value);
            if (isNaN(newQty) || newQty < 1) newQty = 1;
            cart[index].quantity = newQty;
            localStorage.setItem(cartKey, JSON.stringify(cart));
            updateTotal();
            updateCartBadge();
        }
    });

    document.addEventListener("change", function(e) {
        if (e.target.classList.contains("select-item") || e.target.id === "select-all") {
            updateTotal();
        }

        if (e.target.id === "select-all") {
            const isChecked = e.target.checked;
            document.querySelectorAll(".select-item").forEach(cb => cb.checked = isChecked);
            updateTotal();
        }

        const payment = document.querySelector('input[name="payment"]:checked');
        const qrSection = document.getElementById("pay-now-section");
        if (payment && qrSection) {
            qrSection.style.display = payment.value === "now" ? "block" : "none";
        }
    });

    document.getElementById("checkoutForm").addEventListener("submit", (e) => {
        e.preventDefault();

        const selectedItems = [];
        document.querySelectorAll(".select-item").forEach(cb => {
            if (cb.checked) selectedItems.push(cart[cb.dataset.index]);
        });

        if (selectedItems.length === 0) {
            alert("Please select at least one item to checkout.");
            return;
        }

        const payLater = document.querySelector('input[name="payment"]:checked').value === "later";
        const receipt = document.getElementById("receipt");
        const shipping_name = document.getElementById("shipping_name").value.trim();
        const shipping_phone = document.getElementById("shipping_phone").value.trim();
        const shipping_address = document.getElementById("shipping_address").value.trim();

        if (!shipping_name || !shipping_phone || !shipping_address) {
            alert("Please fill in all shipping information.");
            return;
        }

        if (!payLater && (!receipt || !receipt.files[0])) {
            alert("Please upload a receipt before proceeding.");
            return;
        }

        const formData = new FormData();
        formData.append("cart", JSON.stringify(selectedItems));
        formData.append("payment_status", payLater ? "pay_later" : "pay_now");
        formData.append("shipping_name", shipping_name);
        formData.append("shipping_phone", shipping_phone);
        formData.append("shipping_address", shipping_address);
        if (!payLater && receipt.files[0]) {
            formData.append("receipt", receipt.files[0]);
        }

        fetch("/agent/checkout", {
            method: "POST",
            body: formData
        })
        .then(async res => {
            const data = await res.json();
            if (res.ok) {
                alert(data.message);
                localStorage.removeItem(cartKey);
                updateCartBadge();
                window.location.href = "/agent/order";
            } else {
                alert(data.message);
                throw new Error(data.message);
            }
        })
        .catch(err => {
            console.error("Checkout error:", err);
            if (!err.message) {
                alert("Failed to place order.");
            }
        });
    });

    function updateCartBadge() {
        const badge = document.getElementById("cart-count");
        const count = cart.reduce((sum, item) => sum + item.quantity, 0);
        if (badge) badge.textContent = count;
    }

    updateCartDisplay();
    updateCartBadge();
});
