import pyautogui
import time
import re
import keyboard
from datetime import datetime, timedelta
import os

class RobloxPianoLoopPlayer:
    def __init__(self):
        pyautogui.PAUSE = 0.01
        pyautogui.FAILSAFE = True
        
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
        
        self.base_delay = 0.25
        self.chord_delay = 0.05
        self.bar_delay = 0.5
    
    def parse_sheet(self, sheet_music):
        """Parser de partitura"""
        commands = []
        sheet_music = ' '.join(sheet_music.split())
        
        pattern = r'\[([A-Gb#0-9\s]+)\]|BPM:(\d+)|\||([A-G][#b]?\d)(?:-(\d+))?'
        matches = list(re.finditer(pattern, sheet_music))
        
        for match in matches:
            if match.group(1):  # Acorde
                notes = re.findall(r'[A-G][#b]?\d', match.group(1))
                if notes:
                    commands.append(('chord', notes))
                    
            elif match.group(2):  # BPM
                bpm = int(match.group(2))
                self.base_delay = 60.0 / bpm / 2
                continue
                
            elif match.group(0) == '|':  # Pausa
                commands.append(('pause', self.bar_delay))
                
            elif match.group(3):  # Nota
                note = match.group(3)
                delay = float(match.group(4)) / 1000 if match.group(4) else self.base_delay
                commands.append(('note', note, delay))
        
        return commands
    
    def play_note(self, note):
        """Toca nota"""
        key = self.note_mapping.get(note)
        if not key:
            return
        
        needs_shift = key.isupper() or key in '!@$%^*()'
        actual_key = key.lower() if key.isalpha() else key
        
        try:
            if needs_shift:
                keyboard.press('shift')
                time.sleep(0.01)
            keyboard.press(actual_key)
            time.sleep(0.03)
            keyboard.release(actual_key)
            if needs_shift:
                keyboard.release('shift')
        except Exception as e:
            pass
    
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
        except Exception as e:
            pass
    
    def play_song(self, sheet_music, song_name):
        """Toca uma música"""
        print(f"\n🎵 Tocando: {song_name}")
        
        commands = self.parse_sheet(sheet_music)
        
        if not commands:
            return
        
        for command in commands:
            cmd_type = command[0]
            
            try:
                if cmd_type == 'note':
                    _, note, delay = command
                    self.play_note(note)
                    time.sleep(delay)
                    
                elif cmd_type == 'chord':
                    _, notes = command
                    self.play_chord(notes)
                    time.sleep(self.base_delay)
                    
                elif cmd_type == 'pause':
                    _, delay = command
                    time.sleep(delay)
                    
            except KeyboardInterrupt:
                raise
            except Exception as e:
                continue
    
    def load_sheets_from_file(self, filename):
        """Carrega partituras do arquivo"""
        sheets = []
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Processa cada linha que começa com nome
            lines = content.strip().split('\n')
            current_name = None
            current_sheet = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Se começa com emoji ou tem ":" é nome
                if any(emoji in line for emoji in ['🎵', '🎹', '🎼', '♫']) or (line.count(':') == 1 and not line.startswith('BPM')):
                    if current_name and current_sheet:
                        sheets.append((current_name, current_sheet))
                    current_name = line
                    current_sheet = None
                elif line.startswith('BPM:'):
                    current_sheet = line
            
            # Adiciona última música
            if current_name and current_sheet:
                sheets.append((current_name, current_sheet))
                
        except FileNotFoundError:
            print(f"❌ Arquivo {filename} não encontrado!")
            return []
        
        return sheets
    
    def play_loop(self, duration_minutes=20):
        """Toca em loop por X minutos"""
        print("=" * 70)
        print("🎹 ROBLOX AUTO PIANO - MODO LOOP INFINITO")
        print("=" * 70)
        print(f"\n⏰ Duração: {duration_minutes} minutos")
        print(f"📁 Carregando partituras de 'partituras.txt'...")
        
        sheets = self.load_sheets_from_file('partituras.txt')
        
        if not sheets:
            print("\n❌ Nenhuma partitura carregada!")
            return
        
        print(f"✅ {len(sheets)} músicas carregadas!\n")
        
        print("⚡ PREPARAÇÃO:")
        print("   1. Abra Roblox em MODO JANELA")
        print("   2. Clique NO PIANO VIRTUAL do jogo")
        print("   3. NÃO mova o mouse depois")
        print("\n⏰ Iniciando em 5 segundos...\n")
        
        for i in range(5, 0, -1):
            print(f"{'🔴' if i <= 3 else '🟡'} {i}...")
            time.sleep(1)
        
        print("\n🎹 TOCANDO AGORA!\n")
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        song_count = 0
        
        try:
            while datetime.now() < end_time:
                for name, sheet in sheets:
                    if datetime.now() >= end_time:
                        break
                    
                    song_count += 1
                    remaining = (end_time - datetime.now()).total_seconds() / 60
                    
                    print(f"\n{'='*70}")
                    print(f"🎵 Música #{song_count} - {name}")
                    print(f"⏱️  Tempo restante: {remaining:.1f} minutos")
                    print(f"{'='*70}")
                    
                    self.play_song(sheet, name)
                    
                    # Pausa entre músicas
                    time.sleep(2)
                
        except KeyboardInterrupt:
            print("\n\n⛔ INTERROMPIDO PELO USUÁRIO!")
        
        elapsed = (datetime.now() - start_time).total_seconds() / 60
        print(f"\n{'='*70}")
        print(f"✅ SESSÃO CONCLUÍDA!")
        print(f"🎵 {song_count} músicas tocadas")
        print(f"⏱️  Tempo total: {elapsed:.1f} minutos")
        print(f"{'='*70}\n")


def main():
    print("=" * 70)
    print("🎹 ROBLOX AUTO PIANO - LOOP INFINITO V1.0")
    print("=" * 70)
    
    # Instala keyboard se necessário
    try:
        import keyboard
    except:
        print("\n📦 Instalando biblioteca 'keyboard'...")
        os.system("pip install keyboard")
        import keyboard
    
    player = RobloxPianoLoopPlayer()
    
    # Pergunta duração
    print("\n⏰ Por quanto tempo deseja tocar?")
    duration = input("➤ Minutos (padrão: 20): ").strip()
    
    try:
        duration = int(duration) if duration else 20
    except:
        duration = 20
    
    player.play_loop(duration_minutes=duration)
    
    print("\n🎉 Obrigado por usar o Auto Piano!")


if __name__ == "__main__":
    main()