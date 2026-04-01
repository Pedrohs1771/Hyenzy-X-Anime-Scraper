import pyautogui
import time
import re
import keyboard
import requests
from mido import MidiFile, tempo2bpm
import os

class RobloxPianoPlayer:
    def __init__(self, use_keyboard_lib=True):
        self.use_keyboard_lib = use_keyboard_lib
        pyautogui.PAUSE = 0.01
        pyautogui.FAILSAFE = True
        
        # Mapeamento MIDI -> Virtual Piano
        self.midi_to_note = {
            24: 'C1', 25: 'C#1', 26: 'D1', 27: 'D#1', 28: 'E1',
            29: 'F1', 30: 'F#1', 31: 'G1', 32: 'G#1', 33: 'A1', 34: 'A#1', 35: 'B1',
            36: 'C2', 37: 'C#2', 38: 'D2', 39: 'D#2', 40: 'E2',
            41: 'F2', 42: 'F#2', 43: 'G2', 44: 'G#2', 45: 'A2', 46: 'A#2', 47: 'B2',
            48: 'C3', 49: 'C#3', 50: 'D3', 51: 'D#3', 52: 'E3',
            53: 'F3', 54: 'F#3', 55: 'G3', 56: 'G#3', 57: 'A3', 58: 'A#3', 59: 'B3',
            60: 'C4', 61: 'C#4', 62: 'D4', 63: 'D#4', 64: 'E4',
            65: 'F4', 66: 'F#4', 67: 'G4', 68: 'G#4', 69: 'A4', 70: 'A#4', 71: 'B4',
            72: 'C5', 73: 'C#5', 74: 'D5', 75: 'D#5', 76: 'E5',
            77: 'F5', 78: 'F#5', 79: 'G5', 80: 'G#5', 81: 'A5', 82: 'A#5', 83: 'B5',
            84: 'C6',
        }
        
        # Mapeamento completo Virtual Piano
        self.note_mapping = {
            'C1': '1', 'C#1': '!', 'D1': '2', 'D#1': '@', 'E1': '3',
            'F1': '4', 'F#1': '$', 'G1': '5', 'G#1': '%', 'A1': '6', 'A#1': '^', 'B1': '7',
            
            'C2': '8', 'C#2': '*', 'D2': '9', 'D#2': '(', 'E2': '0',
            'F2': 'q', 'F#2': 'Q', 'G2': 'w', 'G#2': 'W', 'A2': 'e', 'A#2': 'E', 'B2': 'r',
            
            'C3': 't', 'C#3': 'T', 'D3': 'y', 'D#3': 'Y', 'E3': 'u',
            'F3': 'i', 'F#3': 'I', 'G3': 'o', 'G#3': 'O', 'A3': 'p', 'A#3': 'P', 'B3': 'a',
            
            'C4': 's', 'C#4': 'S', 'D4': 'd', 'D#4': 'D', 'E4': 'f',
            'F4': 'g', 'F#4': 'G', 'G4': 'h', 'G#4': 'H', 'A4': 'j', 'A#4': 'J', 'B4': 'k',
            
            'C5': 'l', 'C#5': 'L', 'D5': 'z', 'D#5': 'Z', 'E5': 'x',
            'F5': 'c', 'F#5': 'C', 'G5': 'v', 'G#5': 'V', 'A5': 'b', 'A#5': 'B', 'B5': 'n',
            
            'C6': 'm',
        }
        
        # Mapeamento reverso: tecla -> nota
        self.key_to_note = {
            # Oitava 3 (teclas TYUIOPA)
            't': 'C3', 'T': 'C#3',
            'y': 'D3', 'Y': 'D#3',
            'u': 'E3',
            'i': 'F3', 'I': 'F#3',
            'o': 'G3', 'O': 'G#3',
            'p': 'A3', 'P': 'A#3',
            'a': 'B3',
            
            # Oitava 4 (teclas SDFGHJK)
            's': 'C4', 'S': 'C#4',
            'd': 'D4', 'D': 'D#4',
            'f': 'E4',
            'g': 'F4', 'G': 'F#4',
            'h': 'G4', 'H': 'G#4',
            'j': 'A4', 'J': 'A#4',
            'k': 'B4',
            
            # Oitava 5 (teclas LZXCVBN)
            'l': 'C5', 'L': 'C#5',
            'z': 'D5', 'Z': 'D#5',
            'x': 'E5',
            'c': 'F5', 'C': 'F#5',
            'v': 'G5', 'V': 'G#5',
            'b': 'A5', 'B': 'A#5',
            'n': 'B5',
            'm': 'C6',
        }
        
        self.base_delay = 0.25
        self.chord_delay = 0.05
        self.bar_delay = 0.5
    
    def search_virtualpiano_sheets(self, query):
        """Busca partituras no banco local"""
        print(f"🔍 Buscando '{query}' no banco de partituras...")
        
        # FORMATO CORRETO: usando notação com números (C3, D3, etc)
        local_sheets = {
            'bleach': {
                'name': 'Bleach - Number One',
                'sheet': 'BPM:140 A3 A3 A3 G3 A3 A3 G3 F3 A3 | A3 A3 A3 G3 A3 A3 G3 F3 A3'
            },
            'naruto': {
                'name': 'Naruto - Sadness and Sorrow',
                'sheet': 'BPM:80 B3 A3 G3 A3 B3 A3 G3 | B3 A3 G3 A3 B3 A3 F3 | E3 F3 G3 A3 G3 F3 E3'
            },
            'attack on titan': {
                'name': 'Attack on Titan - Guren no Yumiya',
                'sheet': 'BPM:160 F3 F3 F3 G3 A3 B3 | F3 F3 F3 G3 A3 B3 | G3 G3 G3 A3 B3 C4'
            },
            'demon slayer': {
                'name': 'Demon Slayer - Gurenge',
                'sheet': 'BPM:135 B3 C4 D4 E4 F4 G4 A4 | B3 C4 D4 E4 F4 G4 A4 | A4 G4 F4 D4 C4 B3 A3'
            },
            'one piece': {
                'name': 'One Piece - We Are',
                'sheet': 'BPM:130 D4 D4 C4 B3 A3 G3 F3 E3 | D3 E3 F3 G3 A3 B3 C4 D4'
            },
            'tokyo ghoul': {
                'name': 'Tokyo Ghoul - Unravel',
                'sheet': 'BPM:145 C4 C4 C4 D4 E4 D4 C4 B3 | A3 A3 A3 B3 C4 B3 A3 G3'
            },
            'your name': {
                'name': 'Your Name - Sparkle',
                'sheet': 'BPM:125 E4 E4 E4 F4 G4 A4 G4 F4 | E4 E4 E4 F4 G4 A4 G4 F4'
            },
            'jujutsu kaisen': {
                'name': 'Jujutsu Kaisen - SPECIALZ',
                'sheet': 'BPM:150 A4 G4 F4 E4 D4 C4 B3 | A4 G4 F4 E4 D4 C4 B3'
            },
            'giorno theme': {
                'name': 'JoJo - Giorno Theme',
                'sheet': 'BPM:120 F3 F3 F3 F3 E3 F3 G3 | F3 F3 F3 F3 E3 D3 C3'
            },
            'minecraft': {
                'name': 'Minecraft - Sweden',
                'sheet': 'BPM:100 E3 G3 A3 C4 A3 E3 | D3 E3 G3 A3 G3 E3 D3'
            },
        }
        
        query_lower = query.lower()
        for key, value in local_sheets.items():
            if key in query_lower or query_lower in key:
                print(f"✅ Encontrado: {value['name']}")
                return value['sheet']
        
        print(f"⚠️  Partitura não encontrada no banco local")
        return None
    
    def download_midi(self, query):
        """Baixa MIDI de fontes online"""
        print(f"🎵 Tentando baixar MIDI de '{query}'...")
        
        try:
            # Tenta BitMidi API
            url = f"https://bitmidi.com/api/search?q={query.replace(' ', '+')}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    midi_url = f"https://bitmidi.com{data[0]['url']}"
                    
                    midi_response = requests.get(midi_url, timeout=10)
                    filename = f"temp_{query.replace(' ', '_')}.mid"
                    
                    with open(filename, 'wb') as f:
                        f.write(midi_response.content)
                    
                    print(f"✅ MIDI baixado: {filename}")
                    return filename
        except Exception as e:
            print(f"⚠️  Erro: {e}")
        
        return None
    
    def midi_to_sheet(self, midi_file, max_notes=300):
        """Converte MIDI para partitura"""
        print(f"🎼 Convertendo MIDI...")
        
        try:
            mid = MidiFile(midi_file)
            notes = []
            current_time = 0
            tempo = 500000
            
            for track in mid.tracks:
                for msg in track:
                    current_time += msg.time
                    
                    if msg.type == 'set_tempo':
                        tempo = msg.tempo
                    
                    if msg.type == 'note_on' and msg.velocity > 0:
                        if msg.note in self.midi_to_note:
                            note_name = self.midi_to_note[msg.note]
                            time_seconds = current_time / mid.ticks_per_beat * (tempo / 1000000)
                            notes.append((time_seconds, note_name))
            
            notes.sort(key=lambda x: x[0])
            
            if len(notes) > max_notes:
                print(f"⚠️  Limitando a {max_notes} notas")
                notes = notes[:max_notes]
            
            bpm = tempo2bpm(tempo)
            sheet = f"BPM:{int(bpm)} "
            
            last_time = 0
            for time_sec, note in notes:
                delay = time_sec - last_time
                
                if delay > 0.8:
                    sheet += "| "
                
                sheet += f"{note} "
                last_time = time_sec
            
            print(f"✅ {len(notes)} notas convertidas, BPM {int(bpm)}")
            return sheet.strip()
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            return None
    
    def get_music_sheet(self, query):
        """Busca música"""
        print(f"\n{'='*60}")
        print(f"🎵 BUSCANDO: {query}")
        print(f"{'='*60}\n")
        
        # 1. Banco local
        sheet = self.search_virtualpiano_sheets(query)
        if sheet:
            return sheet
        
        # 2. Download MIDI
        print("\n📥 Tentando baixar MIDI...")
        midi_file = self.download_midi(query)
        
        if midi_file and os.path.exists(midi_file):
            sheet = self.midi_to_sheet(midi_file)
            try:
                os.remove(midi_file)
            except:
                pass
            if sheet:
                return sheet
        
        # 3. Manual
        print("\n❌ Não encontrado automaticamente")
        print("\n📝 Você pode:")
        print("1. Inserir partitura manual")
        print("2. Colar de virtualpiano.net")
        print("3. Cancelar")
        
        choice = input("\n➤ (1-3): ").strip()
        
        if choice in ['1', '2']:
            print("\n📋 Cole a partitura:")
            sheet = input("➤ ")
            return sheet if sheet.strip() else None
        
        return None
    
    def parse_sheet(self, sheet_music):
        """Parser CORRIGIDO com debug"""
        commands = []
        sheet_music = ' '.join(sheet_music.split())
        
        print(f"\n🔍 DEBUG: Partitura original = '{sheet_music[:100]}...'")
        
        # Regex para capturar tudo
        pattern = r'\[([A-Gb#0-9\s]+)\]|BPM:(\d+)|\||([A-G][#b]?\d)(?:-(\d+))?'
        matches = list(re.finditer(pattern, sheet_music))
        
        print(f"🔍 DEBUG: Encontradas {len(matches)} correspondências")
        
        for match in matches:
            if match.group(1):  # Acorde
                notes = re.findall(r'[A-G][#b]?\d', match.group(1))
                if notes:
                    commands.append(('chord', notes))
                    print(f"  ♫ Acorde: {notes}")
                    
            elif match.group(2):  # BPM
                bpm = int(match.group(2))
                self.base_delay = 60.0 / bpm / 2
                print(f"  🎼 BPM: {bpm} (delay={self.base_delay:.3f}s)")
                continue
                
            elif match.group(0) == '|':  # Pausa
                commands.append(('pause', self.bar_delay))
                print(f"  ⏸️  Pausa")
                
            elif match.group(3):  # Nota
                note = match.group(3)
                delay = float(match.group(4)) / 1000 if match.group(4) else self.base_delay
                commands.append(('note', note, delay))
                print(f"  🎹 {note} → {self.note_mapping.get(note)} (delay={delay:.3f}s)")
        
        print(f"\n✅ Total de comandos: {len(commands)}\n")
        return commands
    
    def play_note(self, note):
        """Toca nota"""
        key = self.note_mapping.get(note)
        if not key:
            print(f"⚠️  Nota inválida: {note}")
            return
        
        needs_shift = key.isupper() or key in '!@$%^*()'
        actual_key = key.lower() if key.isalpha() else key
        
        try:
            if self.use_keyboard_lib:
                if needs_shift:
                    keyboard.press('shift')
                    time.sleep(0.01)
                keyboard.press(actual_key)
                time.sleep(0.03)
                keyboard.release(actual_key)
                if needs_shift:
                    keyboard.release('shift')
            else:
                if needs_shift:
                    pyautogui.hotkey('shift', actual_key)
                else:
                    pyautogui.press(actual_key)
        except Exception as e:
            print(f"❌ Erro ao tocar {note}: {e}")
    
    def play_chord(self, notes):
        """Toca acorde"""
        keys_info = []
        
        for note in notes:
            key = self.note_mapping.get(note)
            if key:
                needs_shift = key.isupper() or key in '!@$%^*()'
                actual_key = key.lower() if key.isalpha() else key
                keys_info.append((actual_key, needs_shift))
        
        try:
            if self.use_keyboard_lib:
                for actual_key, needs_shift in keys_info:
                    if needs_shift:
                        keyboard.press('shift')
                    keyboard.press(actual_key)
                    time.sleep(0.01)
                
                time.sleep(self.chord_delay)
                
                for actual_key, needs_shift in reversed(keys_info):
                    keyboard.release(actual_key)
                    if needs_shift:
                        keyboard.release('shift')
            else:
                for actual_key, needs_shift in keys_info:
                    if needs_shift:
                        pyautogui.keyDown('shift')
                    pyautogui.keyDown(actual_key)
                
                time.sleep(self.chord_delay)
                
                for actual_key, needs_shift in reversed(keys_info):
                    pyautogui.keyUp(actual_key)
                    if needs_shift:
                        pyautogui.keyUp('shift')
        except Exception as e:
            print(f"❌ Erro no acorde: {e}")
    
    def play(self, sheet_music, delay_before_start=5, show_keys=True):
        """Toca música com PROGRESSO VISUAL"""
        print(f"\n{'='*60}")
        print(f"🎵 MODO: {'KEYBOARD (Recomendado)' if self.use_keyboard_lib else 'PYAUTOGUI'}")
        print(f"{'='*60}")
        print(f"\n⚡ PREPARAÇÃO:")
        print(f"   1. Abra Roblox em MODO JANELA")
        print(f"   2. Clique NO PIANO VIRTUAL do jogo")
        print(f"   3. NÃO mova o mouse depois")
        print(f"\n⏰ Iniciando em {delay_before_start} segundos...\n")
        
        for i in range(delay_before_start, 0, -1):
            print(f"{'🔴' if i <= 3 else '🟡'} {i}...")
            time.sleep(1)
        
        print("\n🎹 TOCANDO AGORA!\n")
        
        commands = self.parse_sheet(sheet_music)
        
        if not commands:
            print("❌ ERRO: Nenhum comando foi gerado!")
            print(f"Partitura: {sheet_music[:200]}")
            return
        
        total = len(commands)
        
        for i, command in enumerate(commands, 1):
            cmd_type = command[0]
            
            try:
                if cmd_type == 'note':
                    _, note, delay = command
                    if show_keys:
                        key = self.note_mapping.get(note)
                        print(f"[{i}/{total}] 🎹 {note} → tecla '{key}'", flush=True)
                    self.play_note(note)
                    time.sleep(delay)
                    
                elif cmd_type == 'chord':
                    _, notes = command
                    if show_keys:
                        print(f"[{i}/{total}] 🎵 Acorde: {notes}", flush=True)
                    self.play_chord(notes)
                    time.sleep(self.base_delay)
                    
                elif cmd_type == 'pause':
                    _, delay = command
                    if show_keys:
                        print(f"[{i}/{total}] ⏸️  Pausa: {delay:.2f}s", flush=True)
                    time.sleep(delay)
                    
            except KeyboardInterrupt:
                print("\n\n⛔ INTERROMPIDO!")
                break
            except Exception as e:
                print(f"\n❌ Erro no comando {i}: {e}")
                continue
        
        print(f"\n{'='*60}")
        print("✅ MÚSICA CONCLUÍDA!")
        print(f"{'='*60}\n")


def main():
    print("=" * 60)
    print("🎹 ROBLOX AUTO PIANO - VERSÃO COMPLETA V2")
    print("=" * 60)
    
    # Setup
    try:
        import keyboard
        use_kb = True
        print("✅ Biblioteca 'keyboard' ativa (MELHOR)")
    except:
        print("📦 Instalando 'keyboard'...")
        os.system("pip install keyboard")
        try:
            import keyboard
            use_kb = True
        except:
            use_kb = False
            print("⚠️  Usando PyAutoGUI")
    
    player = RobloxPianoPlayer(use_keyboard_lib=use_kb)
    
    print("\n🎵 MODO DE USO:")
    print("1. 🔍 Buscar música (anime, jogos, artistas)")
    print("2. 📁 Carregar arquivo MIDI (.mid)")
    print("3. ✍️  Inserir partitura manualmente")
    print("4. 📋 Ver músicas disponíveis")
    
    choice = input("\n➤ Escolha (1-4): ").strip()
    
    sheet = None
    
    if choice == '1':
        query = input("\n🔍 Nome da música: ")
        sheet = player.get_music_sheet(query)
        
    elif choice == '2':
        filepath = input("\n📁 Caminho do .mid: ").strip('"')
        if os.path.exists(filepath):
            sheet = player.midi_to_sheet(filepath)
        else:
            print("❌ Arquivo não encontrado!")
            
    elif choice == '3':
        print("\n✍️  Cole a partitura (ex: BPM:120 C3 D3 E3 F3 G3):")
        sheet = input("➤ ")
        
    elif choice == '4':
        print("\n📋 MÚSICAS NO BANCO:")
        print("  ✅ Bleach - Number One")
        print("  ✅ Naruto - Sadness and Sorrow")
        print("  ✅ Attack on Titan")
        print("  ✅ Demon Slayer - Gurenge")
        print("  ✅ One Piece - We Are")
        print("  ✅ Tokyo Ghoul - Unravel")
        print("  ✅ Your Name - Sparkle")
        print("  ✅ Jujutsu Kaisen - SPECIALZ")
        print("  ✅ JoJo - Giorno Theme")
        print("  ✅ Minecraft - Sweden")
        
        query = input("\n➤ Digite o nome: ")
        sheet = player.get_music_sheet(query)
    
    if sheet:
        print(f"\n📜 Partitura carregada!")
        player.play(sheet, show_keys=True)
    else:
        print("\n❌ Nenhuma partitura!")
    
    print("\n🎉 Obrigado!")


if __name__ == "__main__":
    main()