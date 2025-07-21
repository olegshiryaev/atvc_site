import re
from django import forms
from django.core.validators import RegexValidator

from apps.core.models import Tariff
from .models import Order


import json
from django import forms
from django.core.validators import RegexValidator
from .models import Order, Tariff, Product, AdditionalService, TVChannelPackage

class OrderForm(forms.ModelForm):
    tariff_id = forms.CharField(widget=forms.HiddenInput(), required=False)
    selected_equipment_ids = forms.CharField(widget=forms.HiddenInput(), required=False)
    selected_service_slugs = forms.CharField(widget=forms.HiddenInput(), required=False)
    selected_tv_package_ids = forms.CharField(widget=forms.HiddenInput(), required=False)

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
        fields = ["full_name", "phone", "street", "house", "apartment", "comment", "selected_equipment_ids", "selected_service_slugs", "selected_tv_package_ids"]
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

    def clean_selected_equipment_ids(self):
        data = self.cleaned_data.get("selected_equipment_ids") or "[]"
        try:
            equipment_ids = json.loads(data)
            if not isinstance(equipment_ids, list):
                raise forms.ValidationError("Неверный формат данных оборудования")
            if equipment_ids:
                if not Product.objects.filter(id__in=equipment_ids).count() == len(equipment_ids):
                    raise forms.ValidationError("Некоторые ID оборудования недействительны")
            return equipment_ids
        except json.JSONDecodeError:
            raise forms.ValidationError("Ошибка парсинга данных оборудования")

    def clean_selected_service_slugs(self):
        data = self.cleaned_data.get("selected_service_slugs") or "[]"
        try:
            service_slugs = json.loads(data)
            if not isinstance(service_slugs, list):
                raise forms.ValidationError("Неверный формат данных услуг")
            if service_slugs:
                if not AdditionalService.objects.filter(slug__in=service_slugs).count() == len(service_slugs):
                    raise forms.ValidationError("Некоторые slug'и услуг недействительны")
            return service_slugs
        except json.JSONDecodeError:
            raise forms.ValidationError("Ошибка парсинга данных услуг")

    def clean_selected_tv_package_ids(self):
        data = self.cleaned_data.get("selected_tv_package_ids") or "[]"
        try:
            tv_package_ids = json.loads(data)
            if not isinstance(tv_package_ids, list):
                raise forms.ValidationError("Неверный формат данных ТВ-пакетов")
            if tv_package_ids:
                if not TVChannelPackage.objects.filter(id__in=tv_package_ids).count() == len(tv_package_ids):
                    raise forms.ValidationError("Некоторые ID ТВ-пакетов недействительны")
            return tv_package_ids
        except json.JSONDecodeError:
            raise forms.ValidationError("Ошибка парсинга данных ТВ-пакетов")