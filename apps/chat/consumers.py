import json
import logging
from urllib.parse import parse_qs, unquote
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatSession, ChatMessage

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.session_id = self.scope['url_route']['kwargs']['session_id']
            self.room_group_name = f'chat_{self.session_id}'
            self.session = await self.get_session(self.session_id)

            await self.accept()

            if not self.session:
                logger.error(f"Сессия с ID={self.session_id} не найдена")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Сессия не найдена'
                }))
                await self.close()
                return
            if self.session.is_closed:
                logger.error(f"Сессия с ID={self.session_id} закрыта")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Сессия закрыта'
                }))
                await self.close()
                return

            query_string = self.scope['query_string'].decode()
            query_params = parse_qs(query_string)
            token = unquote(query_params.get('token', [None])[0] or '')
            logger.info(f"Подключение WebSocket: session_id={self.session_id}, token={token}")
            self.is_support = token == 'support'
            if not token or (token != self.session.contact and not self.is_support):
                logger.error(f"Недостаточно прав: session_id={self.session_id}, token={token}, contact={self.session.contact}")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Недостаточно прав: token={token}, contact={self.session.contact}'
                }))
                await self.close()
                return

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            logger.info(f"Успешное подключение: session_id={self.session_id}, channel={self.channel_name}")

            # Отправляем уведомление о подключении специалиста
            if self.is_support:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'status_update',
                        'status': 'connected',
                        'message': 'Специалист на связи'
                    }
                )

            # Помечаем сообщения как прочитанные
            if self.is_support:
                await self.mark_client_messages_as_read()
            else:
                await self.mark_support_messages_as_read()

            # Отправляем обновлённый unread_count
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'read_status',
                    'unread_count': await self.get_unread_count()
                }
            )

            skip_history = 'skip_history=true' in query_string
            if not skip_history:
                messages = await self.get_last_messages(limit=50)
                for msg in messages:
                    await self.send(text_data=json.dumps({
                        'type': 'chat_message',
                        'message_id': str(msg['message_id']),
                        'message': msg['message'],
                        'is_support': msg['is_support'],
                        'timestamp': msg['timestamp'].isoformat(),
                        'sender': msg['sender'],
                        'attachment': msg['attachment_url'],
                        'file_size': msg['file_size'],
                        'history': True,
                        'is_read': msg['is_read']
                    }))
        except Exception as e:
            logger.error(f"Ошибка при подключении WebSocket: session_id={self.session_id}, error={str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Внутренняя ошибка сервера'
            }))
            await self.close()

    async def status_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'status': event['status'],
            'message': event['message']
        }))

    async def disconnect(self, close_code):
        logger.info(f"WebSocket отключен: session_id={self.session_id}, code={close_code}")
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        if self.is_support:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'status_update',
                    'status': 'pending',
                    'message': 'Ожидание специалиста...'
                }
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            logger.info(f"Получено сообщение: session_id={self.session_id}, data={data}")
        except json.JSONDecodeError:
            logger.error(f"Некорректный JSON: session_id={self.session_id}, text_data={text_data}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Некорректный формат данных'
            }))
            return

        if data.get('type') == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_message',
                    'is_typing': data.get('is_typing', False),
                    'sender_channel': self.channel_name,
                    'sender_name': data.get('sender', 'Специалист' if self.is_support else self.session.name)
                }
            )
            return

        if data.get('type') == 'close_session':
            await self.close_session()
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'session_closed',
                    'message': 'Чат закрыт'
                }
            )
            await self.close()
            return

        if data.get('type') == 'mark_read':
            if self.is_support:
                await self.mark_client_messages_as_read()
            else:
                await self.mark_support_messages_as_read()
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'read_status',
                    'unread_count': await self.get_unread_count()
                }
            )
            return

        message = data.get('message', '')
        is_support = data.get('is_support', False)
        attachment_url = data.get('attachment')
        file_size = data.get('file_size')
        sender = data.get('sender', 'Специалист' if is_support else self.session.name)

        if not isinstance(message, str) or not message.strip():
            if not attachment_url:
                return

        if self.session.is_closed or len(message) > 2000:
            logger.error(f"Ошибка отправки: session_id={self.session_id}, closed={self.session.is_closed}, message_length={len(message)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Сессия закрыта или сообщение слишком длинное'
            }))
            return

        if attachment_url and not attachment_url.startswith('/media/chat_attachments/'):
            logger.error(f"Недопустимый URL вложения: session_id={self.session_id}, attachment={attachment_url}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Недопустимый URL вложения'
            }))
            return

        timestamp, message_id = await self.save_message(message.strip(), is_support, attachment_url, file_size, sender)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': str(message_id),
                'message': message.strip(),
                'is_support': is_support,
                'timestamp': timestamp.isoformat(),
                'sender': sender,
                'attachment': attachment_url,
                'file_size': file_size,
                'is_read': False
            }
        )
        # Обновляем статус прочтения для сообщений специалиста
        if is_support:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'read_status',
                    'unread_count': await self.get_unread_count()
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message_id': event['message_id'],
            'message': event['message'],
            'is_support': event['is_support'],
            'timestamp': event['timestamp'],
            'sender': event['sender'],
            'attachment': event.get('attachment'),
            'file_size': event.get('file_size'),
            'is_read': event['is_read']
        }))

    async def typing_message(self, event):
        if event['sender_channel'] == self.channel_name:
            return
        await self.send(text_data=json.dumps({
            'type': 'typing',
            'is_typing': event['is_typing'],
            'sender': event.get('sender_name', 'Собеседник'),
        }))

    async def read_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'read_status',
            'unread_count': event['unread_count']
        }))

    async def session_closed(self, event):
        await self.send(text_data=json.dumps({
            'type': 'session_closed',
            'message': event['message']
        }))

    @database_sync_to_async
    def get_session(self, session_id):
        try:
            return ChatSession.objects.get(id=session_id)
        except ChatSession.DoesNotExist:
            return None

    @database_sync_to_async
    def save_message(self, message, is_support, attachment_url=None, file_size=None, sender=None):
        msg = ChatMessage.objects.create(
            session=self.session,
            message=message,
            is_support=is_support,
            is_read=False,
            sender=sender or ('Специалист' if is_support else self.session.name),
            attachment_url=attachment_url,
            file_size=file_size
        )
        logger.info(f"Сохранено сообщение: session_id={self.session_id}, message_id={msg.message_id}, is_support={is_support}, attachment_url={attachment_url}, file_size={file_size}")
        return msg.timestamp, msg.message_id

    @database_sync_to_async
    def mark_support_messages_as_read(self):
        unread_count = ChatMessage.objects.filter(
            session=self.session,
            is_support=True,
            is_read=False
        ).count()
        logger.info(f"Помечаем сообщения специалиста как прочитанные: session_id={self.session_id}, unread_count={unread_count}")
        if unread_count > 0:
            ChatMessage.objects.filter(
                session=self.session,
                is_support=True,
                is_read=False
            ).update(is_read=True)
        return unread_count

    @database_sync_to_async
    def mark_client_messages_as_read(self):
        unread_count = ChatMessage.objects.filter(
            session=self.session,
            is_support=False,
            is_read=False
        ).count()
        logger.info(f"Помечаем сообщения клиента как прочитанные: session_id={self.session_id}, unread_count={unread_count}")
        if unread_count > 0:
            ChatMessage.objects.filter(
                session=self.session,
                is_support=False,
                is_read=False
            ).update(is_read=True)
        return unread_count

    @database_sync_to_async
    def get_last_messages(self, limit=50, offset=0):
        return list(
            ChatMessage.objects
            .filter(session=self.session)
            .order_by('-timestamp')
            .values(
                'message_id',
                'message',
                'is_support',
                'timestamp',
                'attachment_url',
                'file_size',
                'sender',
                'is_read'
            )[offset:offset+limit]
        )

    @database_sync_to_async
    def get_unread_count(self):
        if self.is_support:
            unread = ChatMessage.objects.filter(session=self.session, is_support=False, is_read=False).count()
        else:
            unread = ChatMessage.objects.filter(session=self.session, is_support=True, is_read=False).count()
        logger.info(f"Непрочитанные сообщения: session_id={self.session_id}, is_support={self.is_support}, unread={unread}")
        return unread

    @database_sync_to_async
    def close_session(self):
        self.session.is_closed = True
        self.session.save()
        logger.info(f"Сессия закрыта: session_id={self.session_id}")