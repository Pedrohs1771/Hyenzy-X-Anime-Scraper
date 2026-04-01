import asyncio
import re
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from providers import BaseProvider
from utils import aplicar_stealth, identificar_tipo_audio, organizar_episodios

class AnimeQScraper(BaseProvider):
    """Provider para AnimeQ.net - Versão Otimizada com dados do Sniffer"""
    
    NOME = "AnimeQ.net"
    BASE_URL = "https://animeq.net"
    
    # Headers otimizados baseados no sniffer
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://animeq.net/',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # Cookies essenciais extraídos do sniffer
    COOKIES = {
        'cf_clearance': '',  # Será preenchido dinamicamente
        '_ga': '',
        '_gid': '',
    }
    
    @staticmethod
    async def buscar_anime(page, termo_busca):
        """Busca animes no site"""
        try:
            url_busca = f"{AnimeQScraper.BASE_URL}/?s={termo_busca.replace(' ', '+')}"
            loop = asyncio.get_event_loop()
            
            # Usa session para manter cookies
            session = requests.Session()
            session.headers.update(AnimeQScraper.HEADERS)
            
            response = await loop.run_in_executor(
                None, 
                lambda: session.get(url_busca, timeout=15)
            )
            
            if response.status_code != 200:
                print(f"[AnimeQ] Status {response.status_code} na busca")
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Múltiplos seletores para garantir captura
            results = (
                soup.select("div.result-item article div.details div.title a") or
                soup.select("article h2 a") or
                soup.select("div.items article a") or
                soup.select("a[href*='/anime/']")
            )
            
            lista_animes = []
            seen_links = set()
            
            for res in results[:15]:
                title = res.get_text(strip=True)
                link = res.get('href')
                
                if link and "/anime/" in link and link not in seen_links:
                    # Normaliza o link
                    if not link.startswith('http'):
                        link = AnimeQScraper.BASE_URL + link
                        
                    lista_animes.append({
                        "nome": title,
                        "link": link,
                        "fonte": AnimeQScraper.NOME,
                        "tipo": identificar_tipo_audio(title)
                    })
                    seen_links.add(link)
                    
            return lista_animes
            
        except Exception as e:
            print(f"[AnimeQ] Erro na busca: {e}")
            return []
    
    @staticmethod
    async def listar_episodios(page, url_anime):
        """Lista episódios de um anime"""
        try:
            loop = asyncio.get_event_loop()
            session = requests.Session()
            session.headers.update(AnimeQScraper.HEADERS)
            session.headers['Referer'] = url_anime
            
            response = await loop.run_in_executor(
                None,
                lambda: session.get(url_anime, timeout=15)
            )
            
            if response.status_code != 200:
                print(f"[AnimeQ] Status {response.status_code} nos episódios")
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Múltiplos seletores para episódios
            ep_elements = (
                soup.select("ul.episodios li div.episodiotitle a") or
                soup.select("a[href*='/episodio/']") or
                soup.select("div.se-c div.se-a a")
            )
            
            episodes = []
            seen_links = set()
            
            for ep in ep_elements:
                title = ep.get_text(strip=True)
                link = ep.get('href')
                
                if not link or link in seen_links:
                    continue
                    
                # Normaliza o link
                if not link.startswith('http'):
                    link = AnimeQScraper.BASE_URL + link
                
                # Extrai número do episódio
                num_match = (
                    re.search(r'episodio[- ](\d+)', link.lower()) or
                    re.search(r'ep[- ]?(\d+)', link.lower()) or
                    re.search(r'(\d+)$', link.rstrip('/'))
                )
                
                num = int(num_match.group(1)) if num_match else 0
                
                if num > 0:
                    episodes.append({
                        "n": title or f"Episódio {num}",
                        "u": link,
                        "num": num
                    })
                    seen_links.add(link)
                    
            return organizar_episodios(episodes)
            
        except Exception as e:
            print(f"[AnimeQ] Erro nos episódios: {e}")
            return []
    
    @staticmethod
    async def extrair_video(url_episodio):
        browser = None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=['--disable-blink-features=AutomationControlled']
                )
                context = await browser.new_context(
                    user_agent=AnimeQScraper.HEADERS['User-Agent'],
                    viewport={'width': 1920, 'height': 1080}
                )
                page = await context.new_page()
                await aplicar_stealth(page)
                
                # Bloqueia recursos pesados para acelerar
                await page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,webp,ico}", lambda route: route.abort())
                await page.route("**/ads/**", lambda route: route.abort())
                await page.route("**/analytics/**", lambda route: route.abort())
                
                captured = []
                
                # Captura URLs de vídeo
                def handle_request(req):
                    url = req.url
                    if "/jwplayer/" in url and "source=" in url:
                        try:
                            import urllib.parse
                            parsed = urllib.parse.urlparse(url)
                            params = urllib.parse.parse_qs(parsed.query)
                            if 'source' in params:
                                video_url = urllib.parse.unquote(params['source'][0])
                                captured.append(video_url)
                        except: pass
                    elif any(x in url for x in [".m3u8", ".mp4"]) and "mangas.cloud" in url:
                        captured.append(url)
                    elif any(x in url for x in [".m3u8", ".mp4", "googlevideo", "blogger.com"]):
                        captured.append(url)
                
                page.on("request", handle_request)
                
                # Navegação mais rápida - não espera networkidle
                try:
                    await page.goto(url_episodio, wait_until="domcontentloaded", timeout=20000)
                except Exception as e:
                    print(f"[AnimeQ] Aviso na navegação: {e}")
                
                await asyncio.sleep(2)
                
                # Extrai Post ID
                post_id = None
                try:
                    post_id = await page.evaluate("""
                        () => {
                            const li = document.querySelector('#playeroptions li[data-post]');
                            return li ? li.dataset.post : null;
                        }
                    """)
                except: pass
                
                # Tenta API do DooPlayer (mais rápido)
                if post_id:
                    for num in range(1, 4):  # Reduzido para 3 tentativas
                        try:
                            api_url = f"{AnimeQScraper.BASE_URL}/wp-json/dooplayer/v2/{post_id}/tv/{num}"
                            response = await page.request.get(api_url, timeout=8000)
                            
                            if response.ok:
                                data = await response.json()
                                if 'embed_url' in data and data['embed_url']:
                                    embed = data['embed_url']
                                    
                                    # Extrai source do embed_url
                                    if "source=" in embed:
                                        try:
                                            import urllib.parse
                                            parsed = urllib.parse.urlparse(embed)
                                            params = urllib.parse.parse_qs(parsed.query)
                                            if 'source' in params:
                                                video_url = urllib.parse.unquote(params['source'][0])
                                                captured.append(video_url)
                                                break  # Encontrou, para aqui
                                        except: pass
                                    
                                    # Verifica se já é URL de vídeo
                                    if any(x in embed for x in ['.m3u8', '.mp4', 'mangas.cloud']):
                                        captured.append(embed)
                                        break
                        except: continue
                
                # Se já encontrou na API, retorna
                if captured:
                    video = next((u for u in captured if "mangas.cloud" in u and ".mp4" in u), captured[0])
                    await browser.close()
                    return (video, url_episodio)
                
                # Fallback: Clica no primeiro player
                try:
                    await page.wait_for_selector("#playeroptions li", timeout=8000)
                    first_option = await page.query_selector("#playeroptions li:first-child")
                    
                    if first_option:
                        await first_option.scroll_into_view_if_needed()
                        await first_option.click()
                        await asyncio.sleep(3)
                        
                        # Verifica iframe
                        iframe = await page.query_selector('iframe[src*="jwplayer"]')
                        if iframe:
                            src = await iframe.get_attribute('src')
                            if src and "source=" in src:
                                try:
                                    import urllib.parse
                                    parsed = urllib.parse.urlparse(src)
                                    params = urllib.parse.parse_qs(parsed.query)
                                    if 'source' in params:
                                        video_url = urllib.parse.unquote(params['source'][0])
                                        captured.append(video_url)
                                except: pass
                except: pass
                
                # Último fallback: busca no HTML
                if not captured:
                    try:
                        html = await page.content()
                        # Busca source= no HTML
                        sources = re.findall(r'source=([^&\s"\']+)', html)
                        for s in sources:
                            try:
                                import urllib.parse
                                decoded = urllib.parse.unquote(s)
                                if any(x in decoded for x in ['.m3u8', '.mp4', 'mangas.cloud']):
                                    captured.append(decoded)
                            except: pass
                        
                        # Busca URLs diretas
                        found = re.findall(r'(https?://[^\s"\']+(?:mangas\.cloud|\.m3u8|\.mp4)[^\s"\']*)', html)
                        captured.extend(found)
                    except: pass
                
                await browser.close()
                
                if captured:
                    # Prioriza mangas.cloud
                    video = (
                        next((u for u in captured if "mangas.cloud" in u and ".mp4" in u), None) or
                        next((u for u in captured if ".m3u8" in u), None) or
                        next((u for u in captured if ".mp4" in u), None) or
                        captured[0]
                    )
                    return (video, url_episodio)
                    
        except Exception as e:
            print(f"[AnimeQ] Erro no vídeo: {e}")
            if browser: 
                try: await browser.close()
                except: pass
        
        return (None, None)