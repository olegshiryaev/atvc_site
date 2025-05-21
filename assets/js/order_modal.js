document.addEventListener('DOMContentLoaded', function () {
    const modal = document.getElementById('orderModal');
    if (!modal) return;

    // Общая функция для проверки заполненности формы
    function checkFormValidity(form) {
        const nameInput = form.querySelector('[name="name"]');
        const phoneInput = form.querySelector('[name="phone"]');
        const privacyInput = form.querySelector('[name="privacy"]');
        const submitBtn = form.querySelector('button[type="submit"]');

        if (!nameInput || !phoneInput || !privacyInput || !submitBtn) return;

        const isNameFilled = nameInput.value.trim() !== '';
        const isPhoneValid = validatePhone(phoneInput.value);
        const isPrivacyChecked = privacyInput.checked;

        submitBtn.disabled = !(isNameFilled && isPhoneValid && isPrivacyChecked);
    }

    // Валидация телефона
    function validatePhone(phoneValue) {
        return phoneValue.replace(/[^0-9]/g, '').length === 11;
    }

    // Инициализация маски телефона
    function initPhoneMask(input) {
        if (input._imask) input._imask.destroy(); // очищаем предыдущую маску
        return IMask(input, {
            mask: '+7(000)000-0000',
            lazy: false,
            placeholderChar: '_'
        });
    }

    // Функция добавления обработчиков кнопок "Подключить"
    function addConnectButtonListeners() {
        const connectButtons = document.querySelectorAll('.connect-btn');
        connectButtons.forEach(button => {
            button.addEventListener('click', function () {
                const tariffName = this.dataset.tariffName || '';
                const localitySlug = this.dataset.localitySlug || window.localitySlug || '';

                const modalTitle = document.getElementById('orderModalLabel');
                const form = document.getElementById('orderForm');
                const nameInput = form.querySelector('[name="name"]');
                const phoneInput = form.querySelector('[name="phone"]');
                const streetInput = form.querySelector('[name="street"]');
                const houseNumberInput = form.querySelector('[name="house_number"]');
                const commentInput = form.querySelector('[name="comment"]');
                const privacyInput = form.querySelector('[name="privacy"]');
                const formErrors = document.getElementById('orderFormErrors');
                const formContainer = document.getElementById('orderFormContainer');
                const successMessage = document.getElementById('orderSuccessMessage');
                const submitBtn = form.querySelector('#submitOrderBtn');

                modalTitle.textContent = 'Оставить заявку';
                const bsModal = new bootstrap.Modal(modal);
                bsModal.show();
                setTimeout(() => { nameInput.focus(); }, 50);

                let phoneMask = initPhoneMask(phoneInput);

                // Очистка формы
                form.reset();
                if (commentInput) commentInput.value = tariffName ? `Тариф: ${tariffName}` : '';
                if (formErrors) {
                    formErrors.classList.add('hidden');
                    formErrors.textContent = '';
                }
                ['nameError', 'phoneError', 'streetError', 'house_numberError', 'commentError', 'privacyError'].forEach(id => {
                    const errorDiv = document.getElementById(id);
                    if (errorDiv) {
                        errorDiv.textContent = '';
                        errorDiv.classList.remove('d-block');
                    }
                });
                ['name', 'phone', 'street', 'house_number', 'comment', 'privacy'].forEach(name => {
                    const input = form.querySelector(`[name="${name}"]`);
                    if (input) input.classList.remove('is-invalid');
                });
                if (submitBtn) submitBtn.disabled = true;

                // Слушатели полей
                form.querySelectorAll('[name="name"], [name="phone"], [name="street"], [name="house_number"], [name="comment"], [name="privacy"]').forEach(input => {
                    input.addEventListener('input', () => checkFormValidity(form));
                });

                // Отправка формы
                form.onsubmit = async function (e) {
                    e.preventDefault();
                    const formData = new FormData(form);
                    const csrfToken = form.querySelector('[name=csrfmiddlewaretoken]').value;
                    formData.append('csrfmiddlewaretoken', csrfToken);

                    try {
                        const submitUrl = `/${localitySlug}/application/submit/`;
                        const response = await fetch(submitUrl, {
                            method: 'POST',
                            body: formData,
                            headers: {
                                'X-Requested-With': 'XMLHttpRequest'
                            }
                        });
                        const data = await response.json();

                        if (response.ok && data.success) {
                            formContainer.classList.add('hidden');
                            successMessage.classList.remove('hidden');
                            // Автозакрытие через 5 секунд
                            setTimeout(() => {
                                bsModal.hide();
                            }, 5000);
                        } else {
                            if (data.errors) {
                                for (const [field, errors] of Object.entries(data.errors)) {
                                    const errorDiv = document.getElementById(`${field}Error`);
                                    if (errorDiv) {
                                        errorDiv.textContent = errors.join(' ');
                                        errorDiv.classList.add('d-block');
                                        const input = form.querySelector(`[name="${field}"]`);
                                        if (input) input.classList.add('is-invalid');
                                    }
                                }
                            } else if (formErrors) {
                                formErrors.classList.remove('hidden');
                                formErrors.textContent = data.error || 'Произошла ошибка при отправке';
                            }
                        }
                    } catch (error) {
                        console.error('Ошибка:', error);
                        if (formErrors) {
                            formErrors.classList.remove('hidden');
                            formErrors.textContent = `Ошибка: ${error.message}`;
                        }
                    }
                };

                // Очистка слушателей и маски при закрытии
                modal.addEventListener('hidden.bs.modal', () => {
                    if (phoneMask) phoneMask.destroy();
                    form.querySelectorAll('[name="name"], [name="phone"], [name="street"], [name="house_number"], [name="comment"], [name="privacy"]').forEach(input => {
                        input.removeEventListener('input', () => checkFormValidity(form));
                    });
                }, { once: true });
            });
        });
    }

    // Добавляем обработчики к кнопкам "Подключить"
    addConnectButtonListeners();
});