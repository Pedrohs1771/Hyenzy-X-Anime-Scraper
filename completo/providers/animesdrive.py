import asyncio
import re
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from providers import BaseProvider
from utils import aplicar_stealth, identificar_tipo_audio, organizar_episodios

class AnimesDriveScraper(BaseProvider):
    """Provider para AnimeDrive.blog - Ultra Rápido via HTTP"""
    
    NOME = "AnimeDrive.blog"
    BASE_URL = "https://animesdrive.blog"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    }
    
    @staticmethod
    async def buscar_anime(page, termo_busca):
        try:
            url_busca = f"{AnimesDriveScraper.BASE_URL}/?s={termo_busca.replace(' ', '+')}"
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: requests.get(url_busca, headers=AnimesDriveScraper.HEADERS, timeout=30))
            
            if response.status_code != 200: return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            # Seletores para resultados de busca
            results = soup.select("article h2 a") or soup.select("div.items article a") or soup.select("h3 a") or soup.find_all('a', href=re.compile(r'/(anime|animes)/'))
            
            lista_animes = []
            seen_links = set()
            
            for res in results[:20]:
                title = res.get_text(strip=True)
                link = res.get('href')
                # Filtra apenas páginas de anime (não episódios)
                if link and link not in seen_links and title and '/episodio/' not in link and len(title) > 2:
                    lista_animes.append({
                        "nome": title, "link": link, "fonte": AnimesDriveScraper.NOME,
                        "tipo": identificar_tipo_audio(title)
                    })
                    seen_links.add(link)
            return lista_animes
        except Exception as e:
            print(f"[AnimeDrive] Erro na busca: {e}")
            return []
    
    @staticmethod
    async def listar_episodios(page, url_anime):
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: requests.get(url_anime, headers=AnimesDriveScraper.HEADERS, timeout=15))
            if response.status_code != 200: return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            # Busca links de episódios
            ep_elements = soup.select("a[href*='/episodio/']") or soup.select("ul.episodios li a")
            
            episodes = []
            seen_links = set()
            for ep in ep_elements:
                title = ep.get_text(strip=True)
                link = ep.get('href')
                if link and link not in seen_links:
                    # Extrai número do episódio
                    num_match = re.search(r'episodio[- ](\d+)', link.lower()) or re.search(r'ep[- ]?(\d+)', title.lower())
                    num = int(num_match.group(1)) if num_match else 0
                    if num > 0:
                        episodes.append({"n": title or f"Episódio {num}", "u": link, "num": num})
                        seen_links.add(link)
            return organizar_episodios(episodes)
        except Exception as e:
            print(f"[AnimeDrive] Erro nos episódios: {e}")
            return []
    
    @staticmethod
    async def extrair_video(url_episodio):
        browser = None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(user_agent=AnimesDriveScraper.HEADERS['User-Agent'])
                page = await context.new_page()
                await aplicar_stealth(page)
                
                # Bloqueia recursos pesados
                await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2,ttf}", lambda route: route.abort())
                
                captured = []
                page.on("request", lambda req: captured.append(req.url) if any(x in req.url for x in [".m3u8", ".mp4", "googlevideo", "blogger.com/video"]) else None)
                
                await page.goto(url_episodio, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(3)
                
                # Tenta interagir com o player
                for selector in [".play-video", "#player", "iframe", "video", ".jw-video"]:
                    try:
                        await page.click(selector, timeout=2000)
                        await asyncio.sleep(2)
                        if captured: break
                    except: pass
                
                if not captured:
                    # Extrai via regex do HTML
                    html = await page.content()
                    found = re.findall(r'(https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*)', html.replace('\\/', '/'))
                    captured.extend(found)
                    
                    # Verifica se há scripts com links de vídeo
                    scripts = await page.evaluate("() => Array.from(document.querySelectorAll('script')).map(s => s.innerText)")
                    for script in scripts:
                        f = re.findall(r'(https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*)', script.replace('\\/', '/'))
                        captured.extend(f)
                
                await browser.close()
                if captured:
                    video = next((u for u in captured if ".m3u8" in u or ".mp4" in u), captured[0])
                    return (video, url_episodio)
        except Exception as e:
            print(f"[AnimeDrive] Erro no vídeo: {e}")
            if browser: await browser.close()
        return (None, None)
