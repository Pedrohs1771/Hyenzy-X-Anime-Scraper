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

class GoFlixyProvider(BaseProvider):
    """Provider para GoFlixy.lol - Baseado em dados reais de network capture"""
    
    NOME = "GoFlixy.lol"
    BASE_URL = "https://goflixy.lol"
    
    @staticmethod
    async def buscar_filme(page, termo_busca):
        """Busca filmes no GoFlixy"""
        try:
            url_busca = f"{GoFlixyProvider.BASE_URL}/buscar?q={termo_busca.replace(' ', '+')}"
            await page.goto(url_busca, wait_until="domcontentloaded", timeout=15000)
            await page.wait_for_selector("a[href*='/filme/']", timeout=6000)
            results = await page.query_selector_all("a[href*='/filme/']")
            
            lista_filmes = []
            seen_links = set()
            
            for res in results[:20]:
                try:
                    title = await res.inner_text()
                    link = await res.get_attribute("href")
                    
                    if link and link not in seen_links and "/filme/" in link:
                        if not link.startswith("http"):
                            link = f"{GoFlixyProvider.BASE_URL}{link}"
                        
                        lista_filmes.append({
                            "nome": title.strip(),
                            "link": link,
                            "fonte": GoFlixyProvider.NOME,
                            "tipo": "FILME"
                        })
                        seen_links.add(link)
                except:
                    continue
            
            return lista_filmes
        except Exception as e:
            print(f"[GoFlixy] Erro na busca: {e}")
            return []
    
    @staticmethod
    async def extrair_video(url_filme):
        """Extrai URL do vídeo - método baseado em network capture real"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            await aplicar_stealth(page)
            
            # Variável para armazenar URLs capturadas
            captured_m3u8 = []
            
            # Intercepta todas as requisições de rede
            async def handle_request(request):
                url = request.url
                # Captura URLs de HLS master playlist
                if "master.m3u8" in url or ".m3u8" in url:
                    if url not in captured_m3u8:
                        captured_m3u8.append(url)
                        print(f"[GoFlixy] Stream capturado: {url[:80]}...")
            
            page.on("request", handle_request)
            
            try:
                print(f"[GoFlixy] Navegando para: {url_filme}")
                await page.goto(url_filme, wait_until="domcontentloaded", timeout=20000)
                
                # Aguarda um pouco para a página carregar completamente
                await asyncio.sleep(3)
                
                # Tenta clicar no botão de play se existir
                try:
                    play_button = await page.query_selector("button[class*='play'], .play-button, #play-button, [aria-label*='play']")
                    if play_button:
                        print("[GoFlixy] Clicando no botão play...")
                        await play_button.click()
                        await asyncio.sleep(3)
                except:
                    pass
                
                # Procura por iframe do player
                try:
                    iframes = await page.query_selector_all("iframe")
                    print(f"[GoFlixy] Encontrados {len(iframes)} iframes")
                    
                    for iframe in iframes:
                        src = await iframe.get_attribute("src")
                        if src and ("embed" in src or "player" in src or "bysevepoin" in src or "f75s" in src):
                            print(f"[GoFlixy] Navegando para iframe: {src[:80]}...")
                            
                            # Navega para o iframe
                            if not src.startswith("http"):
                                src = f"https:{src}" if src.startswith("//") else f"https://{src}"
                            
                            # Abre o iframe em uma nova aba
                            iframe_page = await context.new_page()
                            
                            # Intercepta requisições no iframe também
                            async def handle_iframe_request(request):
                                url = request.url
                                if "master.m3u8" in url or ".m3u8" in url:
                                    if url not in captured_m3u8:
                                        captured_m3u8.append(url)
                                        print(f"[GoFlixy] Stream capturado (iframe): {url[:80]}...")
                            
                            iframe_page.on("request", handle_iframe_request)
                            
                            await iframe_page.goto(src, wait_until="domcontentloaded", timeout=15000)
                            await asyncio.sleep(4)
                            
                            # Tenta clicar em play no iframe
                            try:
                                iframe_play = await iframe_page.query_selector("button, video, .play")
                                if iframe_play:
                                    await iframe_play.click()
                                    await asyncio.sleep(2)
                            except:
                                pass
                            
                            await iframe_page.close()
                            break
                except Exception as e:
                    print(f"[GoFlixy] Erro ao processar iframes: {e}")
                
                # Aguarda mais um pouco para garantir captura
                await asyncio.sleep(2)
                
                # Se capturou algum M3U8
                if captured_m3u8:
                    # Prefere master.m3u8
                    video_url = None
                    for url in captured_m3u8:
                        if "master.m3u8" in url:
                            video_url = url
                            break
                    
                    if not video_url:
                        video_url = captured_m3u8[0]
                    
                    print(f"[GoFlixy] ✓ Vídeo encontrado: {video_url[:100]}...")
                    await browser.close()
                    return (video_url, url_filme)
                
                # Se não encontrou M3U8, tenta extrair do código-fonte
                print("[GoFlixy] Tentando extrair do código-fonte...")
                content = await page.content()
                
                # Procura por URLs M3U8 no HTML
                m3u8_pattern = r'https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*'
                matches = re.findall(m3u8_pattern, content)
                
                if matches:
                    video_url = matches[0]
                    print(f"[GoFlixy] ✓ Vídeo encontrado no HTML: {video_url[:100]}...")
                    await browser.close()
                    return (video_url, url_filme)
                
                print("[GoFlixy] ✗ Nenhum stream encontrado")
                
            except Exception as e:
                print(f"[GoFlixy] Erro ao extrair vídeo: {e}")
            
            await browser.close()
            return (None, None)
    
    @staticmethod
    async def listar_episodios(page, url_filme):
        """Para filmes, retorna apenas um 'episódio'"""
        try:
            await page.goto(url_filme, wait_until="domcontentloaded", timeout=15000)
            
            title_elem = await page.query_selector("h1, .title, [class*='movie-title']")
            title = "Filme"
            if title_elem:
                title = await title_elem.inner_text()
            
            return [{
                "n": title.strip(),
                "u": url_filme,
                "num": 1
            }]
        except:
            return [{
                "n": "Filme",
                "u": url_filme,
                "num": 1
            }]