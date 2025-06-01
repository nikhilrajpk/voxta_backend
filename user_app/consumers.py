import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Message, InterestRequest
from .serializers import MessageSerializer
from django.db import models

User = get_user_model()
logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_group_name = None
        self.user = None

    async def connect(self):
        # Get user from scope (authenticated via middleware)
        self.user = self.scope.get('user')
        
        if not self.user or not self.user.is_authenticated:
            logger.warning("Unauthenticated user attempted to connect")
            await self.close()
            return

        # Create a unique group for this user
        self.user_group_name = f"user_{self.user.id}"
        
        # Join user's personal group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"User {self.user.username} connected to chat")

        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to chat system'
        }))

    async def disconnect(self, close_code):
        # Leave user's personal group
        if self.user_group_name:
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
        
        if self.user:
            logger.info(f"User {self.user.username} disconnected from chat")

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')

            if message_type == 'chat_message':
                await self.handle_chat_message(text_data_json)
            elif message_type == 'typing_indicator':
                await self.handle_typing_indicator(text_data_json)
            else:
                await self.send_error('Invalid message type')

        except json.JSONDecodeError:
            await self.send_error('Invalid JSON format')
        except Exception as e:
            logger.error(f"Error in receive: {str(e)}")
            await self.send_error('Internal server error')

    async def handle_chat_message(self, data):
        receiver_id = data.get('receiver_id')
        content = data.get('content', '').strip()

        if not receiver_id or not content:
            await self.send_error('Missing receiver_id or content')
            return

        try:
            receiver_id = int(receiver_id)
        except (ValueError, TypeError):
            await self.send_error('Invalid receiver_id')
            return

        # Verify mutual connection
        is_connected = await self.check_mutual_connection(self.user.id, receiver_id)
        if not is_connected:
            await self.send_error('You can only message connected users')
            return

        # Get receiver user
        receiver = await self.get_user(receiver_id)
        if not receiver:
            await self.send_error('Receiver not found')
            return

        # Save message to database
        message = await self.save_message(self.user, receiver, content)
        if not message:
            await self.send_error('Failed to save message')
            return

        # Serialize message
        message_data = await self.serialize_message(message)

        # Send to sender (confirmation)
        await self.send(text_data=json.dumps({
            'type': 'message_sent',
            'message': message_data
        }))

        # Send to receiver (if they're online)
        receiver_group_name = f"user_{receiver_id}"
        await self.channel_layer.group_send(
            receiver_group_name,
            {
                'type': 'chat_message_handler',
                'message': message_data
            }
        )

    async def handle_typing_indicator(self, data):
        receiver_id = data.get('receiver_id')
        is_typing = data.get('is_typing', False)

        if not receiver_id:
            return

        try:
            receiver_id = int(receiver_id)
        except (ValueError, TypeError):
            return

        # Verify mutual connection
        is_connected = await self.check_mutual_connection(self.user.id, receiver_id)
        if not is_connected:
            return

        # Send typing indicator to receiver
        receiver_group_name = f"user_{receiver_id}"
        await self.channel_layer.group_send(
            receiver_group_name,
            {
                'type': 'typing_indicator_handler',
                'sender_id': self.user.id,
                'sender_username': self.user.username,
                'is_typing': is_typing
            }
        )

    async def chat_message_handler(self, event):
        """Handler for incoming chat messages"""
        await self.send(text_data=json.dumps({
            'type': 'message_received',
            'message': event['message']
        }))

    async def typing_indicator_handler(self, event):
        """Handler for typing indicators"""
        await self.send(text_data=json.dumps({
            'type': 'typing_indicator',
            'sender_id': event['sender_id'],
            'sender_username': event['sender_username'],
            'is_typing': event['is_typing']
        }))

    async def send_error(self, error_message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'error': error_message
        }))

    @database_sync_to_async
    def check_mutual_connection(self, user_id, other_user_id):
        """Check if two users have mutual connection (accepted interest)"""
        return InterestRequest.objects.filter(
            models.Q(sender_id=user_id, receiver_id=other_user_id, status='accepted') |
            models.Q(sender_id=other_user_id, receiver_id=user_id, status='accepted')
        ).exists()

    @database_sync_to_async
    def get_user(self, user_id):
        """Get user by ID"""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def save_message(self, sender, receiver, content):
        """Save message to database"""
        try:
            return Message.objects.create(
                sender=sender,
                receiver=receiver,
                content=content
            )
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
            return None

    @database_sync_to_async
    def serialize_message(self, message):
        """Serialize message for JSON response"""
        serializer = MessageSerializer(message)
        return serializer.data