import ipaddress
import socket
from urllib.parse import urlparse

from config import settings


BLOCKED_HOSTS = {"localhost", "metadata.google.internal"}


def validate_outbound_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https URLs are allowed")
    if not parsed.hostname:
        raise ValueError("URL must include a hostname")
    host = parsed.hostname.lower()
    if settings.allow_private_tool_hosts:
        return
    if host in BLOCKED_HOSTS or host.endswith(".local"):
        raise ValueError("Private or local hosts are blocked")
    try:
        addresses = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise ValueError(f"Could not resolve host: {host}") from exc
    for item in addresses:
        ip = ipaddress.ip_address(item[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            raise ValueError("Private network targets are blocked")
