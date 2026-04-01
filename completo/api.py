import asyncio
import subprocess
import sys
import os
import importlib
import pkgutil
from datetime import datetime
from playwright.async_api import async_playwright

# ═══════════════════════════════════════════════════════════════════════════
#                         CONFIGURAÇÕES DE AMBIENTE E UTILS
# ═══════════════════════════════════════════════════════════════════════════

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from utils import *
except ImportError:
    print("\033[1;31m[!] Erro: arquivo 'utils.py' não encontrado.\033[0m")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════
#                               CORES E ESTILO (TUI)
# ═══════════════════════════════════════════════════════════════════════════

class Style:
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'
    CLEAR = '\033[H\033[J'
    BG_BLUE = '\033[44m'

def draw_header():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{Style.CYAN}{Style.BOLD}╭────────────────────────────────────────────────────────────────────────────╮")
    print(f"│   {Style.MAGENTA}👻 HYENZY-X ANIME{Style.CYAN}                                           v3.0.0   │")
    print(f"│   {Style.DIM}Multi-Source Scraper • Anime4K Upscale • Playwright Core{Style.RESET}{Style.CYAN}         │")
    print(f"╰────────────────────────────────────────────────────────────────────────────╯{Style.RESET}")

def draw_footer(msg="Use os números para selecionar ou 'v' para voltar"):
    print(f"\n{Style.DIM} 💡 {msg}{Style.RESET}")

def input_styled(prompt):
    return input(f"{Style.MAGENTA} {Style.BOLD}❯ {Style.RESET}{prompt}: ").strip()

# ═══════════════════════════════════════════════════════════════════════════
#                         AUTO-DESCOBERTA DE PROVIDERS
# ═══════════════════════════════════════════════════════════════════════════

def carregar_providers_automaticamente():
    providers_encontrados = []
    providers_path = os.path.join(os.path.dirname(__file__), 'providers')
    
    if not os.path.exists(providers_path):
        return []
    
    if providers_path not in sys.path:
        sys.path.insert(0, providers_path)
    
    try:
        from providers import BaseProvider
    except ImportError:
        return []

    for _, modname, _ in pkgutil.iter_modules([providers_path]):
        if modname == '__init__': continue
        try:
            module = importlib.import_module(modname)
            for item_name in dir(module):
                item = getattr(module, item_name)
                if (isinstance(item, type) and issubclass(item, BaseProvider) and item is not BaseProvider):
                    if hasattr(item, 'NOME') and item.NOME:
                        providers_encontrados.append(item)
        except: continue
    
    return providers_encontrados

# ═══════════════════════════════════════════════════════════════════════════
#                         GERENCIADOR DE SCRAPERS
# ═══════════════════════════════════════════════════════════════════════════

class ScraperManager:
    def __init__(self):
        self.providers_classes = carregar_providers_automaticamente()
        self.scrapers = {p.NOME: p for p in self.providers_classes}
        self.config = carregar_config()
        
        # Ativa novos providers automaticamente
        for nome in self.scrapers.keys():
            if nome not in self.config:
                self.config[nome] = True
        
        self.upscale_config = self.config.get('upscale_profile', {
            'perfil': 'desativado',
            'shaders_path': os.path.join(os.path.dirname(__file__), 'shaders')
        })
        salvar_config(self.config)

    def scrapers_ativos(self):
        return {n: c for n, c in self.scrapers.items() if self.config.get(n, False)}

    async def buscar_em_todos(self, page, termo, filtro_audio=None):
        todos_resultados = []
        ativos = self.scrapers_ativos()
        
        for nome, scraper_class in ativos.items():
            try:
                res = await scraper_class.buscar_anime(page, termo)
                todos_resultados.extend(res)
            except: continue
        
        if filtro_audio:
            todos_resultados = [a for a in todos_resultados if a.get('tipo') == filtro_audio]
        
        # Remover duplicatas (melhorado para manter temporadas diferentes)
        unicos = []
        vistos = [] # Lista de tuplas (nome_normalizado, link)
        for anime in todos_resultados:
            is_dupe = False
            for v_nome, v_link in vistos:
                if animes_sao_duplicados(anime['nome'], v_nome) or anime['link'] == v_link:
                    is_dupe = True
                    break
            if not is_dupe:
                unicos.append(anime)
                vistos.append((anime['nome'], anime['link']))
        
        unicos.sort(key=lambda x: 0 if x.get('tipo') == 'DUB' else 1)
        return unicos

    async def listar_eps(self, page, anime_info):
        src = self.scrapers.get(anime_info['fonte'])
        return await src.listar_episodios(page, anime_info['link']) if src else []

    async def extrair(self, anime_info, url_ep):
        src = self.scrapers.get(anime_info['fonte'])
        return await src.extrair_video(url_ep) if src else (None, None)

    def atualizar_perfil_upscale(self, perfil: str):
        perfis = {
            'forte': {'nome': 'PC Forte (Ultra)', 'pasta': 'shaders', 'arquivos': ['Anime4K_Upscale_CNN_x2_UL.glsl', 'Anime4K_Restore_CNN_Soft_VL.glsl', 'Anime4K_AutoDownscalePre_x4.glsl']},
            'medio': {'nome': 'PC Médio (Balanced)', 'pasta': 'shaders1', 'arquivos': ['Anime4K_Upscale_CNN_x2_L.glsl', 'Anime4K_Restore_CNN_Soft_L.glsl', 'Anime4K_AutoDownscalePre_x2.glsl']},
            'fraco': {'nome': 'PC Fraco (Fast)', 'pasta': 'shaders2', 'arquivos': ['Anime4K_Upscale_CNN_x2_S.glsl', 'Anime4K_Restore_CNN_S.glsl', 'Anime4K_AutoDownscalePre_x2.glsl']},
            'desativado': {'nome': 'Desativado', 'pasta': None, 'arquivos': []}
        }
        p = perfis.get(perfil, perfis['desativado'])
        self.upscale_config = {
            'perfil': perfil,
            'shaders_path': os.path.join(os.path.dirname(__file__), p['pasta']) if p['pasta'] else None,
            'arquivos': p['arquivos']
        }
        self.config['upscale_profile'] = self.upscale_config
        salvar_config(self.config)
        return p['nome']

# ═══════════════════════════════════════════════════════════════════════════
#                              REPRODUTOR MPV
# ═══════════════════════════════════════════════════════════════════════════

class MPVController:
    def __init__(self, manager):
        self.processo = None
        self.manager = manager

    def fechar_mpv(self):
        if self.processo:
            try:
                self.processo.terminate()
                self.processo.wait(timeout=1)
            except: pass
            self.processo = None

    def reproduzir(self, link, referer, titulo, anime_nome, ep_num, fonte):
        self.fechar_mpv()
        upscale = self.manager.upscale_config
        shaders = []
        
        if upscale['perfil'] != 'desativado' and upscale.get('shaders_path'):
            for f in upscale.get('arquivos', []):
                path = os.path.join(upscale['shaders_path'], f)
                if os.path.exists(path): shaders.append(path)

        cmd = ["mpv", "--force-window=immediate", "--hwdec=auto-safe", "--vo=gpu-next", "--profile=gpu-hq", "--deband=yes"]
        if shaders: cmd.append(f"--glsl-shaders={';'.join(shaders)}")
        
        cmd.extend([f"--referrer={referer}", f"--title={titulo}", "--user-agent=Mozilla/5.0", link])

        flags = subprocess.DETACHED_PROCESS if os.name == 'nt' else 0
        try:
            self.processo = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, 
                                            start_new_session=True, creationflags=flags)
            salvar_historico_episodio(anime_nome, ep_num, fonte, None)
        except Exception as e:
            print(f"\033[1;31m[!] Erro MPV: {e}\033[0m")

# ═══════════════════════════════════════════════════════════════════════════
#                           FLUXOS DE INTERFACE (TUI)
# ═══════════════════════════════════════════════════════════════════════════

async def fluxo_busca(manager, page, mpv):
    draw_header()
    termo = input_styled("Nome do Anime")
    if not termo: return

    print(f"\n  {Style.YELLOW}Áudio:{Style.RESET} [1] Dublado  [2] Legendado  [3] Ambos")
    f_opt = input_styled("Opção")
    filtro = "DUB" if f_opt=="1" else "LEG" if f_opt=="2" else None

    print(f"\n  {Style.CYAN}⚡ Buscando em providers ativos...{Style.RESET}", end="", flush=True)
    resultados = await manager.buscar_em_todos(page, termo, filtro)

    if not resultados:
        input(f"\n  {Style.RED}✗ Nenhum resultado. [Enter]{Style.RESET}")
        return

    while True:
        draw_header()
        print(f"  {Style.GREEN}Resultados para: {Style.BOLD}{termo}{Style.RESET}\n")
        for i, anime in enumerate(resultados[:25], 1):
            tipo = f"{Style.YELLOW}[DUB]{Style.RESET}" if anime.get('tipo') == 'DUB' else f"{Style.BLUE}[LEG]{Style.RESET}"
            print(f"  {Style.MAGENTA}{i:02d}.{Style.RESET} {anime['nome'][:55]:<55} {tipo} {Style.DIM}[{anime['fonte']}]{Style.RESET}")
        
        draw_footer()
        escolha = input_styled("Escolha")
        if escolha.lower() == 'v': break
        try:
            selecionado = resultados[int(escolha)-1]
            await fluxo_episodios(selecionado, manager, page, mpv)
            break
        except: continue

async def fluxo_episodios(anime, manager, page, mpv):
    print(f"\n  {Style.CYAN}📥 Carregando episódios...{Style.RESET}")
    eps = await manager.listar_eps(page, anime)
    if not eps: 
        input(f"  {Style.RED}✗ Falha ao carregar eps. [Enter]{Style.RESET}")
        return

    while True:
        draw_header()
        print(f"  {Style.CYAN}📺 {Style.BOLD}{anime['nome']}{Style.RESET}")
        print(f"  {Style.DIM}Fonte: {anime['fonte']} • {len(eps)} episódios encontrados{Style.RESET}\n")
        
        # Grid de 2 colunas para episódios
        for i, ep in enumerate(eps[:40], 1):
            print(f"  {Style.YELLOW}{i:03d}.{Style.RESET} {ep['n'][:34]:<34}", end='\n' if i % 2 == 0 else ' ')
        
        if len(eps) > 40: print(f"\n  {Style.DIM}... e mais {len(eps)-40} episódios.{Style.RESET}")
        
        draw_footer()
        escolha = input_styled("Episódio")
        if escolha.lower() == 'v': break
        
        try:
            idx = int(escolha)-1
            url_ep = eps[idx]['u']
            print(f"\n  {Style.MAGENTA}⚡ Extraindo vídeo...{Style.RESET}")
            link, ref = await manager.extrair(anime, url_ep)
            
            if link:
                num = eps[idx].get('num', idx+1)
                mpv.reproduzir(link, ref or url_ep, f"{anime['nome']} - E{num}", anime['nome'], num, anime['fonte'])
                print(f"  {Style.GREEN}✅ Reproduzindo!{Style.RESET}")
                await asyncio.sleep(2)
            else:
                input(f"  {Style.RED}✗ Link não encontrado. [Enter]{Style.RESET}")
        except: continue

async def fluxo_historico(manager, page, mpv):
    while True:
        draw_header()
        hist = obter_historico_ordenado()
        if not hist:
            input(f"  {Style.DIM}Histórico vazio. [Enter]{Style.RESET}")
            return
        
        print(f"  {Style.GREEN}最近 CONTINUAR ASSISTINDO:{Style.RESET}\n")
        for i, h in enumerate(hist[:15], 1):
            print(f"  {Style.YELLOW}{i:02d}.{Style.RESET} {h['anime'][:45]:<45} {Style.CYAN}Ep {h['ultimo_episodio']}{Style.RESET} {Style.DIM}({h['fonte']}){Style.RESET}")
        
        draw_footer()
        escolha = input_styled("Selecionar")
        if escolha.lower() == 'v': break
        try:
            h_selecionado = hist[int(escolha)-1]
            await fluxo_episodios(h_selecionado['anime_info'], manager, page, mpv)
        except: continue

async def fluxo_config(manager):
    while True:
        draw_header()
        print(f"  {Style.YELLOW}1.{Style.RESET} Gerenciar Fontes {Style.DIM}(ON/OFF){Style.RESET}")
        print(f"  {Style.YELLOW}2.{Style.RESET} Perfil de Upscale {Style.DIM}(Anime4K){Style.RESET}")
        print(f"  {Style.YELLOW}0.{Style.RESET} Voltar")
        
        opt = input_styled("Opção")
        if opt == "0": break
        elif opt == "1":
            while True:
                draw_header()
                scrapers = list(manager.scrapers.keys())
                for i, nome in enumerate(scrapers, 1):
                    st = f"{Style.GREEN}ATIVO{Style.RESET}" if manager.config.get(nome) else f"{Style.RED}INATIVO{Style.RESET}"
                    print(f"  {Style.MAGENTA}[{i}]{Style.RESET} {nome:<20} {st}")
                draw_footer("Digite o número para alternar | 0 para sair")
                c = input_styled("Escolha")
                if c == "0": break
                try:
                    n = scrapers[int(c)-1]
                    manager.config[n] = not manager.config.get(n)
                    salvar_config(manager.config)
                except: continue
        elif opt == "2":
            draw_header()
            perfis = [('Forte (Ultra)', 'forte'), ('Médio (Equilibrado)', 'medio'), ('Fraco (Rápido)', 'fraco'), ('Desativado', 'desativado')]
            for i, (n, _) in enumerate(perfis, 1):
                print(f"  {Style.MAGENTA}[{i}]{Style.RESET} {n}")
            c = input_styled("Escolha o perfil")
            try:
                p_id = perfis[int(c)-1][1]
                nome = manager.atualizar_perfil_upscale(p_id)
                input(f"\n  {Style.GREEN}✓ Perfil {nome} ativado! [Enter]{Style.RESET}")
            except: pass

# ═══════════════════════════════════════════════════════════════════════════
#                               MAIN LOOP
# ═══════════════════════════════════════════════════════════════════════════

async def main():
    manager = ScraperManager()
    mpv = MPVController(manager)
    
    async with async_playwright() as p:
        draw_header()
        print(f"\n  {Style.CYAN}🚀 Inicializando motor Playwright...{Style.RESET}")
        
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()
        await aplicar_stealth(page)

        while True:
            draw_header()
            print(f"  {Style.YELLOW}1.{Style.RESET} 🔍 Buscar Anime")
            print(f"  {Style.YELLOW}2.{Style.RESET} 📺 Histórico / Continuar")
            print(f"  {Style.YELLOW}3.{Style.RESET} ⚙️  Configurações")
            print(f"  {Style.YELLOW}4.{Style.RESET} ❌ Sair")
            
            draw_footer("Escolha uma opção para começar")
            opcao = input_styled("Menu")

            if opcao == "4": break
            elif opcao == "1": await fluxo_busca(manager, page, mpv)
            elif opcao == "2": await fluxo_historico(manager, page, mpv)
            elif opcao == "3": await fluxo_config(manager)

        await browser.close()
        print(f"\n{Style.GREEN}  👋 Até a próxima!{Style.RESET}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Style.GREEN}  👋 Saindo...{Style.RESET}")
    except Exception as e:
        print(f"\n{Style.RED}Erro Crítico: {e}{Style.RESET}")
        input("Pressione Enter para fechar...")