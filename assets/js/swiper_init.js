document.addEventListener('DOMContentLoaded', () => {
    // Утилита для дебouncing
    const debounce = (func, wait) => {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    };

    // Инициализация всех Swiper
    document.querySelectorAll('[data-swiper]').forEach((container) => {
        const config = JSON.parse(container.dataset.swiper || '{}');
        const swiperContainer = container.querySelector('.swiper');
        const nextEl = container.querySelector('.slider-navs__next');
        const prevEl = container.querySelector('.slider-navs__prev');
        const paginationEl = container.querySelector('.slider-navs__pag');

        if (!swiperContainer) return; // Пропускаем, если .swiper не найден

        new Swiper(swiperContainer, {
            ...config,
            navigation: {
                nextEl,
                prevEl,
                disabledClass: 'slider-navs__btn--disabled', // Добавляем класс для неактивных кнопок
            },
            pagination: {
                el: paginationEl,
                clickable: true,
                bulletClass: 'slider-navs__bullet',
                bulletActiveClass: 'slider-navs__bullet--active',
            },
            lazy: {
                loadPrevNext: true,
                loadPrevNextAmount: 2,
                elementClass: 'swiper-lazy',
                preloaderClass: 'swiper-lazy-preloader',
            },
            a11y: {
                prevSlideMessage: 'Предыдущий слайд',
                nextSlideMessage: 'Следующий слайд',
                paginationBulletMessage: 'Перейти к слайду {{index}}',
            },
            watchOverflow: true, // Отключает навигацию, если слайдов мало
            on: {
                init: function () {
                    container.classList.add('swiper-ready');
                },
            },
        });
    });

    // Инициализация Swiper для тарифов
    function initOrUpdateSwipers() {
        document.querySelectorAll('.tariff-swiper').forEach((el) => {
            const wrapper = el.closest('.tariff-swiper-wrapper');
            if (!wrapper) return;

            if (!el.swiper) {
                new Swiper(el, {
                    slidesPerView: 1,
                    spaceBetween: 20,
                    loop: false,
                    watchOverflow: true,
                    pagination: {
                        el: wrapper.querySelector('.slider-navs__pag'),
                        clickable: true,
                        bulletClass: 'slider-navs__bullet',
                        bulletActiveClass: 'slider-navs__bullet--active',
                    },
                    navigation: {
                        nextEl: wrapper.querySelector('.slider-navs__next'),
                        prevEl: wrapper.querySelector('.slider-navs__prev'),
                        disabledClass: 'slider-navs__btn--disabled',
                    },
                    breakpoints: {
                        576: { slidesPerView: 1.2 },
                        768: { slidesPerView: 2 },
                        992: { slidesPerView: 3 },
                        1200: { slidesPerView: 4 },
                    },
                    on: {
                        init: function () {
                            wrapper.classList.add('swiper-ready');
                        },
                    },
                });
            } else {
                el.swiper.update();
            }
        });
    }

    initOrUpdateSwipers();

    // Обновление Swiper при переключении табов
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(btn => {
        btn.addEventListener('shown.bs.tab', () => {
            setTimeout(initOrUpdateSwipers, 50);
        });
    });

    // Поиск каналов
    document.addEventListener('input', debounce((event) => {
        const searchInput = event.target.closest('.channel-search');
        if (!searchInput) return;

        const tariffId = searchInput.id.split('-')[1];
        const channelList = document.getElementById(`channelList-${tariffId}`);
        const channelItems = channelList.querySelectorAll('.channel-item');
        const categoryHeaders = channelList.querySelectorAll('.category-header');
        const searchTerm = searchInput.value.toLowerCase();
        const visibleCategories = new Set();

        channelItems.forEach((item) => {
            const channelName = item.querySelector('span').textContent.toLowerCase();
            const isVisible = channelName.includes(searchTerm);
            item.style.display = isVisible ? '' : 'none';
            if (isVisible) visibleCategories.add(item.dataset.category);
        });

        categoryHeaders.forEach((header) => {
            header.style.display = visibleCategories.has(header.textContent) ? '' : 'none';
        });
    }, 200));

    // Обновление Swiper после HTMX
    document.addEventListener('htmx:afterSwap', () => {
        initOrUpdateSwipers();
    });
});