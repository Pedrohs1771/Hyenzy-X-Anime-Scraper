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
    print(f"│   {Style.MAGENTA}🎬 HYENZY-X FILMES{Style.CYAN}                                        v1.0.0   │")
    print(f"│   {Style.DIM}Multi-Source Movie Scraper • Playwright Core{Style.RESET}{Style.CYAN}                  │")
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
    providers_path = os.path.join(os.path.dirname(__file__), 'providers-filmes')
    
    if not os.path.exists(providers_path):
        os.makedirs(providers_path)
        return []
    
    if providers_path not in sys.path:
        sys.path.insert(0, providers_path)
    
    try:
        from providers import BaseProvider
    except ImportError:
        print(f"{Style.YELLOW}[!] BaseProvider não encontrado, criando base...{Style.RESET}")
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
        
        salvar_config(self.config)

    def scrapers_ativos(self):
        return {n: c for n, c in self.scrapers.items() if self.config.get(n, False)}

    async def buscar_em_todos(self, page, termo):
        todos_resultados = []
        ativos = self.scrapers_ativos()
        
        for nome, scraper_class in ativos.items():
            try:
                # Usa buscar_filme em vez de buscar_anime
                if hasattr(scraper_class, 'buscar_filme'):
                    res = await scraper_class.buscar_filme(page, termo)
                    todos_resultados.extend(res)
            except Exception as e:
                print(f"{Style.RED}[!] Erro em {nome}: {e}{Style.RESET}")
                continue
        
        # Remover duplicatas
        unicos = []
        vistos = []
        for filme in todos_resultados:
            nome_lower = filme['nome'].lower()
            if not any(self._filmes_sao_similares(nome_lower, v) for v in vistos):
                unicos.append(filme)
                vistos.append(nome_lower)
        
        return unicos
    
    def _filmes_sao_similares(self, nome1, nome2):
        """Verifica se dois nomes de filmes são similares"""
        # Remove caracteres especiais e espaços extras
        n1 = re.sub(r'[^\w\s]', '', nome1).strip()
        n2 = re.sub(r'[^\w\s]', '', nome2).strip()
        
        # Compara diretamente ou verifica se um está contido no outro
        if n1 == n2:
            return True
        if len(n1) > len(n2) and n2 in n1:
            return True
        if len(n2) > len(n1) and n1 in n2:
            return True
        
        return False

    async def extrair(self, filme_info, url_filme):
        src = self.scrapers.get(filme_info['fonte'])
        return await src.extrair_video(url_filme) if src else (None, None)

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

    def reproduzir(self, link, referer, titulo, filme_nome, fonte):
        self.fechar_mpv()
        
        cmd = [
            "mpv",
            "--force-window=immediate",
            "--hwdec=auto-safe",
            "--vo=gpu-next",
            "--profile=gpu-hq",
            "--deband=yes",
            f"--referrer={referer}",
            f"--title={titulo}",
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            link
        ]

        flags = subprocess.DETACHED_PROCESS if os.name == 'nt' else 0
        try:
            self.processo = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                creationflags=flags
            )
            # Salva no histórico
            salvar_historico_filme(filme_nome, fonte)
        except Exception as e:
            print(f"\033[1;31m[!] Erro MPV: {e}\033[0m")

# ═══════════════════════════════════════════════════════════════════════════
#                           FLUXOS DE INTERFACE (TUI)
# ═══════════════════════════════════════════════════════════════════════════

async def fluxo_busca(manager, page, mpv):
    draw_header()
    termo = input_styled("Nome do Filme")
    if not termo: return

    print(f"\n  {Style.CYAN}⚡ Buscando em providers ativos...{Style.RESET}", end="", flush=True)
    resultados = await manager.buscar_em_todos(page, termo)

    if not resultados:
        input(f"\n  {Style.RED}✗ Nenhum resultado. [Enter]{Style.RESET}")
        return

    while True:
        draw_header()
        print(f"  {Style.GREEN}Resultados para: {Style.BOLD}{termo}{Style.RESET}\n")
        for i, filme in enumerate(resultados[:25], 1):
            print(f"  {Style.MAGENTA}{i:02d}.{Style.RESET} {filme['nome'][:60]:<60} {Style.DIM}[{filme['fonte']}]{Style.RESET}")
        
        draw_footer()
        escolha = input_styled("Escolha")
        if escolha.lower() == 'v': break
        try:
            selecionado = resultados[int(escolha)-1]
            await reproduzir_filme(selecionado, manager, page, mpv)
            break
        except: continue

async def reproduzir_filme(filme, manager, page, mpv):
    print(f"\n  {Style.MAGENTA}⚡ Extraindo vídeo de {filme['nome']}...{Style.RESET}")
    
    link, ref = await manager.extrair(filme, filme['link'])
    
    if link:
        mpv.reproduzir(link, ref or filme['link'], filme['nome'], filme['nome'], filme['fonte'])
        print(f"  {Style.GREEN}✅ Reproduzindo!{Style.RESET}")
        await asyncio.sleep(2)
    else:
        input(f"  {Style.RED}✗ Link não encontrado. [Enter]{Style.RESET}")

async def fluxo_historico(manager, page, mpv):
    while True:
        draw_header()
        hist = obter_historico_filmes()
        if not hist:
            input(f"  {Style.DIM}Histórico vazio. [Enter]{Style.RESET}")
            return
        
        print(f"  {Style.GREEN}🎬 FILMES ASSISTIDOS RECENTEMENTE:{Style.RESET}\n")
        for i, h in enumerate(hist[:15], 1):
            print(f"  {Style.YELLOW}{i:02d}.{Style.RESET} {h['filme'][:55]:<55} {Style.DIM}({h['fonte']}){Style.RESET}")
        
        draw_footer()
        escolha = input_styled("Selecionar")
        if escolha.lower() == 'v': break
        try:
            h_selecionado = hist[int(escolha)-1]
            await reproduzir_filme(h_selecionado['filme_info'], manager, page, mpv)
        except: continue

async def fluxo_config(manager):
    while True:
        draw_header()
        print(f"  {Style.YELLOW}1.{Style.RESET} Gerenciar Fontes {Style.DIM}(ON/OFF){Style.RESET}")
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

# ═══════════════════════════════════════════════════════════════════════════
#                               MAIN LOOP
# ═══════════════════════════════════════════════════════════════════════════

async def main():
    manager = ScraperManager()
    mpv = MPVController(manager)
    
    async with async_playwright() as p:
        draw_header()
        print(f"\n  {Style.CYAN}🚀 Inicializando motor Playwright...{Style.RESET}")
        
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        await aplicar_stealth(page)

        while True:
            draw_header()
            print(f"  {Style.YELLOW}1.{Style.RESET} 🔍 Buscar Filme")
            print(f"  {Style.YELLOW}2.{Style.RESET} 🎬 Histórico")
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