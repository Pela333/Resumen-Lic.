"""Acceso web compartido por todas las fuentes: reintentos, tiempo límite e identificación."""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class ClienteWeb:
    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout
        self.sesion = requests.Session()
        self.sesion.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "es-AR,es;q=0.9"})
        reintentos = Retry(
            total=3,
            backoff_factor=2,  # espera 2, 4, 8 segundos entre intentos
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        adaptador = HTTPAdapter(max_retries=reintentos)
        self.sesion.mount("https://", adaptador)
        self.sesion.mount("http://", adaptador)

    def html(self, url: str) -> BeautifulSoup:
        respuesta = self.sesion.get(url, timeout=self.timeout)
        respuesta.raise_for_status()
        if not respuesta.encoding or respuesta.encoding.lower() == "iso-8859-1":
            respuesta.encoding = respuesta.apparent_encoding
        return BeautifulSoup(respuesta.text, "html.parser")
