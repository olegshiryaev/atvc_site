document.addEventListener('DOMContentLoaded', function() {
    // 1. Фильтр по городам
    const filterButtons = document.querySelectorAll('.offices-filter__btn');
    const history = window.history;

    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            const localitySlug = this.getAttribute('data-locality-slug');

            if (history.pushState) {
                const newUrl = localitySlug ? `/offices/${localitySlug}/` : '/offices/';
                history.pushState(null, '', newUrl);
            }

            filterButtons.forEach(btn => {
                btn.classList.remove('active');
                btn.setAttribute('aria-selected', 'false');
            });

            this.classList.add('active');
            this.setAttribute('aria-selected', 'true');

            document.querySelectorAll('.offices-city').forEach(city => {
                city.classList.remove('active');
            });

            const targetId = this.getAttribute('data-target');
            document.querySelector(targetId).classList.add('active');
        });
    });

    const activeButton = document.querySelector('.offices-filter__btn.active');
    if (activeButton) {
        const targetId = activeButton.getAttribute('data-target');
        document.querySelector(targetId).classList.add('active');
    }

    // 2. Форма обратной связи
    const feedbackForm = document.getElementById('feedback-form-submit');
    const modal = document.getElementById('feedback-form-modal');

    if (!feedbackForm || !modal) return;

    function showModal() {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        modal.querySelector('#feedback-form-modal-close').focus();
    }

    function hideModal() {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }

    feedbackForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const submitBtn = feedbackForm.querySelector('.btn-submit');
        const originalText = submitBtn.textContent;

        submitBtn.disabled = true;
        submitBtn.textContent = 'Отправка...';

        fetch(feedbackForm.action, {
            method: 'POST',
            body: new FormData(feedbackForm),
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': feedbackForm.querySelector('[name=csrfmiddlewaretoken]').value,
                'Accept': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                feedbackForm.reset();
                showModal();
            } else {
                Object.keys(data.errors).forEach(field => {
                    const errorElement = document.getElementById(`error_${field}`);
                    if (errorElement) {
                        errorElement.textContent = data.errors[field][0];
                        errorElement.style.display = 'block';
                    }
                });
            }
        })
        .catch(error => {
            console.error('Fetch error:', error);
            fetch(feedbackForm.action)  // попробуем получить ответ как текст
                .then(r => r.text())
                .then(text => {
                    console.log('Full response HTML:', text.substring(0, 500)); // первые 500 символов
                });
            // Показываем ошибку
            modal.querySelector('.feedback-form__modal-title').textContent = 'Ошибка';
            modal.querySelector('.feedback-form__modal-text').textContent = 'Произошла ошибка. См. консоль.';
            showModal();
        })
        .finally(() => {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        });
    });

    document.querySelector('.feedback-form__modal-close').addEventListener('click', hideModal);
    document.getElementById('feedback-form-modal-close').addEventListener('click', hideModal);

    modal.addEventListener('click', function(e) {
        if (e.target === this) hideModal();
    });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.style.display === 'flex') {
            hideModal();
        }
    });

    // 3. Маска телефона
    if (typeof Inputmask !== 'undefined' && document.getElementById('feedback-phone')) {
        new Inputmask('+7 (999) 999-99-99').mask(document.getElementById('feedback-phone'));
    }
});