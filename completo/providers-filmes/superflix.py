import asyncio
import re
from playwright.async_api import async_playwright

try:
    from providers import BaseProvider
except ImportError:
    class BaseProvider:
        NOME = None
        BASE_URL = None

try:
    from utils import aplicar_stealth
except ImportError:
    async def aplicar_stealth(page):
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
        """)

class SuperFlixProvider(BaseProvider):
    """Provider para SuperFlix1.cloud - Com bloqueio agressivo de anúncios"""
    
    NOME = "SuperFlix1.cloud"
    BASE_URL = "https://superflix1.cloud"
    
    # Domínios de anúncios para bloquear
    AD_DOMAINS = [
        "adangle.online",
        "entrapsoorki.top",
        "apptracer.ru",
        "doubleclick.net",
        "googlesyndication.com",
        "googletagmanager.com",
        "facebook.com",
        "facebook.net",
        "fbcdn.net",
        "ad-delivery",
        "ads-",
        "analytics",
        "betwinner",
        "dummy.mp4"  # Vídeo dummy de anúncio
    ]
    
    @staticmethod
    async def buscar_filme(page, termo_busca):
        """Busca filmes no SuperFlix"""
        try:
            url_busca = f"{SuperFlixProvider.BASE_URL}/buscar?s={termo_busca.replace(' ', '+')}"
            await page.goto(url_busca, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_selector("a[href*='/filme/'], a[href*='/filmes/']", timeout=6000)
            results = await page.query_selector_all("a[href*='/filme/'], a[href*='/filmes/']")
            
            lista_filmes = []
            seen_links = set()
            
            for res in results[:20]:
                try:
                    title = await res.inner_text()
                    link = await res.get_attribute("href")
                    
                    if link and link not in seen_links and ("/filme/" in link or "/filmes/" in link):
                        if not link.startswith("http"):
                            link = f"{SuperFlixProvider.BASE_URL}{link}"
                        
                        lista_filmes.append({
                            "nome": title.strip(),
                            "link": link,
                            "fonte": SuperFlixProvider.NOME,
                            "tipo": "FILME"
                        })
                        seen_links.add(link)
                except:
                    continue
            
            return lista_filmes
        except:
            return []
    
    @staticmethod
    def is_ad_url(url):
        """Verifica se a URL é de anúncio"""
        url_lower = url.lower()
        for domain in SuperFlixProvider.AD_DOMAINS:
            if domain in url_lower:
                return True
        return False
    
    @staticmethod
    async def extrair_video(url_filme):
        """Extrai URL do vídeo com bloqueio agressivo de anúncios"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            
            # BLOQUEIA ANÚNCIOS em todo o contexto
            await context.route("**/*", lambda route: (
                route.abort() if SuperFlixProvider.is_ad_url(route.request.url)
                else route.continue_()
            ))
            
            page = await context.new_page()
            await aplicar_stealth(page)
            
            # Armazena URLs de vídeo capturadas
            captured_videos = {
                "mp4": [],
                "m3u8": [],
                "google_storage": []
            }
            
            async def handle_request(request):
                url = request.url
                
                # PRIORIDADE 1: Google Storage (melhor qualidade)
                if "storage.googleapis.com" in url and ".mp4" in url:
                    if url not in captured_videos["google_storage"]:
                        captured_videos["google_storage"].append(url)
                
                # PRIORIDADE 2: M3U8
                elif ".m3u8" in url and not SuperFlixProvider.is_ad_url(url):
                    if url not in captured_videos["m3u8"]:
                        captured_videos["m3u8"].append(url)
                
                # PRIORIDADE 3: MP4 direto
                elif ".mp4" in url and not SuperFlixProvider.is_ad_url(url):
                    # Filtra URLs de anúncio e dummy
                    if "dummy" not in url.lower() and "betwinner" not in url.lower():
                        if url not in captured_videos["mp4"]:
                            captured_videos["mp4"].append(url)
            
            page.on("request", handle_request)
            
            try:
                await page.goto(url_filme, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(3)
                
                # Tenta clicar no play
                try:
                    play_selectors = [
                        "button[class*='play']",
                        ".play-button",
                        "#play-button",
                        "button[aria-label*='play']",
                        ".jw-icon-playback",  # JW Player
                        ".vjs-big-play-button"  # Video.js
                    ]
                    
                    for selector in play_selectors:
                        try:
                            play_button = await page.query_selector(selector)
                            if play_button:
                                await play_button.click()
                                await asyncio.sleep(3)
                                break
                        except:
                            continue
                except:
                    pass
                
                # Procura iframes do player
                try:
                    iframes = await page.query_selector_all("iframe")
                    for iframe in iframes:
                        src = await iframe.get_attribute("src")
                        if not src:
                            continue
                        
                        # Pula iframes de anúncio
                        if SuperFlixProvider.is_ad_url(src):
                            continue
                        
                        if "player" in src or "embed" in src or "assistirseriesonline" in src:
                            if not src.startswith("http"):
                                src = f"https:{src}" if src.startswith("//") else f"https://{src}"
                            
                            iframe_page = await context.new_page()
                            
                            async def handle_iframe_request(request):
                                url = request.url
                                
                                if "storage.googleapis.com" in url and ".mp4" in url:
                                    if url not in captured_videos["google_storage"]:
                                        captured_videos["google_storage"].append(url)
                                elif ".m3u8" in url and not SuperFlixProvider.is_ad_url(url):
                                    if url not in captured_videos["m3u8"]:
                                        captured_videos["m3u8"].append(url)
                                elif ".mp4" in url and not SuperFlixProvider.is_ad_url(url):
                                    if "dummy" not in url.lower() and "betwinner" not in url.lower():
                                        if url not in captured_videos["mp4"]:
                                            captured_videos["mp4"].append(url)
                            
                            iframe_page.on("request", handle_iframe_request)
                            await iframe_page.goto(src, wait_until="domcontentloaded", timeout=15000)
                            await asyncio.sleep(5)  # Mais tempo para carregar
                            
                            # Tenta clicar em play no iframe
                            try:
                                for selector in play_selectors:
                                    try:
                                        iframe_play = await iframe_page.query_selector(selector)
                                        if iframe_play:
                                            await iframe_play.click()
                                            await asyncio.sleep(3)
                                            break
                                    except:
                                        continue
                            except:
                                pass
                            
                            await iframe_page.close()
                except:
                    pass
                
                await asyncio.sleep(3)
                
                # RETORNA na ordem de prioridade
                video_url = None
                
                # 1. Google Storage (melhor qualidade, direto)
                if captured_videos["google_storage"]:
                    video_url = captured_videos["google_storage"][0]
                
                # 2. M3U8 (streaming adaptativo)
                elif captured_videos["m3u8"]:
                    # Prefere master.m3u8
                    for url in captured_videos["m3u8"]:
                        if "master.m3u8" in url:
                            video_url = url
                            break
                    if not video_url:
                        video_url = captured_videos["m3u8"][0]
                
                # 3. MP4 direto
                elif captured_videos["mp4"]:
                    video_url = captured_videos["mp4"][0]
                
                if video_url:
                    await browser.close()
                    return (video_url, url_filme)
                
                # Fallback: extrai do HTML
                content = await page.content()
                
                # Procura Google Storage no HTML
                google_storage_pattern = r'https://storage\.googleapis\.com/mediastorage/[^\s"\'<>]+\.mp4'
                google_matches = re.findall(google_storage_pattern, content)
                if google_matches:
                    await browser.close()
                    return (google_matches[0], url_filme)
                
                # Procura M3U8 no HTML
                m3u8_pattern = r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*'
                m3u8_matches = re.findall(m3u8_pattern, content)
                if m3u8_matches:
                    for match in m3u8_matches:
                        if not SuperFlixProvider.is_ad_url(match):
                            await browser.close()
                            return (match, url_filme)
                
            except:
                pass
            
            await browser.close()
            return (None, None)
    
    @staticmethod
    async def listar_episodios(page, url_filme):
        """Para filmes, retorna apenas um item"""
        try:
            await page.goto(url_filme, wait_until="domcontentloaded", timeout=15000)
            title_elem = await page.query_selector("h1, .title, .movie-title")
            title = "Filme"
            if title_elem:
                title = await title_elem.inner_text()
            
            return [{"n": title.strip(), "u": url_filme, "num": 1}]
        except:
            return [{"n": "Filme", "u": url_filme, "num": 1}]