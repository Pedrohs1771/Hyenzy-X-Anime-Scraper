"""
steamrip.py - Provider SteamRIP para games_core
Coloque este arquivo em: providers-games/steamrip.py
Versão final funcional testada.
"""
import asyncio
import re
import requests
from urllib.parse import quote, urljoin, urlparse

try:
    from bs4 import BeautifulSoup
    DEPS_OK = True
except ImportError:
    DEPS_OK = False

class SteamRIP:
    NAME = "SteamRIP"
    ACTIVE = DEPS_OK
    BASE_URL = "https://steamrip.com"
    
    DOWNLOAD_DOMAINS = [
        'gofile.io', '1fichier.com', 'megadb.net', 'buzzheavier.com',
        'qiwi.gg', 'rapidgator.net', 'pixeldrain.com', 'mediafire.com',
        'mega.nz', 'mega.io', 'mega.co.nz', 'uploadhaven.com', 
        'bayfiles.com', 'workupload.com', 'hexupload.net', 'file-up.org',
        'zippyshare.com', 'anonfiles.com', 'upload.ee', 'usersdrive.com',
        'dropapk.to', 'drop.download', 'file.al', 'upload.ac', 'uploadrar.com'
    ]
    
    FORBIDDEN = [
        'discord.gg', 'discord.com', 't.me/', 'telegram.me', 'patreon.com',
        'youtube.com', 'youtu.be', 'twitter.com', 'facebook.com', 'instagram.com',
        'tutorial', 'how.to', 'guide', 'walkthrough', 'support', 'donate', 'paypal', 'ko-fi'
    ]

    @classmethod
    async def search(cls, query):
        if not DEPS_OK: return []
        print(f"[{cls.NAME}] Buscando: {query}")
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, cls._do_search, query)
            print(f"[{cls.NAME}] Encontrados: {len(result)} resultados")
            return result
        except Exception as e:
            print(f"[{cls.NAME}] ERRO na busca: {e}")
            return []

    @classmethod
    def _do_search(cls, query):
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': cls.BASE_URL,
        }
        
        try:
            # Acessa a home para cookies
            session.get(cls.BASE_URL, headers=headers, timeout=15)
            
            search_url = f"{cls.BASE_URL}/?s={quote(query)}"
            response = session.get(search_url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            seen_urls = set()

            # Busca links que parecem ser de jogos
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                url = link['href']
                # Normaliza URL
                abs_url = cls._abs_url(url)
                
                if not abs_url or abs_url in seen_urls: continue
                if not any(x in abs_url.lower() for x in ['free-download', 'download']): continue
                if any(x in abs_url.lower() for x in ['/category/', '/tag/', '/author/', '/page/', '?s=']): continue
                
                title = link.get_text(strip=True)
                if len(title) < 5:
                    parent = link.find_parent(['article', 'div', 'li'])
                    if parent:
                        title_elem = parent.find(['h2', 'h3', 'h4'])
                        if title_elem: title = title_elem.get_text(strip=True)
                
                if len(title) < 5: continue
                
                seen_urls.add(abs_url)
                results.append({
                    'title': title,
                    'url': abs_url
                })

            return results[:15]
        except Exception as e:
            print(f"[{cls.NAME}] Erro na busca: {e}")
            return []

    @classmethod
    async def extract_downloads(cls, url):
        if not DEPS_OK: return []
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, cls._do_extract, url)
        except Exception as e:
            print(f"[{cls.NAME}] ERRO na extração: {e}")
            return []

    @classmethod
    def _do_extract(cls, url):
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
            'Referer': cls.BASE_URL,
        }
        
        try:
            response = session.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            downloads = []
            seen = set()
            
            all_links = soup.find_all('a', href=True)
            
            # Deep Scan em áreas de conteúdo
            content = soup.find(['div', 'article'], class_=re.compile(r'content|entry|download|post', re.I))
            if content:
                all_links.extend(content.find_all('a', href=True))

            for link in all_links:
                href = link.get('href', '')
                if not href: continue
                
                # Verifica se é download ou onclick
                if not cls._is_download(href):
                    onclick = link.get('onclick', '')
                    if onclick:
                        matches = re.findall(r'["\'](https?://[^"\']+)["\']', onclick)
                        if matches: href = matches[0]
                        else: continue
                    else: continue

                abs_href = cls._abs_url(href)
                if not cls._is_download(abs_href) or abs_href in seen: continue
                
                seen.add(abs_href)
                domain = urlparse(abs_href).netloc.lower().replace('www.', '')
                server = domain.split('.')[0].title()
                text = link.get_text(strip=True)
                name = text if len(text) > 3 else f"Download {server}"
                
                downloads.append({
                    'name': name[:60],
                    'url': abs_href,
                    'server': server
                })
            
            return downloads
        except Exception:
            return []

    @classmethod
    def _is_download(cls, url):
        if not url: return False
        url_lower = url.lower()
        if any(x in url_lower for x in cls.FORBIDDEN): return False
        domain = urlparse(url).netloc.lower().replace('www.', '')
        return any(d in domain for d in cls.DOWNLOAD_DOMAINS)

    @classmethod
    def _abs_url(cls, url):
        if not url: return url
        if url.startswith('http'): return url
        if url.startswith('//'): return 'https:' + url
        return urljoin(cls.BASE_URL, url)
