from django import forms
from .models import Application, Feedback


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
        fields = ("subject", "email", "content")

    def __init__(self, *args, **kwargs):
        """
        Обновление стилей формы
        """
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update(
                {"class": "form-control", "autocomplete": "off"}
            )
