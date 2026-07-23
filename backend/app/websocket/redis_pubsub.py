import asyncio
import json
import logging
from typing import Any, Callable, Dict
import redis.asyncio as redis
from app.config import settings

logger = logging.getLogger(__name__)

class RedisPubSubManager:
    def __init__(self):
        self.redis_client = None
        self.pubsub = None
        self.callbacks: Dict[str, Callable] = {}
        self.listen_task = None

    async def connect(self):
        if self.redis_client:
            return
        
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        
        try:
            await self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Could not connect to real Redis: {e}. Falling back to in-memory FakeRedis.")
            import fakeredis.aioredis
            self.redis_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
            
        self.pubsub = self.redis_client.pubsub()
        self.listen_task = asyncio.create_task(self._listen())

    async def disconnect(self):
        if self.listen_task:
            self.listen_task.cancel()
        if self.pubsub:
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()

    async def subscribe(self, room_id: str, callback: Callable[[dict], Any]):
        if not self.redis_client:
            await self.connect()
        
        channel = f"whiteboard:room:{room_id}"
        if channel not in self.callbacks:
            await self.pubsub.subscribe(channel)
        
        self.callbacks[channel] = callback

    async def unsubscribe(self, room_id: str):
        channel = f"whiteboard:room:{room_id}"
        if channel in self.callbacks:
            del self.callbacks[channel]
            if self.pubsub:
                await self.pubsub.unsubscribe(channel)

    async def publish(self, room_id: str, message: dict):
        if not self.redis_client:
            await self.connect()
        channel = f"whiteboard:room:{room_id}"
        await self.redis_client.publish(channel, json.dumps(message))

    async def _listen(self):
        try:
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    channel = message['channel']
                    data = json.loads(message['data'])
                    callback = self.callbacks.get(channel)
                    if callback:
                        asyncio.create_task(callback(data))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Redis listen error: {e}")

redis_pubsub = RedisPubSubManager()
