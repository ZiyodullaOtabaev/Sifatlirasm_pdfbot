"""
Mobile App REST API package (aiohttp.web running alongside Telegram bot).
"""
from bot.api.server import start_api_server, stop_api_server

__all__ = ["start_api_server", "stop_api_server"]
