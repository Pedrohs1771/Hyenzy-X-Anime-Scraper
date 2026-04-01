import asyncio
import base64
import re
import json
from playwright.async_api import async_playwright
from providers import BaseProvider
from utils import aplicar_stealth, identificar_tipo_audio, organizar_episodios

class AnimeCoreScraper(BaseProvider):
    """Provider para AnimeCore.to"""
    
    NOME = "AnimeCore.to"
    BASE_URL = "https://animecore.to"
    
    @staticmethod
    async def buscar_anime(page, termo_busca):
        try:
            # Usa a API de busca instantânea como visto no JSON
            search_url = f"{AnimeCoreScraper.BASE_URL}/wp-admin/admin-ajax.php?action=instant_search&query={termo_busca.replace(' ', '+')}"
            
            # Faz requisição direta à API
            response = await page.evaluate(f"""async () => {{
                const response = await fetch("{search_url}");
                return await response.json();
            }}""")
            
            lista_animes = []
            if isinstance(response, dict) and "data" in response:
                for item in response["data"]:
                    if isinstance(item, dict) and "title" in item and "permalink" in item:
                        title = item["title"]
                        link = item["permalink"]
                        tipo_audio = identificar_tipo_audio(title)
                        lista_animes.append({
                            "nome": title.strip(), 
                            "link": link,
                            "fonte": AnimeCoreScraper.NOME,
                            "tipo": tipo_audio
                        })
            
            return lista_animes[:15]  # Limita a 15 resultados
            
        except Exception as e:
            print(f"Erro na busca: {e}")
            # Fallback: método tradicional
            try:
                url_busca = f"{AnimeCoreScraper.BASE_URL}/busca-detalhada/?s_keyword={termo_busca.replace(' ', '+')}"
                await page.goto(url_busca, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_selector("h3 a, .anime-title a", timeout=6000)
                results = await page.query_selector_all("h3 a, .anime-title a")
                
                lista_animes = []
                for res in results[:15]:
                    title = await res.inner_text()
                    link = await res.get_attribute("href")
                    if link and "anime/" in link:
                        tipo_audio = identificar_tipo_audio(title)
                        lista_animes.append({
                            "nome": title.strip(), 
                            "link": link,
                            "fonte": AnimeCoreScraper.NOME,
                            "tipo": tipo_audio
                        })
                return lista_animes
            except:
                return []
    
    @staticmethod
    async def listar_episodios(page, url_anime):
        try:
            # Extrai o ID do anime da URL
            anime_id_match = re.search(r'anime/([^/]+)', url_anime)
            if anime_id_match:
                anime_slug = anime_id_match.group(1)
                
                # Tenta usar a API para obter episódios
                api_url = f"{AnimeCoreScraper.BASE_URL}/wp-admin/admin-ajax.php?action=get_episodes&anime_id={anime_slug}&page=1&order=desc"
                
                response = await page.evaluate(f"""async () => {{
                    const response = await fetch("{api_url}");
                    return await response.json();
                }}""")
                
                if isinstance(response, dict) and "data" in response:
                    episodes = []
                    for episode in response["data"]:
                        if isinstance(episode, dict) and "title" in episode and "permalink" in episode:
                            title = episode["title"]
                            link = episode["permalink"]
                            ep_num_match = re.search(r'episodio-(\d+)', link.lower())
                            ep_num = int(ep_num_match.group(1)) if ep_num_match else 0
                            episodes.append({
                                "n": title.strip() or f"Episódio {ep_num}", 
                                "u": link, 
                                "num": ep_num
                            })
                    
                    return organizar_episodios(episodes)
            
            # Fallback: método tradicional
            await page.goto(url_anime, wait_until="domcontentloaded", timeout=15000)
            
            # Espera por elementos de episódios
            selectors = [
                "a[href*='/watch/']",
                ".episode-item a",
                ".episodes-list a",
                ".list-episodes a"
            ]
            
            episodes = []
            seen_links = set()
            
            for selector in selectors:
                try:
                    await page.wait_for_selector(selector, timeout=3000)
                    ep_elements = await page.query_selector_all(selector)
                    
                    for ep in ep_elements:
                        title = (await ep.inner_text()).strip()
                        link = await ep.get_attribute("href")
                        
                        if link and link not in seen_links and ("episodio" in link.lower() or "watch" in link.lower()):
                            ep_num_match = re.search(r'episodio-(\d+)', link.lower())
                            ep_num = int(ep_num_match.group(1)) if ep_num_match else 0
                            
                            episodes.append({
                                "n": title or f"Episódio {ep_num}", 
                                "u": link, 
                                "num": ep_num
                            })
                            seen_links.add(link)
                except:
                    continue
            
            return organizar_episodios(episodes)
            
        except Exception as e:
            print(f"Erro ao listar episódios: {e}")
            return []
    
    @staticmethod
    async def extrair_video(url_episodio):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = await context.new_page()
            await aplicar_stealth(page)

            captured_urls = []
            
            async def handle_request(request):
                url = request.url
                # Filtra URLs de vídeo baseado no JSON
                if any(x in url for x in [
                    ".m3u8", ".mp4", "googlevideo.com", 
                    "proxycdn.cc", "videoplayback"
                ]) and ("video/mp4" in request.headers.get("content-type", "") or 
                       "video" in request.resource_type):
                    if url not in captured_urls:
                        captured_urls.append(url)
                        print(f"URL de vídeo capturada: {url[:100]}...")

            page.on("request", handle_request)
            
            try:
                # Navega para o episódio
                await page.goto(url_episodio, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(3)
                
                # Procura por iframes de player
                iframes = await page.query_selector_all("iframe")
                for iframe in iframes:
                    try:
                        src = await iframe.get_attribute("src")
                        if src and ("blogger.com" in src or "youtube" in src):
                            print(f"Encontrado iframe: {src}")
                            # Navega para o iframe para capturar requisições
                            await page.goto(src, wait_until="domcontentloaded", timeout=15000)
                            await asyncio.sleep(2)
                            break
                    except:
                        continue
                
                # Extrai URLs de vídeo do conteúdo da página
                content = await page.content()
                
                # Padrões comuns de URLs de vídeo
                patterns = [
                    r'https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*',
                    r'https?://[^\s"\']+googlevideo\.com/[^\s"\']+',
                    r'https?://proxycdn\.cc/[^\s"\']+\.mp4',
                    r'src\s*[=:]\s*["\']([^"\']+\.(?:m3u8|mp4))["\']',
                    r'file\s*[=:]\s*["\']([^"\']+\.(?:m3u8|mp4))["\']'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        url = match.replace("\\/", "/").replace("\\u0026", "&")
                        if url not in captured_urls and any(x in url for x in [".m3u8", ".mp4"]):
                            captured_urls.append(url)
                
                # Se não encontrou URLs, tenta interagir com o player
                if not captured_urls:
                    # Clica em botões de play se existirem
                    play_buttons = await page.query_selector_all("button, [onclick*='play'], [class*='play']")
                    for btn in play_buttons[:3]:  # Tenta os primeiros 3 botões
                        try:
                            await btn.click()
                            await asyncio.sleep(1)
                        except:
                            pass
                
                # Filtra URLs válidas
                video_urls = [
                    url for url in captured_urls 
                    if any(ext in url.lower() for ext in ['.mp4', '.m3u8', 'videoplayback'])
                ]
                
                if video_urls:
                    # Prefere MP4 direto, depois M3U8, depois outras
                    for url in video_urls:
                        if '.mp4' in url.lower() and 'proxycdn.cc' in url:
                            return (url, url_episodio)
                    
                    for url in video_urls:
                        if '.m3u8' in url.lower():
                            return (url, url_episodio)
                    
                    return (video_urls[0], url_episodio)
                    
            except Exception as e:
                print(f"Erro ao extrair vídeo: {e}")
            
            finally:
                await browser.close()
            
            return (None, None)