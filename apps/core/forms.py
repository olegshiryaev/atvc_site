from django import forms
from .models import Application, Feedback


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["name", "phone", "address"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ваше имя"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ваш телефон"}
            ),
            "address": forms.Textarea(
                attrs={"class": "form-control", "placeholder": "Ваш адрес", "rows": 3}
            ),
        }


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
