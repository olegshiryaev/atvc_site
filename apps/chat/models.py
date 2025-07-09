from django.db import models
from django.core.exceptions import ValidationError
import uuid

def validate_file_size(value):
    if value.size > 5 * 1024 * 1024:  # 5MB
        raise ValidationError("Файл не должен превышать 5 МБ.")

class ChatSession(models.Model):
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    is_closed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.contact})"

class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message_id = models.UUIDField(default=uuid.uuid4, blank=True, null=True)
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