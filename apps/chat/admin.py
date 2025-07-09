from django.contrib import admin
from .models import ChatSession, ChatMessage

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact', 'created_at', 'is_closed', 'unread_messages')
    list_filter = ('is_closed', 'created_at')
    search_fields = ('name', 'contact')
    actions = ['close_sessions']

    def unread_messages(self, obj):
        return ChatMessage.objects.filter(session=obj, is_support=False, is_read=False).count()
    unread_messages.short_description = 'Непрочитанные сообщения'

    def close_sessions(self, request, queryset):
        queryset.update(is_closed=True)
        self.message_user(request, "Выбранные сессии закрыты.")
    close_sessions.short_description = 'Закрыть выбранные сессии'

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'message_preview', 'is_support', 'is_read', 'timestamp', 'attachment')
    list_filter = ('is_support', 'is_read', 'timestamp')
    search_fields = ('message', 'session__name', 'session__contact')
    readonly_fields = ('timestamp',)

    def message_preview(self, obj):
        return obj.message[:50] + ('...' if len(obj.message) > 50 else '')
    message_preview.short_description = 'Сообщение'