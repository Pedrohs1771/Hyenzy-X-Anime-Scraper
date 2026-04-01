"""
main.py - Launcher Hyenzy-X com Discord Rich Presence
Versão compacta e funcional
"""
import os, sys, subprocess, time
from threading import Thread, Event

# ══════════════════════════════════════════════════════════════
# 🎨 CONFIGURAÇÃO COMPLETA DO DISCORD RICH PRESENCE
# ══════════════════════════════════════════════════════════════

DISCORD_APP_ID = "1459931752016380077"

# 🖼️ IMAGENS ROTATIVAS - Alternam a cada 5 segundos no menu
ROTATING_IMAGES = [
    {"name": "hyenzy", "text": "🚀 Vengeance OS"},
    {"name": "hyenzy2", "text": "💜 Powered by Pedrohs"},
]

# ⏱️ INTERVALO DE ROTAÇÃO (segundos)
ROTATION_INTERVAL = 5

# 📝 TEXTOS DO MENU
MENU_CONFIG = {
    "state": "🏠 Menu Principal",
    "details": "OS",
}

# 🎬 TEXTOS DO SISTEMA DE ANIMES
ANIME_CONFIG = {
    "state": "📺 Explorando Animes",
    "details": "Sistema de Animes",
    "large_image": "hyenzy",
    "large_text": "🔥 System Anime Ativo",
    "small_image": "anime",
    "small_text": "Animes"
}

# 🎮 TEXTOS DO SISTEMA DE JOGOS
GAMES_CONFIG = {
    "state": "🎮 Explorando Jogos",
    "details": "Sistema de Jogos",
    "large_image": "hyenzy",
    "large_text": "⚡ System Jogos Ativo",
    "small_image": "games",
    "small_text": "Games"
}

# ══════════════════════════════════════════════════════════════

# Cores
CY, GR, YL, RD, MG, RS = '\033[96m', '\033[92m', '\033[93m', '\033[91m', '\033[95m', '\033[0m'

def clear(): os.system('cls' if os.name == 'nt' else 'clear')

def header():
    clear()
    print(f"{CY}╔══════════════════════════════════════════════╗{RS}")
    print(f"{CY}║          🚀 HYENZY-X LAUNCHER 🚀           ║{RS}")
    print(f"{CY}║      Discord Rich Presence        ║{RS}")
    print(f"{CY}╚══════════════════════════════════════════════╝{RS}\n")

class DiscordRPC:
    def __init__(self):
        self.rpc = None
        self.connected = False
        self.start_time = int(time.time())
        self.current_image_index = 0
        self.rotating = False
        self.rotation_thread = None
        self.stop_event = Event()
        self.images = ROTATING_IMAGES.copy()
        
    def connect(self):
        try:
            from pypresence import Presence
            self.rpc = Presence(DISCORD_APP_ID)
            self.rpc.connect()
            self.connected = True
            return True
        except:
            return False
    
    def start_rotation(self):
        if self.rotating or not self.connected:
            return
        
        self.rotating = True
        self.stop_event.clear()
        self.rotation_thread = Thread(target=self._rotate_images, daemon=True)
        self.rotation_thread.start()
    
    def stop_rotation(self):
        self.rotating = False
        self.stop_event.set()
    
    def _rotate_images(self):
        while self.rotating and self.connected:
            if self.stop_event.wait(timeout=ROTATION_INTERVAL):
                break
            
            if not self.rotating:
                break
            
            self.current_image_index = (self.current_image_index + 1) % len(self.images)
            current_img = self.images[self.current_image_index]
            
            if self.connected and self.rotating:
                try:
                    self.rpc.update(
                        state=MENU_CONFIG["state"],
                        details=MENU_CONFIG["details"],
                        large_image=current_img["name"],
                        large_text=current_img["text"],
                        start=self.start_time
                    )
                except:
                    pass
    
    def update(self, config):
        if not self.connected or not self.rpc:
            return
        
        is_menu = config == MENU_CONFIG
        if not is_menu:
            self.stop_rotation()
        
        try:
            if is_menu:
                current_img = self.images[self.current_image_index]
                update_data = {
                    "state": config.get("state"),
                    "details": config.get("details"),
                    "large_image": current_img["name"],
                    "large_text": current_img["text"],
                    "start": self.start_time
                }
            else:
                update_data = {
                    "state": config.get("state"),
                    "details": config.get("details"),
                    "large_image": config.get("large_image", "hyenzy"),
                    "large_text": config.get("large_text"),
                    "start": self.start_time
                }
            
            if config.get("small_image") is not None:
                update_data["small_image"] = config["small_image"]
                if config.get("small_text"):
                    update_data["small_text"] = config["small_text"]
            
            self.rpc.update(**update_data)
            
            if is_menu:
                self.start_rotation()
                
        except:
            pass
    
    def close(self):
        self.stop_rotation()
        if self.connected and self.rpc:
            try: 
                self.rpc.close()
            except: 
                pass

def launch(script, title, rpc, mode):
    print(f"\n{GR}[⚡] Executando {title}...{RS}")
    
    configs = {"anime": ANIME_CONFIG, "games": GAMES_CONFIG}
    
    if mode in configs and rpc.connected:
        rpc.update(configs[mode])
        print(f"{MG}[Discord] Status: {configs[mode]['details']}{RS}")
    
    time.sleep(1)
    
    try:
        subprocess.run([sys.executable, script], check=True)
    except KeyboardInterrupt:
        print(f"\n{YL}[!] Interrompido{RS}")
    except Exception as e:
        print(f"\n{RD}[!] Erro: {e}{RS}")
    
    if rpc.connected:
        rpc.update(MENU_CONFIG)
    
    time.sleep(1.5)

def main():
    # Instala pypresence se necessário
    try:
        import pypresence
    except:
        print(f"{YL}[!] Instalando pypresence...{RS}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pypresence", "-q"])
            print(f"{GR}[✓] Instalado!{RS}\n")
            time.sleep(1)
        except:
            print(f"{RD}[!] Erro ao instalar. Continue sem RPC.{RS}")
            time.sleep(2)
    
    # Conecta Discord
    discord = DiscordRPC()
    print(f"{MG}[Discord] Conectando...{RS}")
    if discord.connect():
        print(f"{GR}[✓] Rich Presence ativo!{RS}")
        discord.update(MENU_CONFIG)
    else:
        print(f"{YL}[!] Discord não conectado (verifique o APP ID){RS}")
    time.sleep(1.5)
    
    # Muda para pasta completo
    if os.path.exists("completo"):
        os.chdir("completo")
    else:
        print(f"\n{RD}[!] Pasta 'completo' não encontrada!{RS}")
        input("Enter para sair...")
        discord.close()
        return
    
    try:
        while True:
            header()
            if discord.connected:
                print(f"{MG}[Discord] ✓ Ativo{RS}\n")
            else:
                print(f"{YL}[Discord] ✗ Inativo{RS}\n")
            
            print(f"{GR}Escolha:{RS}\n")
            print("1. 📺 Sistema de Animes")
            print("2. 🎮 Sistema de Jogos")
            print("0. 🚪 Sair\n")
            
            files = os.listdir(".")
            has_api = "api.py" in files
            has_api2 = "api2.py" in files
            
            if not has_api: print(f"{YL}[!] api.py não encontrado{RS}")
            if not has_api2: print(f"{YL}[!] api2.py não encontrado{RS}")
            
            op = input(f"\n{CY}> {RS}").strip()
            
            if op == "1" and has_api:
                launch("api.py", "Animes", discord, "anime")
            elif op == "2" and has_api2:
                launch("api2.py", "Jogos", discord, "games")
            elif op == "0":
                print(f"\n{GR}👋 Até logo!{RS}")
                break
            else:
                print(f"\n{RD}[!] Opção inválida!{RS}")
                time.sleep(1)
    finally:
        discord.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YL}[!] Encerrado{RS}")
    except Exception as e:
        print(f"\n{RD}[!] Erro: {e}{RS}")