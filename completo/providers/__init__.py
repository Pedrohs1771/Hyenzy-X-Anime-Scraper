"""
providers/__init__.py - Sistema de Auto-Descoberta de Providers

COMO ADICIONAR UM NOVO SITE:
1. Crie um arquivo providers/meusite.py
2. Copie o template abaixo
3. Implemente os 3 métodos obrigatórios
4. PRONTO! A API detectará automaticamente

A API busca por qualquer classe que herde de BaseProvider.
"""

class BaseProvider:
    """
    Classe base para todos os providers
    
    OBRIGATÓRIO definir:
    - NOME: Nome exibido no menu (ex: "MeuSite.com")
    - BASE_URL: URL do site (ex: "https://meusite.com")
    
    OBRIGATÓRIO implementar:
    - buscar_anime(page, termo_busca)
    - listar_episodios(page, url_anime)
    - extrair_video(url_episodio)
    """
    
    NOME = None  # OBRIGATÓRIO: Nome exibido no menu
    BASE_URL = None  # OBRIGATÓRIO: URL base do site
    
    @staticmethod
    async def buscar_anime(page, termo_busca):
        """
        Busca animes no site
        
        Args:
            page: Página do Playwright
            termo_busca: String de busca (ex: "naruto")
            
        Returns:
            Lista de dicts:
            [
                {
                    "nome": "Naruto Dublado",
                    "link": "https://site.com/anime/naruto",
                    "fonte": MeuProvider.NOME,  # Use self.NOME ou NomeDaClasse.NOME
                    "tipo": "DUB"  # ou "LEG" ou None
                }
            ]
        """
        raise NotImplementedError("Método buscar_anime deve ser implementado")
    
    @staticmethod
    async def listar_episodios(page, url_anime):
        """
        Lista episódios de um anime
        
        Args:
            page: Página do Playwright
            url_anime: URL da página do anime
            
        Returns:
            Lista de dicts:
            [
                {
                    "n": "Episódio 1",  # Nome/título do episódio
                    "u": "https://site.com/episodio/1",  # URL do episódio
                    "num": 1  # Número do episódio (int)
                }
            ]
            
        IMPORTANTE: Use organizar_episodios(lista) do utils.py para:
        - Remover links de redes sociais
        - Ordenar do primeiro ao último
        """
        raise NotImplementedError("Método listar_episodios deve ser implementado")
    
    @staticmethod
    async def extrair_video(url_episodio):
        """
        Extrai link direto do vídeo
        
        Args:
            url_episodio: URL da página do episódio
            
        Returns:
            Tupla (url_video, referer):
            - url_video: Link direto (.m3u8, .mp4, etc)
            - referer: URL de referência (geralmente url_episodio)
            
            Se falhar: (None, None)
            
        Exemplo:
            return ("https://cdn.com/video.m3u8", url_episodio)
        """
        raise NotImplementedError("Método extrair_video deve ser implementado")


# ═══════════════════════════════════════════════════════════════════════════
#                    TEMPLATE PARA NOVO PROVIDER
# ═══════════════════════════════════════════════════════════════════════════

"""
COPIE ESTE TEMPLATE PARA providers/meusite.py:

import asyncio
import re
from playwright.async_api import async_playwright
from providers import BaseProvider
from utils import *

class MeuSiteScraper(BaseProvider):
    '''Provider para MeuSite.com'''
    
    NOME = "MeuSite.com"  # ← OBRIGATÓRIO: Nome no menu
    BASE_URL = "https://meusite.com"  # ← OBRIGATÓRIO: URL base
    
    @staticmethod
    async def buscar_anime(page, termo_busca):
        '''Busca animes no site'''
        try:
            # Monta URL de busca
            url_busca = f"{MeuSiteScraper.BASE_URL}/search?q={termo_busca.replace(' ', '+')}"
            
            # Acessa página
            await page.goto(url_busca, wait_until="domcontentloaded", timeout=15000)
            
            # Aguarda resultados carregarem
            await page.wait_for_selector(".anime-card", timeout=6000)
            
            # Captura resultados
            resultados = await page.query_selector_all(".anime-card")
            
            lista_animes = []
            for res in resultados[:15]:  # Limita a 15
                # Extrai título
                titulo_el = await res.query_selector(".title")
                titulo = await titulo_el.inner_text()
                
                # Extrai link
                link_el = await res.query_selector("a")
                link = await link_el.get_attribute("href")
                
                # Identifica áudio (usa função do utils.py)
                tipo_audio = identificar_tipo_audio(titulo)
                
                lista_animes.append({
                    "nome": titulo.strip(),
                    "link": link,
                    "fonte": MeuSiteScraper.NOME,
                    "tipo": tipo_audio
                })
            
            return lista_animes
            
        except Exception as e:
            print(f"[{MeuSiteScraper.NOME}] Erro na busca: {e}")
            return []
    
    @staticmethod
    async def listar_episodios(page, url_anime):
        '''Lista episódios do anime'''
        try:
            # Acessa página do anime
            await page.goto(url_anime, wait_until="domcontentloaded", timeout=15000)
            
            # Aguarda lista de episódios
            await page.wait_for_selector(".episode-list", timeout=6000)
            
            # Captura episódios
            elementos = await page.query_selector_all(".episode-item a")
            
            episodes = []
            for ep in elementos:
                titulo = await ep.inner_text()
                link = await ep.get_attribute("href")
                
                # Extrai número do episódio (regex)
                ep_num_match = re.search(r'(\d+)', titulo)
                ep_num = int(ep_num_match.group(1)) if ep_num_match else 0
                
                episodes.append({
                    "n": titulo.strip(),
                    "u": link,
                    "num": ep_num
                })
            
            # IMPORTANTE: Usa função do utils.py para organizar
            return organizar_episodios(episodes)
            
        except Exception as e:
            print(f"[{MeuSiteScraper.NOME}] Erro ao listar: {e}")
            return []
    
    @staticmethod
    async def extrair_video(url_episodio):
        '''Extrai link direto do vídeo'''
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Aplica stealth (do utils.py)
            await aplicar_stealth(page)
            
            captured_urls = []
            
            # Intercepta requisições de vídeo
            async def handle_request(request):
                url = request.url
                # Captura .m3u8, .mp4, etc
                if any(x in url for x in [".m3u8", ".mp4", ".ts"]):
                    if url not in captured_urls:
                        captured_urls.append(url)
            
            page.on("request", handle_request)
            
            try:
                # Acessa página do episódio
                await page.goto(url_episodio, timeout=15000)
                
                # Aguarda player carregar
                await asyncio.sleep(3)
                
                # Tenta clicar em botão de play (se existir)
                try:
                    play_btn = await page.query_selector(".play-button")
                    if play_btn:
                        await play_btn.click()
                        await asyncio.sleep(2)
                except:
                    pass
                
                # Se capturou algum link
                if captured_urls:
                    await browser.close()
                    return (captured_urls[0], url_episodio)
                
            except Exception as e:
                print(f"[{MeuSiteScraper.NOME}] Erro extração: {e}")
            
            await browser.close()
            return (None, None)
"""