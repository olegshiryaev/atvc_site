document.addEventListener('DOMContentLoaded', function() {
    console.log('Cart system initialized');

    // Основные элементы
    const cartCounter = document.getElementById('cart-counter');
    const cartIcon = document.querySelector('.cart-icon');

    // Инициализация корзины
    initCart();

    // Обработчики кнопок
    document.querySelectorAll('[data-add-to-cart]').forEach(button => {
        button.addEventListener('click', handleAddToCart);
    });

    // Функция инициализации
    async function initCart() {
        try {
            const localitySlug = getCurrentLocality();
            const response = await fetch(`/${localitySlug}/get-cart-count/`);
            const data = await response.json();
            
            if (data.success) {
                updateCartCounter(data.items_count);
            }
        } catch (error) {
            console.error('Cart init error:', error);
        }
    }

    // Обработчик добавления в корзину
    async function handleAddToCart(e) {
        e.preventDefault();
        e.stopImmediatePropagation();

        const button = e.currentTarget;
        if (button.disabled || button.classList.contains('processing')) return;

        const productCard = button.closest('.product-card');
        const productId = productCard.dataset.productId;
        const priceText = productCard.querySelector('.product-card__price').textContent;

        if (!productId || priceText.includes('запросу')) {
            showToast('Этот товар недоступен для заказа', 'error');
            return;
        }

        setButtonState(button, 'loading');

        try {
            const localitySlug = getCurrentLocality();
            const response = await fetch(`/${localitySlug}/add-to-cart/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `model_type=product&object_id=${productId}`
            });

            const data = await response.json();

            if (data.success) {
                updateCartCounter(data.items_count);
                showToast('Товар добавлен в корзину', 'success');
                animateCartIcon();
                setButtonState(button, 'success');
            } else {
                throw new Error(data.error || 'Ошибка сервера');
            }
        } catch (error) {
            console.error('Add to cart error:', error);
            showToast(error.message, 'error');
            setButtonState(button, 'error');
        } finally {
            setTimeout(() => setButtonState(button, 'reset'), 2000);
        }
    }

    // Вспомогательные функции
    function getCurrentLocality() {
        return window.location.pathname.split('/')[1] || 'default';
    }

    function updateCartCounter(count) {
        if (cartCounter) {
            cartCounter.textContent = count;
            cartCounter.classList.add('updated');
            setTimeout(() => cartCounter.classList.remove('updated'), 500);
        }
    }

    function animateCartIcon() {
        if (cartIcon) {
            cartIcon.classList.add('animate');
            setTimeout(() => cartIcon.classList.remove('animate'), 500);
        }
    }

    function setButtonState(button, state) {
        const originalText = button.dataset.originalText || button.textContent;
        button.dataset.originalText = originalText;

        switch (state) {
            case 'loading':
                button.innerHTML = `
                    <span class="button-loader"></span>
                    <span class="button-text">Добавление...</span>
                `;
                button.classList.add('processing');
                button.disabled = true;
                break;
                
            case 'success':
                button.innerHTML = `
                    <span class="button-icon">✓</span>
                    <span class="button-text">Добавлено</span>
                `;
                button.classList.add('success');
                break;
                
            case 'error':
                button.textContent = 'Ошибка';
                button.classList.add('error');
                break;
                
            case 'reset':
                button.innerHTML = originalText;
                button.classList.remove('processing', 'success', 'error');
                button.disabled = false;
                break;
        }
    }

    function showToast(message, type = 'success') {
        // Реализация toast-уведомлений (адаптируйте под свою систему)
        console.log(`${type.toUpperCase()}: ${message}`);
    }

    function getCookie(name) {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [key, value] = cookie.trim().split('=');
            if (key === name) return decodeURIComponent(value);
        }
        return null;
    }
});