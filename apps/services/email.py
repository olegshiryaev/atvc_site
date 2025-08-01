from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.auth.models import User


def send_contact_email_message(subject, email, content, ip, user_id):
    """
    Function to send contact form email
    """
    message = render_to_string(
        "system/email/feedback_email_send.html",
        {
            "email": email,
            "content": content,
            "ip": ip,
        },
    )
    email = EmailMessage(subject, message, settings.EMAIL_SERVER, settings.EMAIL_ADMIN)
    email.send(fail_silently=False)
