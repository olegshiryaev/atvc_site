document.addEventListener("DOMContentLoaded", function () {
    const modal = document.getElementById("orderModal")
    if (modal) {
        modal.addEventListener("show.bs.modal", function (event) {
            const button = event.relatedTarget
            const tariffId = button.getAttribute("data-tariff-id")
            const tariffName = button.getAttribute("data-tariff-name")

            modal.querySelector("#modalTariffId").value = tariffId
            modal.querySelector("#modalTariffName").value = tariffName
        })
    }
})
