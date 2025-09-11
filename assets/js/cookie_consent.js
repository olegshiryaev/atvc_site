document.addEventListener('DOMContentLoaded', () => {
    const cookieConsent = document.getElementById('cookie-consent');
    const acceptButton = document.getElementById('cookie-accept');
    const declineButton = document.getElementById('cookie-decline');

    // Проверяем, был ли сделан выбор ранее
    if (!localStorage.getItem('cookieConsent')) {
        cookieConsent.style.display = 'flex';
    }

    // Обработчик кнопки "Принять"
    acceptButton.addEventListener('click', () => {
        localStorage.setItem('cookieConsent', 'accepted');
        cookieConsent.style.display = 'none';
        // Разрешить загрузку Яндекс.Метрики (если она отключена по умолчанию)
    });

    // Обработчик кнопки "Отказаться"
    declineButton.addEventListener('click', () => {
        localStorage.setItem('cookieConsent', 'declined');
        cookieConsent.style.display = 'none';
        // Отключить Яндекс.Метрику (если требуется)
        window['disableYandexMetrika'] = true;
    });
});