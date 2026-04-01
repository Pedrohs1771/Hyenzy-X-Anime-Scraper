import asyncio
import re
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from providers import BaseProvider
from utils import aplicar_stealth, identificar_tipo_audio, organizar_episodios

class AnimesOnlineFHDScraper(BaseProvider):
    """Provider para AnimesOnlineFHD.vip - Ultra Rápido via HTTP"""
    
    NOME = "AnimesOnlineFHD.vip"
    BASE_URL = "https://animesonlinefhd.vip"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    }
    
    @staticmethod
    async def buscar_anime(page, termo_busca):
        try:
            url_busca = f"{AnimesOnlineFHDScraper.BASE_URL}/?s={termo_busca.replace(' ', '+')}"
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: requests.get(url_busca, headers=AnimesOnlineFHDScraper.HEADERS, timeout=30))
            
            if response.status_code != 200: return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            # Busca todos os links que contenham o termo de busca no texto ou href
            all_links = soup.find_all('a', href=True)
            results = [a for a in all_links if termo_busca.lower() in a.get_text().lower() or termo_busca.lower() in a.get('href', '').lower()]
            
            lista_animes = []
            seen_links = set()
            
            for res in results[:20]:
                title = res.get_text(strip=True)
                link = res.get('href')
                # Filtra apenas páginas de anime (evita links com "Dublado1", "Legendado2", etc)
                if (link and link not in seen_links and title and '/episodio/' not in link and 
                    len(title) > 5 and 'lista' not in title.lower() and 
                    not re.match(r'^(Dublado|Legendado)\d+', title)):
                    lista_animes.append({
                        "nome": title, "link": link, "fonte": AnimesOnlineFHDScraper.NOME,
                        "tipo": identificar_tipo_audio(title)
                    })
                    seen_links.add(link)
            return lista_animes
        except Exception as e:
            print(f"[AnimesOnlineFHD] Erro na busca: {e}")
            return []
    
    @staticmethod
    async def listar_episodios(page, url_anime):
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: requests.get(url_anime, headers=AnimesOnlineFHDScraper.HEADERS, timeout=15))
            if response.status_code != 200: return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            ep_elements = soup.select("a[href*='/episodio/']")
            
            episodes = []
            seen_links = set()
            for ep in ep_elements:
                title = ep.get_text(strip=True)
                link = ep.get('href')
                if link and link not in seen_links and '/episodio/' in link:
                    num_match = re.search(r'episodio[- ](\d+)', link.lower()) or re.search(r'(\d+)', title)
                    num = int(num_match.group(1)) if num_match else 0
                    if num > 0:
                        episodes.append({"n": title or f"Episódio {num}", "u": link, "num": num})
                        seen_links.add(link)
            return organizar_episodios(episodes)
        except Exception as e:
            print(f"[AnimesOnlineFHD] Erro nos episódios: {e}")
            return []
    
    @staticmethod
    async def extrair_video(url_episodio):
        browser = None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(user_agent=AnimesOnlineFHDScraper.HEADERS['User-Agent'])
                page = await context.new_page()
                await aplicar_stealth(page)
                
                # Bloqueia recursos pesados
                await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2,ttf}", lambda route: route.abort())
                
                captured = []
                page.on("request", lambda req: captured.append(req.url) if any(x in req.url for x in [".m3u8", ".mp4", "googlevideo"]) else None)
                
                await page.goto(url_episodio, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(3)
                
                # Tenta clicar no player se necessário (vários seletores possíveis)
                for selector in ["#video", "video", ".play-video", ".player-embed", "iframe"]:
                    try:
                        await page.click(selector, timeout=2000)
                        await asyncio.sleep(2)
                        if captured: break
                    except: pass
                
                if not captured:
                    # Extrai do HTML e de todos os iframes presentes
                    html = await page.content()
                    found = re.findall(r'(https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*)', html.replace('\\/', '/'))
                    captured.extend(found)
                    
                    # Busca em iframes
                    iframes = await page.query_selector_all("iframe")
                    for f in iframes:
                        try:
                            src = await f.get_attribute("src")
                            if src and src.startswith('http'):
                                p2 = await context.new_page()
                                await p2.goto(src, timeout=10000)
                                h2 = await p2.content()
                                f2 = re.findall(r'(https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*)', h2.replace('\\/', '/'))
                                captured.extend(f2)
                                await p2.close()
                        except: pass
                
                await browser.close()
                if captured:
                    video = next((u for u in captured if ".m3u8" in u or ".mp4" in u), captured[0])
                    return (video, url_episodio)
        except Exception as e:
            print(f"[AnimesOnlineFHD] Erro no vídeo: {e}")
            if browser: await browser.close()
        return (None, None)
