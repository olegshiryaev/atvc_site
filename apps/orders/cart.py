from decimal import Decimal

from apps.core.models import AdditionalService, TVChannelPackage, Tariff

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get("cart")
        if not cart:
            cart = self.session["cart"] = {
                "tariff": None,
                "products": {},
                "services": [],
                "tv_packages": [],
            }
        self.cart = cart

    def save(self):
        self.session.modified = True

    # Тариф
    def set_tariff(self, tariff_id):
        self.cart["tariff"] = tariff_id
        self.save()

    def clear_tariff(self):
        self.cart["tariff"] = None
        self.save()

    # Оборудование
    def add_product(self, product_id, variant_id, quantity, price):
        key = f"{product_id}:{variant_id or 'null'}"
        if key in self.cart["products"]:
            self.cart["products"][key]["quantity"] += quantity
        else:
            self.cart["products"][key] = {
                "quantity": quantity,
                "price": price,
            }
        self.save()

    def remove_product(self, product_id, variant_id):
        key = f"{product_id}:{variant_id or 'null'}"
        if key in self.cart["products"]:
            del self.cart["products"][key]
            self.save()

    # Доп. услуги
    def add_service(self, service_id):
        if service_id not in self.cart["services"]:
            self.cart["services"].append(service_id)
            self.save()

    def remove_service(self, service_id):
        if service_id in self.cart["services"]:
            self.cart["services"].remove(service_id)
            self.save()

    # ТВ-пакеты
    def add_tv_package(self, package_id):
        if package_id not in self.cart["tv_packages"]:
            self.cart["tv_packages"].append(package_id)
            self.save()

    def remove_tv_package(self, package_id):
        if package_id in self.cart["tv_packages"]:
            self.cart["tv_packages"].remove(package_id)
            self.save()
    
    def get_total(self):
        total = Decimal('0')
        
        # Добавляем стоимость тарифа, если выбран
        if self.cart["tariff"]:
            try:
                tariff = Tariff.objects.get(pk=self.cart["tariff"])
                total += Decimal(tariff.get_actual_price())
            except Tariff.DoesNotExist:
                pass
        
        # Добавляем товары
        for key, item in self.cart["products"].items():
            total += Decimal(item["price"]) * Decimal(item["quantity"])
        
        # Добавляем услуги
        for service_id in self.cart["services"]:
            try:
                service = AdditionalService.objects.get(pk=service_id)
                total += Decimal(service.price)
            except AdditionalService.DoesNotExist:
                pass
        
        # Добавляем ТВ-пакеты
        for package_id in self.cart["tv_packages"]:
            try:
                package = TVChannelPackage.objects.get(pk=package_id)
                total += Decimal(package.price)
            except TVChannelPackage.DoesNotExist:
                pass
        
        return total

    def clear(self):
        self.session["cart"] = {
            "tariff": None,
            "products": {},
            "services": [],
            "tv_packages": [],
        }
        self.save()
