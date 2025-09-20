document.addEventListener('DOMContentLoaded', () => {
    const debounce = (func, wait) => {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    };

    function initOrUpdateSwipers() {
        console.log('Initializing Swipers...'); // Для отладки

        // Тарифы
        document.querySelectorAll('.tariff-swiper').forEach((el) => {
            const wrapper = el.closest('.tariff-swiper-wrapper');
            if (!wrapper) {
                console.warn('No tariff-swiper-wrapper found for:', el);
                return;
            }

            if (window.innerWidth >= 576) {
                if (!el.swiper) {
                    console.log('Initializing Swiper for tariffs:', el);
                    new Swiper(el, {
                        slidesPerView: 1.1,
                        spaceBetween: 30,
                        loop: false,
                        watchOverflow: true,
                        grabCursor: true,
                        pagination: {
                            el: wrapper.querySelector('.slider-navs__pag'),
                            clickable: true,
                        },
                        navigation: {
                            nextEl: wrapper.querySelector('.slider-navs__next'),
                            prevEl: wrapper.querySelector('.slider-navs__prev'),
                        },
                        breakpoints: {
                            576: { slidesPerView: 1.2 },
                            768: { slidesPerView: 2 },
                            992: { slidesPerView: 3 },
                            1200: { slidesPerView: 4 },
                        },
                        a11y: {
                            prevSlideMessage: 'Предыдущий слайд',
                            nextSlideMessage: 'Следующий слайд',
                            paginationBulletMessage: 'Перейти к слайду {{index}}',
                        },
                        on: {
                            init: function () {
                                console.log('Tariff Swiper initialized:', this.el);
                                this.el.classList.remove('swiper-container--not-ready');
                                this.el.classList.add('swiper-container--ready');
                            },
                        },
                    });
                } else {
                    el.swiper.update();
                }
            } else {
                if (el.swiper) {
                    console.log('Destroying Swiper for tariffs:', el);
                    el.swiper.destroy(true, true);
                }
                el.classList.remove('swiper-container--not-ready', 'swiper-container--ready');
            }
        });

        // Продукты
        document.querySelectorAll('.products-slider-block .swiper').forEach((el) => {
            const wrapper = el.closest('.products-slider-block__wrapper');
            if (!wrapper) {
                console.warn('No products-slider-block__wrapper found for:', el);
                return;
            }
            if (!el.swiper) {
                console.log('Initializing Swiper for products:', el);
                new Swiper(el, {
                    slidesPerView: 1.1,
                    spaceBetween: 24,
                    loop: false,
                    pagination: {
                        el: wrapper.querySelector('.slider-navs__pag'),
                        clickable: true,
                    },
                    navigation: {
                        nextEl: wrapper.querySelector('.slider-navs__next'),
                        prevEl: wrapper.querySelector('.slider-navs__prev'),
                    },
                    breakpoints: {
                        640: { slidesPerView: 2, spaceBetween: 20 },
                        1024: { slidesPerView: 4, spaceBetween: 30 },
                    },
                    a11y: {
                        prevSlideMessage: 'Предыдущий слайд',
                        nextSlideMessage: 'Следующий слайд',
                        paginationBulletMessage: 'Перейти к слайду {{index}}',
                    },
                    on: {
                        init: function () {
                            console.log('Products Swiper initialized:', this.el);
                            this.el.classList.remove('swiper-container--not-ready');
                            this.el.classList.add('swiper-container--ready');
                        },
                    },
                });
            } else {
                el.swiper.update();
            }
        });

        // Преимущества
        document.querySelectorAll('.advantages-block .swiper').forEach((el) => {
            if (!el.swiper) {
                console.log('Initializing Swiper for advantages:', el);
                new Swiper(el, {
                    slidesPerView: 1,
                    spaceBetween: 30,
                    loop: false,
                    pagination: {
                        el: '.advantages-block .slider-navs__pag',
                        clickable: true,
                    },
                    navigation: {
                        nextEl: '.advantages-block .slider-navs__next',
                        prevEl: '.advantages-block .slider-navs__prev',
                    },
                    breakpoints: {
                        768: { slidesPerView: 2.2 },
                        1024: { slidesPerView: 3.2 },
                        1200: { slidesPerView: 4 },
                    },
                    a11y: {
                        prevSlideMessage: 'Предыдущий слайд',
                        nextSlideMessage: 'Следующий слайд',
                        paginationBulletMessage: 'Перейти к слайду {{index}}',
                    },
                    on: {
                        init: function () {
                            console.log('Advantages Swiper initialized:', this.el);
                            this.el.classList.remove('swiper-container--not-ready');
                            this.el.classList.add('swiper-container--ready');
                        },
                    },
                });
            } else {
                el.swiper.update();
            }
        });

        // ТВ-пакеты
        document.querySelectorAll('.tv-packages-block .swiper').forEach((el) => {
            if (!el.swiper) {
                console.log('Initializing Swiper for tv-packages:', el);
                new Swiper(el, {
                    slidesPerView: 1,
                    spaceBetween: 20,
                    loop: false,
                    pagination: {
                        el: '.tv-packages-block .slider-navs__pag',
                        clickable: true,
                    },
                    navigation: {
                        nextEl: '.tv-packages-block .slider-navs__next',
                        prevEl: '.tv-packages-block .slider-navs__prev',
                    },
                    lazy: {
                        loadPrevNext: true,
                    },
                    breakpoints: {
                        640: { slidesPerView: 2, spaceBetween: 20 },
                        1024: { slidesPerView: 4, spaceBetween: 30 },
                    },
                    a11y: {
                        prevSlideMessage: 'Предыдущий слайд',
                        nextSlideMessage: 'Следующий слайд',
                        paginationBulletMessage: 'Перейти к слайду {{index}}',
                    },
                    on: {
                        init: function () {
                            console.log('TV Packages Swiper initialized:', this.el);
                            this.el.classList.remove('swiper-container--not-ready');
                            this.el.classList.add('swiper-container--ready');
                        },
                    },
                });
            } else {
                el.swiper.update();
            }
        });

        // Новости
        document.querySelectorAll('.main_news-block__wrapper_slider .swiper').forEach((el) => {
            const wrapper = el.closest('.main_news-block__wrapper_slider');
            if (!wrapper) {
                console.warn('No main_news-block__wrapper_slider found for:', el);
                return;
            }
            if (!el.swiper) {
                console.log('Initializing Swiper for news:', el);
                new Swiper(el, {
                    slidesPerView: 1.1,
                    spaceBetween: 24,
                    loop: false,
                    pagination: {
                        el: wrapper.querySelector('.slider-navs__pag'),
                        clickable: true,
                    },
                    navigation: {
                        nextEl: wrapper.querySelector('.slider-navs__next'),
                        prevEl: wrapper.querySelector('.slider-navs__prev'),
                    },
                    breakpoints: {
                        768: { slidesPerView: 2, spaceBetween: 24 },
                        1024: { slidesPerView: 3, spaceBetween: 24 },
                        1200: { slidesPerView: 3, spaceBetween: 24 },
                    },
                    a11y: {
                        prevSlideMessage: 'Предыдущий слайд',
                        nextSlideMessage: 'Следующий слайд',
                        paginationBulletMessage: 'Перейти к слайду {{index}}',
                    },
                    on: {
                        init: function () {
                            console.log('News Swiper initialized:', this.el);
                            this.el.classList.remove('swiper-container--not-ready');
                            this.el.classList.add('swiper-container--ready');
                        },
                    },
                });
            } else {
                el.swiper.update();
            }
        });
    }

    initOrUpdateSwipers();

    window.addEventListener('resize', debounce(initOrUpdateSwipers, 200));

    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(btn => {
        btn.addEventListener('shown.bs.tab', () => {
            console.log('Tab switched, updating Swipers');
            setTimeout(initOrUpdateSwipers, 50);
        });
    });

    document.addEventListener('htmx:afterSwap', () => {
        console.log('HTMX swap, updating Swipers');
        initOrUpdateSwipers();
    });

    // Поиск каналов (если используется)
    document.addEventListener('input', debounce((event) => {
        const searchInput = event.target.closest('.channel-search');
        if (!searchInput) return;

        const tariffId = searchInput.id.split('-')[1];
        const channelList = document.getElementById(`channelList-${tariffId}`);
        if (!channelList) return;

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
});