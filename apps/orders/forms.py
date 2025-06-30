import re
from django import forms

from apps.core.models import Tariff
from .models import Order
from django.core.validators import RegexValidator


class OrderForm(forms.ModelForm):
    tariff_id = forms.CharField(widget=forms.HiddenInput(), required=False)
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
        fields = ["full_name", "phone", "street", "house", "apartment", "comment"]
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
        self.fields["phone"].validators.append(
            RegexValidator(
                regex=r"^\+7\d{10}$",
                message="Введите номер телефона в формате +7 (XXX) XXX-XX-XX",
            )
        )
        self.fields["full_name"].validators.append(
            RegexValidator(
                regex=r"^[А-Яа-яA-Za-z\s]+$",
                message="Имя должно содержать только буквы и пробелы",
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

        # Удаляем все нецифровые символы
        cleaned_phone = re.sub(r"[^\d]", "", phone)

        # Проверяем длину и начало номера
        if len(cleaned_phone) != 11 or not cleaned_phone.startswith("7"):
            raise forms.ValidationError(
                "Введите номер телефона в формате +7 (XXX) XXX-XX-XX"
            )

        return f"+7{cleaned_phone[1:]}"  # Возвращаем в формате +7XXXXXXXXXX

    def clean_street(self):
        street = self.cleaned_data.get("street") or ""
        return street.strip()

    def clean_house(self):
        house = self.cleaned_data.get("house") or ""
        return house.strip()

    def clean_apartment(self):
        apartment = self.cleaned_data.get("apartment") or ""
        return apartment.strip()

    def clean_tariff_id(self):
        tariff_id = self.cleaned_data.get("tariff_id")
        if tariff_id and self.locality:
            try:
                tariff = Tariff.objects.get(
                    id=tariff_id, is_active=True, localities=self.locality
                )
            except Tariff.DoesNotExist:
                raise forms.ValidationError(
                    "Выбранный тариф недоступен для вашего региона"
                )
            return tariff_id
        return None