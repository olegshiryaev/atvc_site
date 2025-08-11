from django import forms
from django.core.validators import RegexValidator
from .models import Order
from apps.equipments.models import ProductItem
from apps.cities.models import Locality
import re
import logging

logger = logging.getLogger(__name__)

class OrderForm(forms.ModelForm):
    product_item_id = forms.CharField(widget=forms.HiddenInput(), required=True)
    payment_type = forms.ChoiceField(
        choices=[
            ('purchase', 'Покупка'),
            ('installment12', 'Рассрочка на 12 месяцев'),
            ('installment24', 'Рассрочка на 24 месяцев'),
            ('installment48', 'Рассрочка на 48 месяцев'),
        ],
        widget=forms.HiddenInput(),
        required=True
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

    class Meta:
        model = Order
        fields = [
            "full_name", "phone", "street", "house", "apartment", "comment",
            "product_item_id", "payment_type"
        ]
        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "class": "connect-form__input",
                    "placeholder": "Иванов Иван Иванович",
                    "autocomplete": "name",
                    "required": "required",
                    "aria-describedby": "error_full_name",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "connect-form__input",
                    "placeholder": "+7 (___) ___-__-__",
                    "autocomplete": "tel",
                    "required": "required",
                    "aria-describedby": "error_phone",
                }
            ),
            "street": forms.TextInput(
                attrs={
                    "class": "connect-form__input",
                    "placeholder": "ул. Ленина",
                    "autocomplete": "address-line1",
                    "aria-describedby": "error_street",
                }
            ),
            "house": forms.TextInput(
                attrs={
                    "class": "connect-form__input",
                    "placeholder": "1",
                    "autocomplete": "address-line2",
                    "aria-describedby": "error_house",
                }
            ),
            "apartment": forms.TextInput(
                attrs={
                    "class": "connect-form__input",
                    "placeholder": "1",
                    "autocomplete": "address-line3",
                    "aria-describedby": "error_apartment",
                }
            ),
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
        street = self.cleaned_data.get("street") or ""
        return street.strip()

    def clean_house(self):
        house = self.cleaned_data.get("house") or ""
        return house.strip()

    def clean_apartment(self):
        apartment = self.cleaned_data.get("apartment") or ""
        return apartment.strip()

    def clean_product_item_id(self):
        product_item_id = self.cleaned_data.get("product_item_id")
        try:
            product_item = ProductItem.objects.get(id=product_item_id, in_stock__gt=0)
            logger.info(f"Проверена товарная позиция ID={product_item_id}")
            return product_item_id
        except ProductItem.DoesNotExist:
            logger.warning(f"Товарная позиция ID={product_item_id} недоступна или отсутствует на складе")
            raise forms.ValidationError("Выбранная товарная позиция недоступна или отсутствует на складе")

    def clean_payment_type(self):
        payment_type = self.cleaned_data.get("payment_type")
        product_item_id = self.cleaned_data.get("product_item_id")
        if not product_item_id:
            return payment_type
        try:
            product_item = ProductItem.objects.get(id=product_item_id)
            if payment_type != 'purchase' and not product_item.installment_available:
                raise forms.ValidationError("Рассрочка недоступна для выбранной товарной позиции")
            months = {'installment12': 12, 'installment24': 24, 'installment48': 48}
            if payment_type in months and not product_item.get_installment_price(months[payment_type]):
                raise forms.ValidationError(f"Рассрочка на {months[payment_type]} месяцев не настроена")
        except ProductItem.DoesNotExist:
            logger.warning(f"Товарная позиция ID={product_item_id} не найдена при проверке payment_type")
            pass
        return payment_type