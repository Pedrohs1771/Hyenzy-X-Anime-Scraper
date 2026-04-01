import asyncio
import base64
import re
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
            url_busca = f"{AnimeCoreScraper.BASE_URL}/busca-detalhada/?s_keyword={termo_busca.replace(' ', '+')}&orderby=popular&order=DESC&action=advanced_search&page=1"
            await page.goto(url_busca, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_selector("h3 a", timeout=6000)
            results = await page.query_selector_all("h3 a")
            
            lista_animes = []
            for res in results[:15]:
                title = await res.inner_text()
                link = await res.get_attribute("href")
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
            await page.goto(url_anime, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_selector("a[href*='/watch/']", timeout=6000)
            ep_elements = await page.query_selector_all("a[href*='/watch/']")
            
            episodes = []
            seen_links = set()
            for ep in ep_elements:
                title = (await ep.inner_text()).strip()
                link = await ep.get_attribute("href")
                if link and link not in seen_links and "episodio" in link.lower():
                    ep_num_match = re.search(r'episodio-(\d+)', link.lower())
                    ep_num = int(ep_num_match.group(1)) if ep_num_match else 0
                    episodes.append({"n": title or f"Episódio {ep_num}", "u": link, "num": ep_num})
                    seen_links.add(link)
            
            return organizar_episodios(episodes)
        except:
            return []
    
    @staticmethod
    async def extrair_video(url_episodio):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            await aplicar_stealth(page)

            captured_urls = []
            
            async def handle_request(request):
                url = request.url
                if any(x in url for x in [".m3u8", ".mp4", "googlevideo.com"]):
                    if url not in captured_urls:
                        captured_urls.append(url)

            page.on("request", handle_request)
            
            try:
                await page.goto(url_episodio, wait_until="domcontentloaded", timeout=15000)
                await asyncio.sleep(1.5)
                
                # Extrai player via Base64
                embed_element = await page.query_selector("[data-embed-id]")
                player_url = None
                
                if embed_element:
                    embed_data = await embed_element.get_attribute("data-embed-id")
                    if embed_data and ":" in embed_data:
                        try:
                            player_url = base64.b64decode(embed_data.split(':')[1]).decode('utf-8')
                        except:
                            pass
                
                if player_url:
                    await page.goto(player_url, wait_until="domcontentloaded", timeout=15000)
                    await asyncio.sleep(2)
                    
                    # Extrai do código-fonte (Blogger)
                    content = await page.content()
                    for match in re.findall(r'https://[^"\s]+googlevideo\.com/[^"\s]+', content):
                        url = match.replace("\\u0026", "&")
                        if url not in captured_urls:
                            captured_urls.append(url)
                
                if not captured_urls:
                    # Tenta extrair de scripts globais
                    html = await page.content()
                    found = re.findall(r'(https?://[^\s"\']+\.(?:m3u8|mp4)[^\s"\']*)', html.replace('\\/', '/'))
                    captured_urls.extend(found)

                if captured_urls:
                    video_url = next((u for u in captured_urls if ".m3u8" in u), captured_urls[0])
                    return (video_url, url_episodio)
            except:
                pass

            await browser.close()
            return (None, None)