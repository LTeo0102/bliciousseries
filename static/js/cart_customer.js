document.addEventListener("DOMContentLoaded", () => {
    const userId = localStorage.getItem("user_id");
    const cartKey = `cart_${userId}`;
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
                <td>RM ${(itemTotal).toFixed(2)}</td>
                <td><button type="button" onclick="deleteItem(${index})">🗑️</button></td>
            `;
            tbody.appendChild(row);
        });

        tfoot.innerHTML = `
            <tr>
                <td colspan="4"><strong>Cart Total</strong><br><small>(All items in cart)</small></td>
                <td colspan="2"><div id="cart-total">RM 0.00</div><div><strong>Selected:</strong> <span id="selected-total">RM 0.00</span></div></td>
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
    };

    window.deleteItem = function(index) {
        cart.splice(index, 1);
        localStorage.setItem(cartKey, JSON.stringify(cart));
        updateCartDisplay();
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

    document.addEventListener("change", function (e) {
        if (e.target.classList.contains("select-item") || e.target.id === "select-all") {
            updateTotal();
        }

        if (e.target.id === "select-all") {
            const isChecked = e.target.checked;
            document.querySelectorAll(".select-item").forEach(cb => cb.checked = isChecked);
            updateTotal();
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

        const shipping_name = document.getElementById("shipping_name").value.trim();
        const shipping_phone = document.getElementById("shipping_phone").value.trim();
        const shipping_address = document.getElementById("shipping_address").value.trim();
        const referral_code = document.getElementById("referral_code").value.trim();
        const receipt = document.getElementById("receipt");

        const nameRegex = /^[A-Za-z\s]{3,}$/;
        const phoneRegex = /^[0-9]{9,12}$/;
        const addressMinLength = 10;

        if (!shipping_name || !nameRegex.test(shipping_name)) {
            alert("Please enter a valid full name (e.g. Aina Binti Ahmad)");
            return;
        }

        if (!shipping_phone || !phoneRegex.test(shipping_phone)) {
            alert("Please enter a valid phone number (e.g. 0123456789)");
            return;
        }

        if (!shipping_address || shipping_address.length < addressMinLength) {
            alert("Please enter a valid shipping address (e.g. No 25, Jalan Melur 2, 83000 Batu Pahat)");
            return;
        }

        if (!receipt || !receipt.files[0]) {
            alert("Please upload your payment receipt.");
            return;
        }

        const formData = new FormData();
        formData.append("cart", JSON.stringify(selectedItems));
        formData.append("payment_status", "pay_now");
        formData.append("shipping_name", shipping_name);
        formData.append("shipping_phone", shipping_phone);
        formData.append("shipping_address", shipping_address);
        formData.append("referral_code", referral_code);
        formData.append("receipt", receipt.files[0]);

        fetch("/customer/checkout", {
            method: "POST",
            body: formData
        })
        .then(res => res.json().then(data => ({ status: res.status, body: data })))
        .then(response => {
            if (response.status === 200) {
                const usedReferral = referral_code.trim();
                const successMsg = usedReferral
                    ? `Order placed successfully! Referral code "${usedReferral}" has been applied. 🎉`
                    : "Order placed successfully! ✅";

                alert(successMsg);
                localStorage.removeItem(cartKey);
                window.location.href = "/customer/order";
            } else {
                alert(response.body.message);
            }
        })
        .catch(err => {
            console.error(err);
            alert("Something went wrong while placing your order.");
        });
    });

    let referralHintShown = false;
    const referralInput = document.getElementById("referral_code");
    referralInput.addEventListener("focus", () => {
        if (!referralHintShown && !referralInput.value.trim()) {
            alert("Enter a valid referral code (e.g. 250601 or ALICE01). Leave empty if not using.");
            referralHintShown = true;
        }
    });

    updateCartDisplay();
});
