from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import uuid

def validate_file_size(value):
    if value.size > 5 * 1024 * 1024:  # 5MB
        raise ValidationError("Файл не должен превышать 5 МБ.")

class ChatOperator(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telegram_chat_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

class ChatSession(models.Model):
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=100)
    operator = models.ForeignKey(ChatOperator, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    is_closed = models.BooleanField(default=False)
    token = models.CharField(max_length=32, unique=True, blank=True)  # Для аутентификации WebSocket

    def __str__(self):
        return f"{self.name} ({self.contact})"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = uuid.uuid4().hex  # Генерируем токен, если не задан
        super().save(*args, **kwargs)

class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    message = models.TextField(max_length=2000)
    is_support = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    sender = models.CharField(max_length=100, default='Клиент')
    attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True, validators=[validate_file_size])
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]
        indexes = [
            models.Index(fields=['session', 'timestamp']),
            models.Index(fields=['message_id']),
        ]