document.addEventListener('DOMContentLoaded', function() {
    // 1. Код для фильтрации городов (оставляем без изменений)
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
    
    // Инициализация текущего города
    const activeButton = document.querySelector('.offices-filter__btn.active');
    if (activeButton) {
        const targetId = activeButton.getAttribute('data-target');
        document.querySelector(targetId).classList.add('active');
    }

    // 2. Код для формы обратной связи (упрощаем и исправляем)
    const feedbackForm = document.getElementById('feedback-form-submit');
    const modal = document.getElementById('feedback-form-modal');
    
    if (!feedbackForm || !modal) return;

    // Функции для работы с модальным окном
    function showModal() {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        modal.querySelector('#feedback-form-modal-close').focus();
    }

    function hideModal() {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }

    // Обработчик отправки формы
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
                'X-CSRFToken': feedbackForm.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                feedbackForm.reset();
                showModal();
            } else {
                // Обработка ошибок
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
            console.error('Error:', error);
            // Показываем сообщение об ошибке в модальном окне
            modal.querySelector('.feedback-form__modal-title').textContent = 'Ошибка';
            modal.querySelector('.feedback-form__modal-text').textContent = 'Произошла ошибка при отправке. Пожалуйста, попробуйте позже.';
            showModal();
        })
        .finally(() => {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        });
    });

    // Обработчики закрытия модального окна
    document.querySelector('.feedback-form__modal-close').addEventListener('click', hideModal);
    document.getElementById('feedback-form-modal-close').addEventListener('click', hideModal);
    
    // Закрытие при клике на фон
    modal.addEventListener('click', function(e) {
        if (e.target === this) hideModal();
    });

    // Закрытие по ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.style.display === 'flex') {
            hideModal();
        }
    });

    // 3. Инициализация маски телефона (если нужно)
    if (typeof Inputmask !== 'undefined' && document.getElementById('feedback-phone')) {
        new Inputmask('+7 (999) 999-99-99').mask(document.getElementById('feedback-phone'));
    }
});