from django.contrib import admin
from django.utils.html import format_html
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
    list_display = ('session', 'message_preview', 'is_support', 'is_read', 'attachment_link', 'file_size_formatted', 'timestamp')
    list_filter = ('is_support', 'is_read', 'timestamp', 'attachment_url')
    search_fields = ('message', 'session__name', 'session__contact')
    readonly_fields = ('timestamp',)

    def message_preview(self, obj):
        return obj.message[:50] + ('...' if len(obj.message) > 50 else '')
    message_preview.short_description = 'Сообщение'

    def attachment_link(self, obj):
        if obj.attachment_url:
            file_name = obj.attachment_url.split('/')[-1]
            if file_name and '_' in file_name and len(file_name) > 37:
                file_name = file_name[37:]  # Убираем UUID и '_'
            return format_html('<a href="{}" target="_blank">{}</a>', obj.attachment_url, file_name)
        return '-'
    attachment_link.short_description = 'Вложение'

    def file_size_formatted(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} Б"
            kb = obj.file_size / 1024
            if kb < 1024:
                return f"{kb:.1f} КБ"
            mb = kb / 1024
            return f"{mb:.1f} МБ"
        return '-'
    file_size_formatted.short_description = 'Размер файла'