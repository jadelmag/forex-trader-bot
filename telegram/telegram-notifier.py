
# telegram/telegram-notifier.py

from telethon import TelegramClient, functions
import asyncio
import threading
from typing import Callable, Optional

API_ID = 123456                         
API_HASH = "abcd1234efgh5678"           
SESSION_NAME = "Forex Market Channel"   

DEFAULT_TITLE = "Forex Market Channel"
DEFAULT_DESCRIPTION = "Canal privado para el trading de Forex"

class TelegramNotifier:
    def __init__(self):
        self.client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        self.loop = asyncio.new_event_loop()
        self._thread = None

    async def save_title_and_description(self, title: str, description: str):
        self.title = title
        self.description = description
        print(f"✅ Título y descripción guardados: {self.title}, {self.description}")

    async def _connect(self):
        """Inicia sesión en Telegram"""
        await self.client.start()
        print("✅ Conectado a Telegram")

    async def _create_private_channel(self, channel_name: str, description: str = ""):
        """Crea un canal privado"""
        result = await self.client(functions.channels.CreateChannelRequest(
            title=channel_name,
            about=description,
            megagroup=False
        ))
        channel = result.chats[0]
        print(f"✅ Canal creado: {channel.title}")
        return channel

    async def _generate_invite_link(self, channel):
        """Genera enlace de invitación"""
        invite = await self.client(functions.messages.ExportChatInviteRequest(
            peer=channel
        ))
        print(f"🔗 Enlace de invitación generado: {invite.link}")
        return invite.link

    def _run_async_in_thread(self, title: str, description: str, 
                           callback: Optional[Callable] = None):
        """Ejecuta las operaciones asíncronas en un hilo separado"""
        async def async_operations():
            try:
                await self._connect()
                channel = await self._create_private_channel(title, description)
                invite_link = await self._generate_invite_link(channel)
                
                if callback:
                    callback(invite_link, None)
                
            except Exception as e:
                print(f"❌ Error: {e}")
                if callback:
                    callback(None, str(e))
            finally:
                await self.client.disconnect()

        # Ejecutar en el loop del hilo
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(async_operations())

    def init_telegram(self, title: str, description: str, 
                     callback: Optional[Callable] = None):
        """
        Inicializa Telegram en un hilo separado
        
        Args:
            title: Título del canal
            description: Descripción del canal
            callback: Función que se llamará cuando termine (invite_link, error)
        """
        # Detener cualquier operación previa
        self.stop()
        
        # Crear y ejecutar en nuevo hilo
        self._thread = threading.Thread(
            target=self._run_async_in_thread,
            args=(title, description, callback),
            daemon=True
        )
        self._thread.start()
        
        print("⏳ Iniciando Telegram en segundo plano...")

    def stop(self):
        """Detiene las operaciones en curso"""
        if self._thread and self._thread.is_alive():
            # Para el loop asíncrono
            self.loop.call_soon_threadsafe(self.loop.stop)
            self._thread.join(timeout=2.0)
            
    def is_running(self):
        """Verifica si está ejecutándose"""
        return self._thread and self._thread.is_alive()

    def __del__(self):
        """Limpia recursos al destruir el objeto"""
        self.stop()