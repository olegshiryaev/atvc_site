from django import forms
from django.core.validators import RegexValidator
from .models import Order
from apps.equipments.models import ProductItem
from apps.cities.models import Locality
import re
import logging

logger = logging.getLogger(__name__)

class OrderForm(forms.ModelForm):
    
    """
    Универсальная форма для оформления заявок.
    
    Используется в двух сценариях:
    1. Заказ тарифа с оборудованием, ТВ-пакетами и услугами.
       - Используются: tariff_id, selected_equipment_ids, equipment_payment_options и др.
    2. Заказ отдельного оборудования.
       - Используются: product_item_id, payment_type.
       - Остальные поля игнорируются.
    """
    
    product_item_id = forms.CharField(
        widget=forms.HiddenInput(),
        required=False  # Теперь не всегда требуется
    )
    payment_type = forms.ChoiceField(
        choices=[
            ('purchase', 'Покупка'),
            ('installment12', 'Рассрочка на 12 месяцев'),
            ('installment24', 'Рассрочка на 24 месяцев'),
            ('installment48', 'Рассрочка на 48 месяцев'),
        ],
        widget=forms.HiddenInput(),
        required=False  # Теперь не всегда требуется
    )

    comment = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Ваш комментарий (необязательно)'
        }),
        required=False,
        label='Комментарий'
    )

    # Добавьте поля, используемые в заказе тарифа
    tariff_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    selected_equipment_ids = forms.JSONField(widget=forms.HiddenInput(), required=False)
    equipment_payment_options = forms.JSONField(widget=forms.HiddenInput(), required=False)
    selected_service_slugs = forms.JSONField(widget=forms.HiddenInput(), required=False)
    selected_tv_package_ids = forms.JSONField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = Order
        fields = [
            "full_name", "phone", "street", "house", "apartment", "comment",
            "product_item_id", "payment_type",
            "tariff_id", "selected_equipment_ids", "equipment_payment_options",
            "selected_service_slugs", "selected_tv_package_ids"
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={
                "class": "connect-form__input",
                "id": "name",
                "placeholder": "Иванов Иван Иванович",
                "autocomplete": "name",
                "required": "required",
                "aria-describedby": "error_full_name",
            }),
            "phone": forms.TextInput(attrs={
                "class": "connect-form__input",
                "id": "phone",
                "placeholder": "+7 (___) ___-__-__",
                "autocomplete": "tel",
                "required": "required",
                "aria-describedby": "error_phone",
            }),
            "street": forms.TextInput(attrs={
                "class": "connect-form__input",
                "id": "street",
                "placeholder": "ул. Ленина",
                "autocomplete": "address-line1",
                "aria-describedby": "error_street",
            }),
            "house": forms.TextInput(attrs={
                "class": "connect-form__input",
                "id": "house",
                "placeholder": "1",
                "autocomplete": "address-line2",
                "aria-describedby": "error_house",
            }),
            "apartment": forms.TextInput(attrs={
                "class": "connect-form__input",
                "id": "apartment",
                "placeholder": "1",
                "autocomplete": "address-line3",
                "aria-describedby": "error_apartment",
            }),
            "comment": forms.Textarea(attrs={
                "class": "order-form__textarea",
                "id": "comments",
                "rows": "2",
                "placeholder": "Ваш комментарий (необязательно)",
            }),
        }
        labels = {
            "full_name": "Имя",
            "phone": "Номер телефона",
            "street": "Улица",
            "house": "Номер дома",
            "apartment": "Квартира",
        }

    def __init__(self, *args, locality=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.locality = locality
        self.fields["full_name"].required = True
        self.fields["phone"].required = True
        self.fields["street"].required = False
        self.fields["house"].required = False
        self.fields["apartment"].required = False

        # Валидатор для ФИО
        self.fields["full_name"].validators.append(
            RegexValidator(
                regex=r"^[А-Яа-яЁёA-Za-z\s\.\-]+$",
                message="Имя может содержать только буквы, пробелы, точку и дефис",
            )
        )

    def clean_full_name(self):
        full_name = self.cleaned_data.get("full_name") or ""
        full_name = full_name.strip()
        if not full_name:
            raise forms.ValidationError("Введите ваше имя")
        return full_name

    def clean_phone(self):
        phone = self.cleaned_data.get("phone") or ""
        phone = phone.strip()
        cleaned_phone = re.sub(r"[^\d]", "", phone)
        if len(cleaned_phone) != 11:
            raise forms.ValidationError("Введите номер телефона в формате +7 (XXX) XXX-XX-XX")
        if cleaned_phone.startswith("8"):
            cleaned_phone = "7" + cleaned_phone[1:]
        elif not cleaned_phone.startswith("7"):
            raise forms.ValidationError("Номер телефона должен начинаться с +7 или 8")
        return f"+7{cleaned_phone[1:]}"

    def clean_street(self):
        return (self.cleaned_data.get("street") or "").strip()

    def clean_house(self):
        return (self.cleaned_data.get("house") or "").strip()

    def clean_apartment(self):
        return (self.cleaned_data.get("apartment") or "").strip()

    def clean_product_item_id(self):
        product_item_id = self.cleaned_data.get("product_item_id")
        if not product_item_id:
            return None  # Может быть None, если не используется

        try:
            product_item = ProductItem.objects.get(id=product_item_id, in_stock__gt=0)
            return product_item_id
        except ProductItem.DoesNotExist:
            raise forms.ValidationError("Выбранная товарная позиция недоступна или отсутствует на складе")

    def clean_payment_type(self):
        payment_type = self.cleaned_data.get("payment_type")
        product_item_id = self.cleaned_data.get("product_item_id")

        # Если нет product_item_id — значит, это не заказ одного товара
        if not product_item_id:
            return payment_type  # Не проверяем

        if not payment_type:
            return 'purchase'  # Дефолт

        try:
            product_item = ProductItem.objects.get(id=product_item_id)
            if payment_type != 'purchase' and not product_item.installment_available:
                raise forms.ValidationError("Рассрочка недоступна для выбранной товарной позиции")

            months_map = {'installment12': 12, 'installment24': 24, 'installment48': 48}
            if payment_type in months_map:
                if not product_item.get_installment_price(months_map[payment_type]):
                    raise forms.ValidationError(f"Рассрочка на {months_map[payment_type]} месяцев не настроена")
        except ProductItem.DoesNotExist:
            pass

        return payment_type