import json
import datetime
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatSession, ChatMessage

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'chat_{self.session_id}'

        self.session = await self.get_session(self.session_id)
        if not self.session or self.session.is_closed:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # Отправка последних 50 сообщений при подключении
        messages = await self.get_last_messages(limit=50)
        for msg in messages:
            await self.send(text_data=json.dumps({
                'type': 'chat_message',  # Тип для клиента
                'message': msg['message'],
                'is_support': msg['is_support'],
                'timestamp': msg['timestamp'].isoformat(),
                'sender': self.session.name if not msg['is_support'] else 'Специалист',
                'history': True,
            }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return  # Игнорируем неверный JSON

        # Обработка typing-событий
        if data.get('type') == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_message',
                    'is_typing': data.get('is_typing', False),
                    'sender_channel': self.channel_name,
                    'sender_name': self.session.name
                }
            )
            return

        # Обработка обычных сообщений
        message = data.get('message', None)
        is_support = data.get('is_support', False)

        # Защита от нестроковых или пустых сообщений
        if not isinstance(message, str) or not message.strip():
            return

        # Проверка закрытия сессии и длины
        if self.session.is_closed or len(message) > 2000:
            return

        # Всё прошло — сохраняем и отправляем
        timestamp = await self.save_message(message.strip(), is_support=is_support)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message.strip(),
                'is_support': is_support,
                'timestamp': timestamp.isoformat(),
                'sender': self.session.name if not is_support else 'Специалист',
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'is_support': event['is_support'],
            'timestamp': event['timestamp'],
            'sender': event['sender'],
        }))

    # Новый метод для рассылки уведомлений о наборе сообщения
    async def typing_message(self, event):
        # Не отправляем самому отправителю
        if event['sender_channel'] == self.channel_name:
            return

        await self.send(text_data=json.dumps({
            'type': 'typing',
            'is_typing': event['is_typing'],
            'sender': event.get('sender_name', 'Собеседник'),
        }))

    @database_sync_to_async
    def get_session(self, session_id):
        try:
            return ChatSession.objects.get(id=session_id)
        except ChatSession.DoesNotExist:
            return None

    @database_sync_to_async
    def save_message(self, message, is_support):
        msg = ChatMessage.objects.create(
            session=self.session,
            message=message,
            is_support=is_support
        )
        return msg.timestamp

    @database_sync_to_async
    def get_last_messages(self, limit=50):
        return list(
            ChatMessage.objects
            .filter(session=self.session)
            .order_by('-timestamp')
            .values('message', 'is_support', 'timestamp')[:limit][::-1]
        )