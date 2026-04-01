import json
import os
import re
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════
#                           CONFIGURAÇÃO
# ═══════════════════════════════════════════════════════════════════════════

CONFIG_FILE = "config_scrapers.json"
HISTORICO_FILE = "historico_animes.json"

def carregar_config():
    """Carrega configuração de scrapers ativos"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def salvar_config(config):
    """Salva configuração de scrapers"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

def carregar_historico():
    """Carrega histórico agrupado por anime"""
    if os.path.exists(HISTORICO_FILE):
        try:
            with open(HISTORICO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def salvar_historico_episodio(anime_nome, episodio_num, fonte, anime_info):
    """Salva episódio assistido agrupado por anime"""
    historico = carregar_historico()
    chave_anime = f"{anime_nome}|{fonte}"
    
    if chave_anime not in historico:
        historico[chave_anime] = {
            'anime': anime_nome,
            'fonte': fonte,
            'anime_info': anime_info,
            'episodios_assistidos': [],
            'ultimo_episodio': episodio_num,
            'ultimo_acesso': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_assistidos': 0
        }
    
    eps_assistidos = historico[chave_anime]['episodios_assistidos']
    if episodio_num not in eps_assistidos:
        eps_assistidos.append(episodio_num)
    
    historico[chave_anime]['ultimo_episodio'] = episodio_num
    historico[chave_anime]['ultimo_acesso'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    historico[chave_anime]['total_assistidos'] = len(eps_assistidos)
    historico[chave_anime]['episodios_assistidos'] = sorted(eps_assistidos)
    
    with open(HISTORICO_FILE, 'w', encoding='utf-8') as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)

def obter_historico_ordenado():
    """Retorna histórico ordenado por último acesso"""
    historico = carregar_historico()
    items = list(historico.values())
    items.sort(key=lambda x: x['ultimo_acesso'], reverse=True)
    return items

# ═══════════════════════════════════════════════════════════════════════════
#                           UTILITÁRIOS
# ═══════════════════════════════════════════════════════════════════════════

async def aplicar_stealth(page):
    """Remove detecção de automação"""
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        window.chrome = { runtime: {} };
    """)

def fechar_mpv():
    """Fecha qualquer instância do MPV"""
    import psutil
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and 'mpv' in proc.info['name'].lower():
                proc.kill()
        except:
            pass

def limpar_tela():
    """Limpa terminal"""
    os.system('cls' if os.name == 'nt' else 'clear')

def extrair_numeros_episodio(texto):
    """Extrai número do episódio"""
    match = re.search(r'\d+', texto)
    return int(match.group()) if match else 0

def organizar_episodios(lista_eps):
    """Organiza e filtra episódios removendo links sociais"""
    eps_validos = []
    for ep in lista_eps:
        nome_lower = ep['n'].lower()
        if any(rede in nome_lower for rede in ['telegram', 'reddit', 'facebook', 'whatsapp', 'twitter', 'tumblr']):
            continue
        if 'episodio' in nome_lower or 'episode' in nome_lower or re.search(r'\d+', ep['n']):
            eps_validos.append(ep)
    
    return sorted(eps_validos, key=lambda x: extrair_numeros_episodio(x['n']))

def normalizar_nome(nome):
    """Normaliza nome para comparação"""
    import unicodedata
    nome = unicodedata.normalize('NFD', nome)
    nome = ''.join(c for c in nome if unicodedata.category(c) != 'Mn')
    nome = nome.lower()
    for palavra in ['dublado', 'legendado', 'online', 'assistir']:
        nome = nome.replace(palavra, '')
    nome = re.sub(r'[^a-z0-9\s]', '', nome)
    return ' '.join(nome.split())

def animes_sao_duplicados(nome1, nome2):
    """Verifica se dois nomes são o mesmo anime"""
    norm1 = normalizar_nome(nome1)
    norm2 = normalizar_nome(nome2)
    if norm1 == norm2:
        return True
    if len(norm1) > 5 and len(norm2) > 5:
        # Se um nome contém o outro, mas eles têm sufixos de temporada (como II, 2, etc), não são duplicados
        if (norm1 in norm2 or norm2 in norm1) and abs(len(norm1) - len(norm2)) < 15:
            # Verifica se há números ou algarismos romanos que os diferenciem
            diff = norm1.replace(norm2, '').strip() or norm2.replace(norm1, '').strip()
            if any(char.isdigit() for char in diff) or any(r in diff.upper() for r in ['I', 'V', 'X']):
                return False
            return True
    return False

def identificar_tipo_audio(titulo):
    """Identifica se é dublado ou legendado"""
    titulo_lower = titulo.lower()
    if 'dub' in titulo_lower or 'dublado' in titulo_lower:
        return 'DUB'
    elif 'leg' in titulo_lower or 'legendado' in titulo_lower:
        return 'LEG'
    return None