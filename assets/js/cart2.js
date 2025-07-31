function getCart() {
  const cart = localStorage.getItem("cart");
  if (cart) {
    return JSON.parse(cart);
  }
  return {
    tariff: null,
    products: {}, // key = "product_id:variant_id"
    services: [],
    tv_packages: []
  };
}

function saveCart(cart) {
  localStorage.setItem("cart", JSON.stringify(cart));
  updateCartCounter();
}

function updateCartCounter() {
  const cart = getCart();
  let total = 0;

  for (const key in cart.products) {
    total += cart.products[key].quantity;
  }
  total += cart.services.length + cart.tv_packages.length;
  if (cart.tariff) total += 1;

  const counterEl = document.querySelector("#cart-counter");
  if (counterEl) {
    counterEl.textContent = total;
  }
}

// ------- Тариф -------
function setTariff(tariffId) {
  const cart = getCart();
  cart.tariff = tariffId;
  saveCart(cart);
  showToast("Тариф выбран");
}

function clearTariff() {
  const cart = getCart();
  cart.tariff = null;
  saveCart(cart);
}

// ------- Оборудование (товары) -------
function addProduct(productId, variantId, price, quantity = 1) {
  const cart = getCart();
  const key = `${productId}:${variantId || "null"}`;
  if (cart.products[key]) {
    cart.products[key].quantity += quantity;
  } else {
    cart.products[key] = {
      quantity,
      price
    };
  }
  saveCart(cart);
  showToast("Оборудование добавлено");
}

function removeProduct(productId, variantId) {
  const cart = getCart();
  const key = `${productId}:${variantId || "null"}`;
  delete cart.products[key];
  saveCart(cart);
}

// ------- Доп. услуги -------
function addService(serviceId) {
  const cart = getCart();
  if (!cart.services.includes(serviceId)) {
    cart.services.push(serviceId);
    saveCart(cart);
    showToast("Услуга добавлена");
  }
}

function removeService(serviceId) {
  const cart = getCart();
  cart.services = cart.services.filter(id => id !== serviceId);
  saveCart(cart);
}

// ------- ТВ-пакеты -------
function addTVPackage(packageId) {
  const cart = getCart();
  if (!cart.tv_packages.includes(packageId)) {
    cart.tv_packages.push(packageId);
    saveCart(cart);
    showToast("ТВ-пакет добавлен");
  }
}

function removeTVPackage(packageId) {
  const cart = getCart();
  cart.tv_packages = cart.tv_packages.filter(id => id !== packageId);
  saveCart(cart);
}

// ------- Очистка корзины -------
function clearCart() {
  const cart = {
    tariff: null,
    products: {},
    services: [],
    tv_packages: []
  };
  saveCart(cart);
  showToast("Корзина очищена");
}

// ------- Отправка корзины на сервер (пример через fetch) -------
function submitCartForm(endpointUrl) {
  const cart = getCart();
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

  fetch(endpointUrl, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken
    },
    body: JSON.stringify(cart)
  })
  .then(response => {
    if (response.ok) {
      showToast("Заявка отправлена");
      clearCart();
    } else {
      alert("Ошибка при отправке заявки");
    }
  })
  .catch(() => alert("Ошибка сети"));
}

// ------- Уведомления -------
function showToast(message) {
  alert(message); // можно заменить на кастомный всплывающий элемент
}

document.addEventListener("click", function (e) {
  if (e.target.closest("[data-add-package-cart]")) {
    const btn = e.target.closest("[data-add-package-cart]");
    const id = parseInt(btn.dataset.packageId);
    addTVPackage(id);
  }
});