document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll('[id^="channelsModal"]').forEach(modal => {
        // Извлекаем modal_type и id из формата channelsModal-<modal_type>-<id>
        const modalParts = modal.id.split("-");
        const modalType = modalParts[1]; // tariff или package
        const modalId = modalParts[2];   // id объекта
        const channelList = document.getElementById(`channelList-${modalType}-${modalId}`);
        const filterButtons = modal.querySelectorAll(".btn-category");
        const categoryToggle = modal.querySelector(".btn-category-toggle");
        const dropdownItems = modal.querySelectorAll(".channel-category-item");

        if (!channelList) return;

        // Подсчёт каналов по категориям
        const categoryCount = {};
        let totalChannels = 0;

        channelList.querySelectorAll(".channel-item").forEach(item => {
            const category = item.getAttribute("data-category");
            categoryCount[category] = (categoryCount[category] || 0) + 1;
            totalChannels += 1;
        });

        // Обновляем десктопные кнопки
        filterButtons.forEach(button => {
            const category = button.getAttribute("data-category");
            const count = category === "" ? totalChannels : categoryCount[category] || 0;

            if (count === 0 && category !== "") {
                button.style.display = "none";
                return;
            }

            const countSpan = button.querySelector(".category-count");
            if (countSpan) {
                countSpan.textContent = count;
            }
        });

        // Обновляем мобильные пункты меню
        dropdownItems.forEach(dropdownItem => {
            const category = dropdownItem.getAttribute("data-category");
            const count = category === "" ? totalChannels : categoryCount[category] || 0;

            if (category !== "" && count === 0) {
                if (dropdownItem.closest("li")) {
                    dropdownItem.closest("li").style.display = "none";
                }
                return;
            }

            const countSpan = dropdownItem.querySelector(".channel-category-count");
            if (countSpan) {
                countSpan.textContent = count;
            }
        });

        // Функция фильтрации
        function handleCategoryClick(element) {
            const selectedCategory = element.getAttribute("data-category");

            // Сброс активного состояния
            modal.querySelectorAll(".btn-category, .channel-category-item").forEach(el => el.classList.remove("active"));

            // Добавляем active текущему элементу
            element.classList.add("active");

            // Находим соответствующую кнопку и добавляем ей active
            const matchingButton = modal.querySelector(`.btn-category[data-category="${selectedCategory}"]`);
            if (matchingButton) {
                matchingButton.classList.add("active");
            } else {
                const allButton = modal.querySelector('.btn-category[data-category=""]');
                if (allButton) {
                    allButton.classList.add("active");
                }
            }

            // Фильтруем каналы
            channelList.querySelectorAll(".channel-item").forEach(item => {
                const itemCategory = item.getAttribute("data-category");
                const show = !selectedCategory || itemCategory === selectedCategory;
                item.style.display = show ? "block" : "none";
            });
        }

        // Назначаем обработчики событий
        filterButtons.forEach(button => {
            button.addEventListener("click", function (e) {
                e.preventDefault();
                handleCategoryClick(this);
            });
        });

        dropdownItems.forEach(dropdownItem => {
            dropdownItem.addEventListener("click", function (e) {
                e.preventDefault();
                handleCategoryClick(this);
            });
        });
    });
});