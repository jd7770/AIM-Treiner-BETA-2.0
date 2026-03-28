import sys
import os
import math
import random
import json
import pygame
import numpy as np
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from panda3d.core import loadPrcFileData
import os
import sys

# Esta función mágica encuentra la carpeta real de los archivos cuando es un .exe
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Ahora actualizamos las rutas de tus archivos usando la función:
LOGO_PATH = resource_path("logo.png")
LOBBY_PATH = resource_path("lobby.mp3")
# --- OPTIMIZACIÓN DEL MOTOR ---
loadPrcFileData("", "load-display pandagl")
loadPrcFileData("", "notify-level-glgsg fatal")

app = Ursina()

# ==========================================
# MOTOR DE AUDIO PROFESIONAL
# ==========================================
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.mixer.init()

class ProAudio:
    def __init__(self):
        self.click_sound = self._gen_tone(600, 0.02)   
        self.track_hit = self._gen_tone(440, 0.05)     
        self.track_miss = self._gen_tone(880, 0.05)    

    def _gen_tone(self, freq, dur):
        sr = 44100
        t = np.linspace(0, dur, int(sr * dur), False)
        wave = np.sin(2 * np.pi * freq * t) * 32767 * 0.1
        return pygame.mixer.Sound(buffer=wave.astype(np.int16))

    def play_lobby(self):
        if os.path.exists("lobby.mp3"):
            pygame.mixer.music.load("lobby.mp3")
            pygame.mixer.music.set_volume(0.3)
            pygame.mixer.music.play(-1)

    def stop_lobby(self):
        pygame.mixer.music.fadeout(500)

snd = ProAudio()

# ==========================================
# CONFIGURACIÓN Y VARIABLES GLOBALES
# ==========================================
window.title = "AIM TRAINER BETA 2.0 - GOLD EDITION"
window.fullscreen = True
window.exit_button.visible = False
window.fps_counter.enabled = False 
window.color = color.black

speed_val = 5
time_limit = 60
is_playing = False
current_level = 'easy'
map_index = 1
map_selected = False 

time_on_target = 0
total_time_passed = 0
direction_x = 1
direction_z = 1
menu_state = 'main'
pause_timer = 0
is_paused = False

# Variables de la Máquina de Estados (Fusionadas)
bs_state = 0 
state_timer = 0 # IMPORTADO DEL CÓDIGO 2
current_random_speed = 10
target_y = 3
target_z = 20 

# --- SISTEMA DE RANKING ---
def cargar_ranking():
    if os.path.exists("ranking_aim.json"):
        try:
            with open("ranking_aim.json", "r") as f:
                return sorted([int(x) for x in json.load(f)], reverse=True)[:3]
        except: return [0, 0, 0]
    return [0, 0, 0]

def guardar_record(acc):
    actuales = cargar_ranking()
    actuales.append(int(acc))
    actuales = sorted(actuales, reverse=True)[:3]
    with open("ranking_aim.json", "w") as f: json.dump(actuales, f)

# ==========================================
# ESCENARIO Y JUGADOR
# ==========================================
ground = Entity(model='plane', scale=60, y=-2, color=color.dark_gray, texture='white_cube', texture_scale=(15,15), collider='box')
ceiling = Entity(model='plane', scale=60, y=15, rotation_x=180, color=color.dark_gray, texture='white_cube', texture_scale=(15,15))
wall_f = Entity(model='cube', scale=(60, 40, 1), z=25, color=color.black, collider='box')
wall_b = Entity(model='cube', scale=(60, 40, 1), z=-15, color=color.black, collider='box')
wall_l = Entity(model='cube', scale=(1, 40, 60), x=-25, color=color.black, collider='box')
wall_r = Entity(model='cube', scale=(1, 40, 60), x=25, color=color.black, collider='box')

target = Entity(model='cube', color=color.red, collider='box', position=(0, 3, 20), enabled=False)

player = FirstPersonController(y=1.5, z=-5, enabled=False)
player.cursor.model, player.cursor.scale, player.cursor.color = 'quad', 0.01, color.lime

# ==========================================
# INTERFAZ DE USUARIO (UI)
# ==========================================
main_menu = Entity(parent=camera.ui)
levels_menu = Entity(parent=camera.ui, enabled=False)
settings_menu = Entity(parent=camera.ui, enabled=False)
ranking_menu = Entity(parent=camera.ui, enabled=False)
ui_game = Entity(parent=camera.ui, enabled=False)

def set_menu_state(state):
    global menu_state
    snd.click_sound.play()
    menu_state = state
    main_menu.enabled = (state == 'main')
    levels_menu.enabled = (state == 'levels')
    settings_menu.enabled = (state == 'settings')
    ranking_menu.enabled = (state == 'ranking')
    if state == 'main' and map_selected: start_txt.text = "Presiona 'ENTER' para jugar"
    if state == 'ranking':
        recs = cargar_ranking()
        for i, t in enumerate(r_labels): t.text = f"TOP {i+1}: {recs[i] if i < len(recs) else 0}%"

# --- MENÚ PRINCIPAL ---
logo = Entity(parent=main_menu, model='quad', texture='logo.png', y=0.25, scale=(0.5, 0.25))
start_txt = Text("", parent=main_menu, y=-0.1, color=color.yellow, origin=(0,0))
btn_style = {'x': -0.7, 'scale': (0.2, 0.05), 'origin': (-0.5, 0)}
Button('MAPAS', parent=main_menu, y=-0.2, on_click=lambda: set_menu_state('levels'), **btn_style)
Button('AJUSTES', parent=main_menu, y=-0.27, on_click=lambda: set_menu_state('settings'), **btn_style)
Button('RANKING', parent=main_menu, y=-0.34, on_click=lambda: set_menu_state('ranking'), **btn_style)

# --- AJUSTES ---
speed_label = Text('', parent=settings_menu, y=0.25, scale=1.2, origin=(0,0), color=color.cyan)
time_label = Text('', parent=settings_menu, y=0.05, scale=1.2, origin=(0,0), color=color.yellow)

def adjust_speed(v):
    global speed_val
    speed_val = max(1, min(20, speed_val + v))
    speed_label.text = f'VELOCIDAD OBJETIVO: {speed_val}'
    snd.click_sound.play()

def set_time_limit(t):
    global time_limit
    time_limit = t
    time_label.text = f'TIEMPO DE SESIÓN: {time_limit}s'
    snd.click_sound.play()

adjust_speed(0)
set_time_limit(60)

Button('-', parent=settings_menu, x=-0.1, y=0.15, scale=0.06, on_click=lambda: adjust_speed(-1))
Button('+', parent=settings_menu, x=0.1, y=0.15, scale=0.06, on_click=lambda: adjust_speed(1))
for i, t in enumerate([30, 60, 120, 300]):
    Button(text=str(t), parent=settings_menu, x=-0.22 + (i * 0.15), y=-0.05, scale=(0.12, 0.05), on_click=Func(set_time_limit, t))
Button('VOLVER', parent=settings_menu, y=-0.3, scale=(0.2, 0.05), on_click=lambda: set_menu_state('main'))

# --- SELECCIÓN DE MAPAS ---
niveles = ['easy', 'medium', 'hard', 'bloodstrike']
for i, lvl in enumerate(niveles):
    Text(lvl.upper(), parent=levels_menu, x=-0.2, y=0.3 - (i*0.15), scale=1.2)
    for idx in range(1, 4):
        def select(l=lvl, n=idx):
            global current_level, map_index, map_selected
            snd.click_sound.play(); current_level, map_index = l, n; map_selected = True; set_menu_state('main')
        Button(str(idx), parent=levels_menu, x=0 + (idx*0.1), y=0.3 - (i*0.15), scale=0.05, on_click=select)
Button('VOLVER', parent=levels_menu, y=-0.4, scale=(0.15, 0.05), on_click=lambda: set_menu_state('main'))
r_labels = [Text('', parent=ranking_menu, y=0.1 - (j*0.15), scale=2, origin=(0,0), color=color.lime) for j in range(3)]
Button('VOLVER', parent=ranking_menu, y=-0.35, scale=(0.2, 0.05), on_click=lambda: set_menu_state('main'))

# --- HUD EN JUEGO ---
precision_bar_bg = Entity(parent=ui_game, model='quad', scale=(0.4, 0.02), y=-0.25, color=color.black66)
precision_bar = Entity(parent=ui_game, model='quad', scale=(0, 0.02), y=-0.25, color=color.lime, origin_x=-0.5, x=-0.2)
precision_hud = Text('', parent=ui_game, origin=(0,0), y=-0.2, scale=2, color=color.cyan)
timer_hud = Text('', parent=ui_game, position=(0, 0.4), origin=(0,0), scale=1.5)
fps_display = Text(text='FPS: 0', position=window.top_left + Vec2(0.02, -0.02), color=color.lime, parent=camera.ui)

# ==========================================
# LÓGICA PRINCIPAL DEL JUEGO (CORE FUSIONADO)
# ==========================================
def update():
    global is_playing, total_time_passed, direction_x, direction_z, is_paused, pause_timer
    global time_on_target, current_random_speed, target_y, target_z, bs_state, state_timer

    # RESTRICCIÓN: Jugador no se puede mover (player.speed=0)
    if player.speed != 0: player.speed = 0

    if time.dt > 0: fps_display.text = f'FPS: {int(1/time.dt)}'
    if not is_playing:
        if menu_state == 'main' and map_selected and held_keys['enter']: start_game()
        return

    total_time_passed += time.dt
    state_timer += time.dt # IMPORTANTE PARA MAPAS 2 Y 3

    if is_paused:
        pause_timer -= time.dt
        if pause_timer <= 0: is_paused = False
        return

    # --- LÓGICA DE MOVIMIENTO POR NIVELES CLÁSICOS ---
    if current_level == 'easy':
        if map_index == 1: target.x += direction_x * speed_val * time.dt
        elif map_index == 2:
            target.x += direction_x * 8 * time.dt
            target.z += direction_z * 10 * time.dt
            if target.z > 23 or target.z < 5: direction_z *= -1
        elif map_index == 3:
            target.x += direction_x * 9 * time.dt
            target.y = 4 + math.sin(total_time_passed * 4) * 5

    elif current_level == 'medium':
        if map_index == 1:
            if int(total_time_passed) % 2 == 0: current_random_speed = random.uniform(8, 22)
            target.x += direction_x * current_random_speed * time.dt
        elif map_index == 2:
            target.x += direction_x * 12 * time.dt
            if random.random() < 0.02: target_z = random.uniform(5, 22)
            target.z = lerp(target.z, target_z, time.dt * 4)
        elif map_index == 3: target.x += direction_x * 15 * time.dt

    elif current_level == 'hard':
        if map_index == 1:
            target.x += direction_x * 16 * time.dt
            if random.random() < 0.015: is_paused, pause_timer, direction_x = True, 1.2, direction_x * -1
        elif map_index == 2 or map_index == 3:
            target.x += direction_x * (20 if map_index == 2 else 25) * time.dt
            if random.random() < 0.03: target_y = random.choice([1, 8, 4])
            target.y = lerp(target.y, target_y, time.dt * 5)
            if map_index == 3 and random.random() < 0.02: 
                is_paused, pause_timer, direction_x = True, 0.4, direction_x * -1

    # ==========================================
    # --- 🔴 SECCIÓN BLOODSTRIKE (LA MEJOR COMBINACIÓN) 🔴 ---
    # ==========================================
    elif current_level == 'bloodstrike':
        
        # MOVIMIENTO 1 (DEL CÓDIGO 1): El Arco Perfecto que te gustó
        if map_index == 1:
            lat_spd = 16 
            target.x += direction_x * lat_spd * time.dt
            if target.x > 8: 
                target.x = 8; direction_x = -1
            elif target.x < -8: 
                target.x = -8; direction_x = 1
            target.y = 2 + (1 - (target.x / 8)**2) * 3 

        # MOVIMIENTO 2 (DEL CÓDIGO 2): A -> B -> C -> D (EL SALTO TÉCNICO)
        elif map_index == 2:
            duracion_paso = 1.0 / (speed_val * 0.2)
            
            if bs_state == 0: # A -> B: Diagonal adelante izquierda
                target.position = lerp(Vec3(0, 2, 25), Vec3(-10, 2, 15), state_timer / duracion_paso)
                if state_timer >= duracion_paso: bs_state = 1; state_timer = 0
            
            elif bs_state == 1: # B -> C -> D: Salto en arco hacia la derecha
                t = state_timer / duracion_paso
                target.x = lerp(-10, 10, t)
                target.y = 2 + math.sin(t * math.pi) * 8 # Altura máxima en C
                target.z = lerp(15, 20, t)
                if state_timer >= duracion_paso: bs_state = 2; state_timer = 0
                
            elif bs_state == 2: # Reset a A
                target.position = Vec3(0, 2, 25)
                bs_state = 0; state_timer = 0

        # MOVIMIENTO 3 (DEL CÓDIGO 2): IZ IZ IZ (PROFUNDIDAD + CÍRCULO)
        elif map_index == 3:
            puntos = [Vec3(0,2,25), Vec3(-12,2,20), Vec3(12,2,18), Vec3(0,2,10), Vec3(12,2,8)]
            dur = 0.6 / (speed_val * 0.2)
            
            p_actual = puntos[bs_state]
            p_siguiente = puntos[(bs_state + 1) % len(puntos)]
            
            target.position = lerp(p_actual, p_siguiente, state_timer / dur)
            
            if state_timer >= dur:
                bs_state = (bs_state + 1) % len(puntos)
                state_timer = 0
                if bs_state == 0: target.position = puntos[0]

    # Rebote clásico en X (solo para niveles normales)
    if current_level != 'bloodstrike':
        if target.x > 23: direction_x = -1
        elif target.x < -23: direction_x = 1

    # --- TRACKING Y SISTEMA DE PUNTUACIÓN ---
    if mouse.hovered_entity == target:
        time_on_target += time.dt
        if int(total_time_passed * 20) % 2 == 0: snd.track_hit.play()
    else:
        if int(total_time_passed * 10) % 2 == 0: snd.track_miss.play()
    
    acc = (time_on_target / total_time_passed) * 100 if total_time_passed > 0 else 100
    precision_hud.text = f'{int(acc)}%'
    precision_bar.scale_x = (acc / 100) * 0.4
    timer_hud.text = f'TIEMPO: {int(max(0, time_limit - total_time_passed))}s'
    
    if total_time_passed >= time_limit: end_game(acc)

# ==========================================
# GESTIÓN DE PARTIDAS
# ==========================================
def start_game():
    global is_playing, total_time_passed, time_on_target, bs_state, state_timer
    snd.stop_lobby()
    is_playing, total_time_passed, time_on_target, bs_state, state_timer = True, 0, 0, 0, 0
    set_menu_state('playing')
    start_txt.text = "" 
    
    # Restablecer modelo por defecto a Rectángulo
    target.model = 'cube'
    target.scale = (2, 4, 0.5) 
    target.enabled = True
    
    # RESTRICCIÓN: Jugador no se puede mover
    player.speed = 0
    player.enabled = True # Solo para el ratón

    # Posicionamiento inicial y configuración de modelo según el nivel
    if current_level == 'bloodstrike':
        if map_index == 1: 
            target.position = (0, 3, 20)
        elif map_index == 2: 
            target.position = (0, 2, 25) # Arranca exacto donde pide el código 2
        elif map_index == 3: 
            target.model = 'sphere'
            target.scale = (2.2, 2.2, 2.2) 
            target.position = (0, 2, 25) # Arranca exacto donde pide el código 2
    else:
        # Niveles normales usan Rectángulo
        target.position = (0, 3, 20)
        if current_level == 'easy':
            if map_index == 2: target.scale = (1.5, 4, 1.5)
            if map_index == 3: target.model, target.scale = 'sphere', (2, 2, 2)
        elif current_level == 'hard': target.scale = (1.2, 1.2, 0.5)

    mouse.locked = ui_game.enabled = True

def end_game(acc):
    global is_playing
    is_playing = False
    snd.play_lobby()
    guardar_record(acc)
    target.enabled = player.enabled = mouse.locked = ui_game.enabled = False
    set_menu_state('main')

# --- INICIO DEL PROGRAMA ---
snd.play_lobby()
app.run()