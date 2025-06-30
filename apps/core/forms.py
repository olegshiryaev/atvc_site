import re
from django import forms
from .models import Application, Document, Feedback
from django.core.validators import RegexValidator


class ApplicationForm(forms.ModelForm):
    privacy = forms.BooleanField(
        required=True,
        label="Я соглашаюсь, что ознакомлен с политикой конфиденциальности",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        error_messages={
            "required": "Необходимо согласиться с политикой конфиденциальности"
        },
    )

    class Meta:
        model = Application
        fields = ["name", "phone", "street", "house_number", "comment"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ваше имя"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "+7 (___) ___-__-__"}
            ),
            "street": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Укажите улицу"}
            ),
            "house_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Укажите номер дома"}
            ),
            "comment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ваши пожелания или дополнительная информация",
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].required = True
        self.fields["phone"].required = True
        self.fields["street"].required = False
        self.fields["house_number"].required = False
        self.fields["comment"].required = False


class FeedbackCreateForm(forms.ModelForm):
    """
    Форма отправки обратной связи
    """

    class Meta:
        model = Feedback
        fields = ("name", "phone", "content")

    def __init__(self, *args, **kwargs):
        """
        Обновление стилей формы
        """
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update(
                {"class": "form-control", "autocomplete": "off"}
            )


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = "__all__"

    def clean(self):
        super().clean()
        # Вызываем метод clean модели для валидации файла
        self.instance.clean()


class ContactForm(forms.Form):
    name = forms.CharField(
        label="Имя", widget=forms.TextInput(attrs={"class": "form-control"})
    )
    email = forms.EmailField(
        label="Email", widget=forms.EmailInput(attrs={"class": "form-control"})
    )
    message = forms.CharField(
        label="Сообщение", widget=forms.Textarea(attrs={"class": "form-control"})
    )


class FeedbackForm(forms.ModelForm):
    phone_validator = RegexValidator(
        regex=r"^\+7 \(\d{3}\) \d{3}-\d{2}-\d{2}$",
        message="Введите номер в формате +7 (XXX) XXX-XX-XX",
    )

    class Meta:
        model = Feedback
        fields = ["name", "phone", "content"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Как вас зовут?",
                    "required": True,
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "+7 (XXX) XXX-XX-XX",
                    "required": True,
                }
            ),
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Сообщение",
                    "rows": 4,
                }
            ),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if phone:
            self.phone_validator(phone)
        return phone
