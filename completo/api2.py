"""
games_core.py - Sistema de busca de jogos
Auto-discovery de providers + Menu PS2 dedicado
"""
import asyncio
import os
import sys
import importlib.util
import traceback

# ===== ESTILOS =====
class C:
    CY = '\033[96m'  # Cyan
    MG = '\033[95m'  # Magenta
    GR = '\033[92m'  # Green
    YL = '\033[93m'  # Yellow
    RD = '\033[91m'  # Red
    BD = '\033[1m'   # Bold
    RS = '\033[0m'   # Reset

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def header(subtitle=""):
    clear()
    print(f"{C.CY}{C.BD}╔══════════════════════════════════════════════╗{C.RS}")
    print(f"{C.CY}{C.BD}║          🎮 HYENZY-X GAMES 🎮              ║{C.RS}")
    if subtitle:
        print(f"{C.CY}{C.BD}║  {subtitle:^40}  ║{C.RS}")
    print(f"{C.CY}{C.BD}╚══════════════════════════════════════════════╝{C.RS}\n")


# ===== GERENCIADOR DE PROVIDERS =====
class GameManager:
    def __init__(self):
        self.providers = {}
        self.ps2_provider = None
        self.providers_path = "providers-games"
        self._load_providers()
    
    def _load_providers(self):
        """Carrega providers da pasta"""
        print(f"\n{C.CY}[*] Carregando providers...{C.RS}")
        
        # Cria pasta se não existir
        if not os.path.exists(self.providers_path):
            os.makedirs(self.providers_path)
            print(f"{C.YL}[!] Pasta {self.providers_path} criada{C.RS}")
            self._create_example()
            return
        
        # Adiciona ao path do Python
        abs_path = os.path.abspath(self.providers_path)
        if abs_path not in sys.path:
            sys.path.insert(0, abs_path)
        
        # Lista arquivos
        files = [f for f in os.listdir(self.providers_path) if f.endswith('.py')]
        
        if not files:
            print(f"{C.YL}[!] Nenhum arquivo .py encontrado{C.RS}")
            self._create_example()
            return
        
        print(f"{C.CY}[*] Arquivos encontrados: {files}{C.RS}")
        
        # Carrega cada arquivo
        for filename in files:
            if filename.startswith('_'):
                continue
            
            module_name = filename[:-3]
            filepath = os.path.join(self.providers_path, filename)
            
            print(f"\n{C.CY}[*] Carregando {filename}...{C.RS}")
            
            try:
                # Importa o módulo
                spec = importlib.util.spec_from_file_location(module_name, filepath)
                if not spec or not spec.loader:
                    print(f"{C.RD}[!] Spec inválido para {filename}{C.RS}")
                    continue
                
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                print(f"{C.GR}[✓] Módulo {module_name} importado{C.RS}")
                
                # Busca classes de provider
                found = False
                for attr_name in dir(module):
                    if attr_name.startswith('_'):
                        continue
                    
                    try:
                        attr = getattr(module, attr_name)
                        
                        # Verifica se é uma classe válida
                        if not isinstance(attr, type):
                            continue
                        
                        # Verifica atributos necessários
                        has_name = hasattr(attr, 'NAME')
                        has_search = hasattr(attr, 'search')
                        has_extract = hasattr(attr, 'extract_downloads')
                        
                        if not (has_name and has_search and has_extract):
                            continue
                        
                        # Verifica se está ativo
                        is_active = getattr(attr, 'ACTIVE', True)
                        if not is_active:
                            print(f"{C.YL}[!] {attr.NAME} está inativo{C.RS}")
                            continue
                        
                        # Adiciona provider
                        provider_name = attr.NAME
                        
                        # Separa PS2 dos demais
                        if 'PS2' in provider_name.upper():
                            self.ps2_provider = attr
                            print(f"{C.GR}[✓] Provider PS2 '{provider_name}' carregado (menu dedicado)!{C.RS}")
                        else:
                            self.providers[provider_name] = attr
                            print(f"{C.GR}[✓] Provider '{provider_name}' carregado!{C.RS}")
                        
                        found = True
                        
                    except Exception as e:
                        print(f"{C.RD}[!] Erro ao processar {attr_name}: {e}{C.RS}")
                        continue
                
                if not found:
                    print(f"{C.YL}[!] Nenhum provider válido em {filename}{C.RS}")
                
            except Exception as e:
                print(f"{C.RD}[!] Erro ao carregar {filename}:{C.RS}")
                print(f"{C.RD}    {e}{C.RS}")
                traceback.print_exc()
        
        # Resumo
        print(f"\n{C.BD}{'='*50}{C.RS}")
        if self.providers or self.ps2_provider:
            if self.providers:
                print(f"{C.GR}[✓] {len(self.providers)} provider(s) geral carregado(s):{C.RS}")
                for name in self.providers.keys():
                    print(f"    • {name}")
            if self.ps2_provider:
                print(f"{C.MG}[✓] Provider PS2: {self.ps2_provider.NAME}{C.RS}")
        else:
            print(f"{C.RD}[!] NENHUM provider carregado!{C.RS}")
        print(f"{C.BD}{'='*50}{C.RS}\n")
    
    def _create_example(self):
        """Cria provider de exemplo"""
        code = '''"""
example.py - Provider de exemplo
Renomeie ou crie seu próprio provider baseado neste
"""

class ExampleProvider:
    NAME = "Example"
    ACTIVE = True
    
    @classmethod
    async def search(cls, query):
        """Busca jogos - retorna lista de dicts com 'title' e 'url'"""
        return [
            {'title': f'{query} - Game Demo 1', 'url': 'https://example.com/game1'},
            {'title': f'{query} - Game Demo 2', 'url': 'https://example.com/game2'},
        ]
    
    @classmethod
    async def extract_downloads(cls, url):
        """Extrai downloads - retorna lista de dicts com 'name', 'url', 'server'"""
        return [
            {'name': 'Download Link 1', 'url': url, 'server': 'Example Server'},
            {'name': 'Download Link 2', 'url': url, 'server': 'Mirror'},
        ]
'''
        
        example_path = os.path.join(self.providers_path, "example.py")
        with open(example_path, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"{C.GR}[✓] Exemplo criado em {example_path}{C.RS}")
    
    async def search(self, query):
        """Busca em todos os providers (exceto PS2)"""
        if not self.providers:
            print(f"{C.RD}[!] Nenhum provider disponível{C.RS}")
            return []
        
        print(f"{C.CY}[*] Buscando em {len(self.providers)} provider(s)...{C.RS}")
        
        # Executa buscas em paralelo
        tasks = []
        for name, provider in self.providers.items():
            task = self._search_provider(name, provider, query)
            tasks.append(task)
        
        # Aguarda resultados
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Processa resultados
        results = []
        for result in all_results:
            if isinstance(result, list):
                results.extend(result)
            elif isinstance(result, Exception):
                print(f"{C.RD}[!] Erro: {result}{C.RS}")
        
        print(f"{C.CY}[*] Total de resultados: {len(results)}{C.RS}")
        
        # Calcula scores
        for r in results:
            r['score'] = self._calc_score(r.get('title', ''), query)
        
        # Ordena por score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results[:20]
    
    async def search_ps2(self, query):
        """Busca APENAS no provider PS2"""
        if not self.ps2_provider:
            print(f"{C.RD}[!] Provider PS2 não disponível{C.RS}")
            return []
        
        print(f"{C.CY}[*] Buscando no João13 Traduções...{C.RS}")
        
        try:
            results = await self.ps2_provider.search(query)
            
            if not results:
                print(f"{C.YL}[!] Nenhum resultado encontrado{C.RS}")
                return []
            
            print(f"{C.GR}[✓] {len(results)} resultado(s) encontrado(s){C.RS}")
            
            # Adiciona provider info
            for item in results:
                item['provider'] = self.ps2_provider.NAME
                item['score'] = self._calc_score(item.get('title', ''), query)
            
            # Ordena por score
            results.sort(key=lambda x: x['score'], reverse=True)
            
            return results[:20]
            
        except Exception as e:
            print(f"{C.RD}[!] Erro na busca PS2: {e}{C.RS}")
            traceback.print_exc()
            return []
    
    async def _search_provider(self, name, provider, query):
        """Busca em um provider específico"""
        try:
            print(f"{C.YL}[{name}] Iniciando busca...{C.RS}")
            items = await provider.search(query)
            
            if not items:
                print(f"{C.YL}[{name}] Nenhum resultado{C.RS}")
                return []
            
            print(f"{C.GR}[{name}] {len(items)} resultado(s){C.RS}")
            
            # Adiciona provider info
            for item in items:
                item['provider'] = name
            
            return items
            
        except Exception as e:
            print(f"{C.RD}[{name}] ERRO: {e}{C.RS}")
            traceback.print_exc()
            return []
    
    def _calc_score(self, title, query):
        """Calcula score de relevância"""
        if not title:
            return 0
        
        title_l = title.lower()
        query_l = query.lower()
        score = 0
        
        # Match exato
        if query_l in title_l:
            score += 100
        
        # Palavras individuais
        words = [w for w in query.split() if len(w) > 2]
        for word in words:
            word_l = word.lower()
            if word_l in title_l:
                score += 20
                if title_l.startswith(word_l):
                    score += 10
        
        return max(0, score)
    
    async def get_downloads(self, game):
        """Obtém downloads de um jogo"""
        provider_name = game.get('provider')
        
        # Verifica se é PS2
        if self.ps2_provider and provider_name == self.ps2_provider.NAME:
            provider = self.ps2_provider
        else:
            provider = self.providers.get(provider_name)
        
        if not provider:
            print(f"{C.RD}[!] Provider '{provider_name}' não encontrado{C.RS}")
            return []
        
        try:
            print(f"{C.CY}[{provider_name}] Extraindo downloads...{C.RS}")
            downloads = await provider.extract_downloads(game['url'])
            print(f"{C.GR}[{provider_name}] {len(downloads)} download(s) encontrado(s){C.RS}")
            return downloads
            
        except Exception as e:
            print(f"{C.RD}[{provider_name}] Erro: {e}{C.RS}")
            traceback.print_exc()
            return []


# ===== INTERFACE =====
async def search_menu(manager):
    """Menu de busca geral"""
    header("Buscar Jogos (Geral)")
    
    query = input(f"{C.MG}🔍 Nome do jogo: {C.RS}").strip()
    if not query:
        return
    
    print(f"\n{C.YL}[⚡] Buscando '{query}'...{C.RS}\n")
    results = await manager.search(query)
    
    if not results:
        input(f"\n{C.RD}[✗] Nenhum resultado encontrado{C.RS}\n{C.YL}Pressione Enter...{C.RS}")
        return
    
    # Mostra resultados
    header(f"Resultados: {query}")
    
    for i, game in enumerate(results, 1):
        title = game['title'][:45]
        provider = game.get('provider', '?')
        score = game.get('score', 0)
        
        print(f"{C.MG}{i:2}.{C.RS} {title:<45} {C.YL}[{provider}]{C.RS} ★{score}")
    
    # Seleção
    print()
    try:
        choice = input(f"{C.MG}Escolha (1-{len(results)} ou Enter para voltar): {C.RS}").strip()
        if not choice:
            return
        
        idx = int(choice) - 1
        if 0 <= idx < len(results):
            await download_menu(manager, results[idx])
    except ValueError:
        pass

async def search_ps2_menu(manager):
    """Menu de busca PS2 dedicado"""
    header("Buscar Jogos PS2 - João13 Traduções")
    
    if not manager.ps2_provider:
        print(f"{C.RD}[!] Provider PS2 não está carregado!{C.RS}")
        print(f"{C.YL}[!] Certifique-se que ps2.py está em providers-games/{C.RS}\n")
        input(f"{C.YL}Pressione Enter...{C.RS}")
        return
    
    query = input(f"{C.MG}🔍 Nome do jogo PS2: {C.RS}").strip()
    if not query:
        return
    
    print(f"\n{C.YL}[⚡] Buscando '{query}' no João13...{C.RS}\n")
    results = await manager.search_ps2(query)
    
    if not results:
        input(f"\n{C.RD}[✗] Nenhum jogo PS2 encontrado{C.RS}\n{C.YL}Pressione Enter...{C.RS}")
        return
    
    # Mostra resultados
    header(f"Jogos PS2 Encontrados: {query}")
    
    for i, game in enumerate(results, 1):
        title = game['title'][:60]
        score = game.get('score', 0)
        
        print(f"{C.MG}{i:2}.{C.RS} {title:<60} ★{score}")
    
    # Seleção
    print()
    try:
        choice = input(f"{C.MG}Escolha (1-{len(results)} ou Enter para voltar): {C.RS}").strip()
        if not choice:
            return
        
        idx = int(choice) - 1
        if 0 <= idx < len(results):
            await download_menu_ps2(manager, results[idx])
    except ValueError:
        pass

async def download_menu(manager, game):
    """Menu de downloads (geral)"""
    header("Downloads")
    
    print(f"{C.CY}📦 {game['title']}{C.RS}")
    print(f"{C.YL}Provider: {game.get('provider', '?')}{C.RS}\n")
    
    downloads = await manager.get_downloads(game)
    
    if not downloads:
        input(f"\n{C.RD}[✗] Nenhum download encontrado{C.RS}\n{C.YL}Pressione Enter...{C.RS}")
        return
    
    # Mostra downloads
    header("Downloads Disponíveis")
    print(f"{C.CY}{game['title']}{C.RS}\n")
    
    for i, dl in enumerate(downloads, 1):
        name = dl.get('name', 'Download')[:40]
        server = dl.get('server', 'Unknown')
        print(f"{C.MG}{i:2}.{C.RS} {name:<40} {C.YL}[{server}]{C.RS}")
    
    # Seleção
    print()
    try:
        choice = input(f"{C.MG}Escolha (ou Enter para voltar): {C.RS}").strip()
        if not choice:
            return
        
        idx = int(choice) - 1
        if 0 <= idx < len(downloads):
            show_download(downloads[idx], game)
    except ValueError:
        pass

async def download_menu_ps2(manager, game):
    """Menu de downloads PS2 com auto-download"""
    header("Downloads PS2")
    
    print(f"{C.CY}📦 {game['title']}{C.RS}")
    print(f"{C.YL}Provider: João13 Traduções{C.RS}\n")
    
    downloads = await manager.get_downloads(game)
    
    if not downloads:
        input(f"\n{C.RD}[✗] Nenhum download encontrado{C.RS}\n{C.YL}Pressione Enter...{C.RS}")
        return
    
    # Mostra downloads
    header("Downloads PS2 Disponíveis")
    print(f"{C.CY}{game['title']}{C.RS}\n")
    
    for i, dl in enumerate(downloads, 1):
        name = dl.get('name', 'Download')[:50]
        server = dl.get('server', 'Unknown')
        print(f"{C.MG}{i:2}.{C.RS} {name:<50} {C.YL}[{server}]{C.RS}")
    
    # Seleção com opção de auto-download
    print()
    print(f"{C.GR}[PS2] Download automático disponível!{C.RS}")
    print(f"{C.YL}Digite o número + 'D' para baixar e extrair automaticamente{C.RS}")
    print(f"{C.YL}Exemplo: 1D para auto-download da opção 1{C.RS}\n")
    
    try:
        choice = input(f"{C.MG}Escolha (ou Enter para voltar): {C.RS}").strip().upper()
        if not choice:
            return
        
        # Verifica se quer auto-download
        auto_download = choice.endswith('D')
        if auto_download:
            choice = choice[:-1]
        
        idx = int(choice) - 1
        if 0 <= idx < len(downloads):
            if auto_download:
                await auto_download_ps2(downloads[idx], game)
            else:
                show_download(downloads[idx], game)
    except ValueError:
        pass

async def auto_download_ps2(download, game):
    """Download automático de jogos PS2"""
    header("Download Automático PS2")
    
    print(f"{C.CY}🎮 {game['title']}{C.RS}")
    print(f"{C.YL}🌐 {download.get('server', 'Unknown')}{C.RS}")
    print(f"{C.MG}🔗 {download['url']}{C.RS}\n")
    
    confirm = input(f"{C.YL}Confirmar download e extração? (S/N): {C.RS}").strip().upper()
    
    if confirm != 'S':
        print(f"{C.YL}[!] Cancelado{C.RS}")
        input(f"{C.YL}Pressione Enter...{C.RS}")
        return
    
    # Tenta importar downloader
    try:
        from ps2_downloader import download_ps2_game
        
        print(f"\n{C.GR}[*] Iniciando download automático...{C.RS}\n")
        success = await download_ps2_game(download, game)
        
        if success:
            print(f"\n{C.GR}{'='*60}{C.RS}")
            print(f"{C.GR}[✓] SUCESSO! Jogo baixado e extraído!{C.RS}")
            print(f"{C.GR}{'='*60}{C.RS}\n")
        else:
            print(f"\n{C.RD}[✗] Falha no processo{C.RS}\n")
        
    except ImportError:
        print(f"\n{C.RD}[!] Módulo ps2_downloader.py não encontrado!{C.RS}")
        print(f"{C.YL}[!] Coloque ps2_downloader.py na mesma pasta{C.RS}\n")
    except Exception as e:
        print(f"\n{C.RD}[!] Erro: {e}{C.RS}\n")
        traceback.print_exc()
    
    input(f"\n{C.YL}Pressione Enter para voltar...{C.RS}")

def show_download(download, game):
    """Mostra link selecionado"""
    header("Link Selecionado")
    
    print(f"{C.CY}🎮 {game['title']}{C.RS}")
    print(f"{C.YL}🌐 {download.get('server', 'Unknown')}{C.RS}\n")
    print(f"{C.MG}🔗 {download['url']}{C.RS}\n")
    
    # Tenta copiar para clipboard
    try:
        import pyperclip
        pyperclip.copy(download['url'])
        print(f"{C.GR}[✓] Link copiado para clipboard!{C.RS}\n")
    except:
        print(f"{C.YL}[i] Instale pyperclip para copiar automaticamente{C.RS}\n")
    
    input(f"{C.YL}Pressione Enter para voltar...{C.RS}")


# ===== MAIN =====
async def main():
    """Loop principal"""
    print(f"{C.CY}[*] Iniciando Game Manager...{C.RS}")
    manager = GameManager()
    
    while True:
        header()
        print(f"{C.YL}1.{C.RS} 🔍 Buscar jogo (Geral)")
        print(f"{C.YL}2.{C.RS} 🎮 Buscar jogos PS2 (João13 PT-BR)")
        print(f"{C.YL}3.{C.RS} 🔙 Sair")
        
        # Status dos providers
        print(f"\n{C.BD}{'─'*46}{C.RS}")
        if manager.providers:
            print(f"{C.CY}Providers gerais: {', '.join(manager.providers.keys())}{C.RS}")
        else:
            print(f"{C.YL}Providers gerais: Nenhum{C.RS}")
        
        if manager.ps2_provider:
            print(f"{C.MG}Provider PS2: {manager.ps2_provider.NAME}{C.RS}")
            # Verifica se downloader está disponível
            try:
                import ps2_downloader
                print(f"{C.GR}PS2 Auto-Download: ✓ Ativo{C.RS}")
            except:
                print(f"{C.YL}PS2 Auto-Download: ✗ Inativo (ps2_downloader.py não encontrado){C.RS}")
        else:
            print(f"{C.RD}Provider PS2: ✗ Não carregado{C.RS}")
        
        print(f"{C.BD}{'─'*46}{C.RS}")
        
        op = input(f"\n{C.MG}❯ {C.RS}").strip()
        
        if op == "1":
            if not manager.providers:
                print(f"\n{C.RD}[!] Nenhum provider geral disponível{C.RS}")
                input(f"{C.YL}Pressione Enter...{C.RS}")
            else:
                await search_menu(manager)
        elif op == "2":
            await search_ps2_menu(manager)
        elif op == "3":
            return "exit"

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        if result == "exit":
            print(f"\n{C.GR}[✓] Até logo!{C.RS}")
    except KeyboardInterrupt:
        print(f"\n{C.YL}[!] Cancelado pelo usuário{C.RS}")
    except Exception as e:
        print(f"\n{C.RD}[!] Erro crítico: {e}{C.RS}")
        traceback.print_exc()
        input("\nPressione Enter para sair...")