"""
ps2.py - Provider para jogos PS2 traduzidos do João13
Coloque este arquivo em: providers-games/ps2.py
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re

class PS2Provider:
    NAME = "PS2 João13 Traduções"
    ACTIVE = True
    
    BASE_URL = "https://joao13traducoes.com/"
    SEARCH_URL = BASE_URL + "?s={query}"
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Referer": BASE_URL
    }
    
    # Palavras que indicam que NÃO é uma ISO completa (apenas patch)
    BLACKLIST = [
        "DELTAPATCH", "XDELTA", "PATCH APENAS", 
        "SOMENTE TRADUÇÃO", "PATCH DE TRADUÇÃO"
    ]
    
    @classmethod
    async def search(cls, query):
        """Busca jogos PS2 traduzidos"""
        url = cls.SEARCH_URL.format(query=query.replace(" ", "+"))
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=cls.HEADERS, timeout=15) as response:
                    if response.status != 200:
                        return []
                    
                    html = await response.text()
        except Exception as e:
            print(f"[PS2] Erro na busca: {e}")
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        seen = set()
        
        # Busca por títulos de jogos PS2
        for item in soup.find_all(['h1', 'h2', 'h3', 'a']):
            text = item.get_text().strip()
            upper_text = text.upper()
            
            # Deve ter [PS2] no título
            if "[PS2]" not in upper_text:
                continue
            
            # Não pode ser apenas patch
            is_patch = any(word in upper_text for word in cls.BLACKLIST)
            if is_patch:
                continue
            
            # Extrai link
            link = item.find('a') if item.name != 'a' else item
            if not link or not link.has_attr('href'):
                continue
            
            href = link['href']
            
            # Valida URL
            if not href.startswith(cls.BASE_URL):
                continue
            if "/category/" in href:
                continue
            if len(href) <= len(cls.BASE_URL) + 5:
                continue
            
            # Evita duplicatas
            if href in seen:
                continue
            
            seen.add(href)
            results.append({
                'title': text.strip(),
                'url': href
            })
        
        return results
    
    @classmethod
    def _clean_filename(cls, filename):
        """Limpa e decodifica nomes de arquivos"""
        import urllib.parse
        # Decodifica URL encoding (%20, %5B, etc)
        decoded = urllib.parse.unquote(filename)
        # Remove caracteres ruins
        cleaned = decoded.replace('%', '').strip()
        return cleaned if cleaned else filename
    
    @classmethod
    def _is_valid_download(cls, url, text):
        """Verifica se é um link de download válido"""
        # Lista negra de links inúteis
        blacklist = [
            'discord.gg', 'discord.com',
            'facebook.com', 'twitter.com', 'instagram.com',
            'youtube.com', 'youtu.be',
            cls.BASE_URL  # Links internos do site
        ]
        
        # Verifica se está na blacklist
        for bad in blacklist:
            if bad in url.lower():
                return False
        
        # Texto deve ter conteúdo útil
        if text:
            text_lower = text.lower()
            useless = ['discord', 'facebook', 'twitter', 'instagram', 'youtube', 'compartilhar', 'share']
            if any(word in text_lower for word in useless):
                return False
        
        return True
    
    @classmethod
    async def extract_downloads(cls, url):
        """Extrai links de download do HuggingFace e outros"""
        print(f"[PS2] Acessando página: {url}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=cls.HEADERS, timeout=15) as response:
                    if response.status != 200:
                        print(f"[PS2] Erro HTTP {response.status}")
                        return []
                    
                    html = await response.text()
                    
        except Exception as e:
            print(f"[PS2] Erro ao acessar página: {e}")
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        downloads = []
        seen_urls = set()
        
        print(f"[PS2] Analisando HTML...")
        
        # ===== MÉTODO 1: Links diretos do HuggingFace =====
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # HuggingFace com resolve (download direto)
            if "huggingface.co" in href and "resolve" in href:
                if href not in seen_urls:
                    seen_urls.add(href)
                    
                    # Extrai e limpa nome do arquivo
                    filename = href.split('/')[-1] if '/' in href else "Download"
                    filename = cls._clean_filename(filename)
                    
                    name_type = "Censurado" if "censurado" in href.lower() else "Completo"
                    
                    downloads.append({
                        'name': f"{filename} ({name_type})",
                        'url': href,
                        'server': 'HuggingFace'
                    })
                    print(f"[PS2] ✓ HuggingFace: {filename}")
        
        # ===== MÉTODO 2: Links do HuggingFace (qualquer) =====
        if not downloads:
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text().strip()
                
                if "huggingface.co" in href and href not in seen_urls:
                    if cls._is_valid_download(href, text):
                        seen_urls.add(href)
                        clean_text = cls._clean_filename(text) if text else "HuggingFace Link"
                        downloads.append({
                            'name': clean_text[:60],
                            'url': href,
                            'server': 'HuggingFace'
                        })
                        print(f"[PS2] ✓ HuggingFace (geral): {clean_text[:40]}")
        
        # ===== MÉTODO 3: Busca por palavras-chave =====
        if not downloads:
            keywords = ['download', 'baixar', 'mega', 'drive', 'mediafire', 'gdrive', 'hugging']
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.get_text().strip().lower()
                
                # Valida link
                if not cls._is_valid_download(href, text):
                    continue
                
                # Verifica palavras-chave
                if any(kw in text for kw in keywords):
                    if href.startswith('http') and href not in seen_urls:
                        seen_urls.add(href)
                        clean_text = cls._clean_filename(link.get_text().strip())
                        downloads.append({
                            'name': clean_text[:60] or "Download Link",
                            'url': href,
                            'server': 'Externo'
                        })
                        print(f"[PS2] ✓ Link externo: {clean_text[:40]}")
        
        # ===== MÉTODO 4: Busca em botões e divs =====
        if not downloads:
            # Procura em elementos com classes comuns de download
            for element in soup.find_all(['div', 'button', 'span'], class_=re.compile('download|button|link', re.I)):
                for link in element.find_all('a', href=True):
                    href = link['href']
                    text = link.get_text().strip()
                    
                    if href.startswith('http') and href not in seen_urls:
                        if cls._is_valid_download(href, text):
                            seen_urls.add(href)
                            clean_text = cls._clean_filename(text)
                            downloads.append({
                                'name': clean_text[:60] or "Download",
                                'url': href,
                                'server': 'Detectado'
                            })
                            print(f"[PS2] ✓ Detectado: {clean_text[:40]}")
        
        # ===== MÉTODO 5: REGEX para URLs em texto =====
        if not downloads:
            print(f"[PS2] Tentando REGEX no HTML...")
            # Procura URLs no texto
            url_pattern = r'https?://(?:www\.)?(?:huggingface\.co|mega\.nz|drive\.google\.com|mediafire\.com)[^\s<>"\']*'
            matches = re.findall(url_pattern, html)
            
            for match in matches:
                if match not in seen_urls and cls._is_valid_download(match, ''):
                    seen_urls.add(match)
                    # Extrai nome do servidor
                    if 'huggingface' in match:
                        server = 'HuggingFace'
                        filename = match.split('/')[-1]
                        name = cls._clean_filename(filename)
                    elif 'mega' in match:
                        server = 'MEGA'
                        name = "MEGA Download"
                    elif 'drive.google' in match:
                        server = 'Google Drive'
                        name = "Google Drive"
                    else:
                        server = 'Link Direto'
                        name = "Download"
                    
                    downloads.append({
                        'name': name,
                        'url': match,
                        'server': server
                    })
                    print(f"[PS2] ✓ REGEX [{server}]: {name[:40]}")
        
        # ===== Aviso se não encontrou downloads =====
        if not downloads:
            print(f"\n{C.YL}[PS2] ⚠️  Nenhum link de download encontrado!{C.RS}")
            print(f"{C.YL}[PS2] Este jogo pode ter o link apenas no Discord do João13{C.RS}\n")
        
        return downloads


# Importa cores se disponível
try:
    from games_core import C
except:
    class C:
        YL = RS = ''