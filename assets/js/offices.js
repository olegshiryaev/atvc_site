document.addEventListener('DOMContentLoaded', function() {
    const filterButtons = document.querySelectorAll('.offices-filter__btn');
    const history = window.history;
    
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            const localitySlug = this.getAttribute('data-locality-slug');
            
            // Обновляем URL без перезагрузки страницы
            if (history.pushState) {
                const newUrl = localitySlug ? `/offices/${localitySlug}/` : '/offices/';
                history.pushState(null, '', newUrl);
            }
            
            // Обновляем UI
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
});