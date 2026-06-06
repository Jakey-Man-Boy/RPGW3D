import pygame
import json
import os
import random
import copy
from settings import *
from inventory import Inventory
from ui import ActionBar

class DummyChannel:
    def play(self, *args, **kwargs): pass
    def stop(self): pass
    def get_busy(self): return False
    def set_volume(self, vol): pass
    def fadeout(self, time): pass

try:
    pygame.mixer.init()
    CH_WALK = pygame.mixer.Channel(1)
    CH_RAIN = pygame.mixer.Channel(2)
    CH_CRICKETS = pygame.mixer.Channel(3)
    CH_TORCHES = pygame.mixer.Channel(4) 
    MIXER_READY = True
except Exception:
    CH_WALK = DummyChannel()
    CH_RAIN = DummyChannel()
    CH_CRICKETS = DummyChannel()
    CH_TORCHES = DummyChannel()
    MIXER_READY = False

def load_audio_safe(filename):
    if not MIXER_READY: return None
    try: return pygame.mixer.Sound(filename)
    except: return None

SFX_PICKUP = load_audio_safe("pickup.wav")
SFX_DOOR = load_audio_safe("door.wav")
SFX_ERROR = load_audio_safe("error.wav")
SFX_USE = load_audio_safe("use.wav")
SFX_WALK = load_audio_safe("walking.mp3")
SFX_RAIN = load_audio_safe("raining.mp3")
SFX_FIREBALL = load_audio_safe("shoot_fireball.wav")
SFX_DRINK = load_audio_safe("drink.wav")
SFX_CRICKETS = load_audio_safe("Midnight_crickets.mp3")
SFX_TORCH = load_audio_safe("torches_burning_sound.mp3") 
SFX_HIT_METALLIC = load_audio_safe("sword_hit_metallic.mp3")

class Game:
    def __init__(self):
        pygame.init()
        pygame.mouse.set_visible(False) 
        # Force double buffering and hardware scaling to squeeze out more FPS
        #self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.DOUBLEBUF | pygame.SCALED)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("RPGW3D Engine")
        self.clock = pygame.time.Clock()

        # Ensure a map attribute exists early so any helper called during init won't crash.
        # We try to use TileType / MAP_SIZE but fall back to a reasonable default if not available yet.
        try:
            self.map = [[TileType.EMPTY.value for _ in range(MAP_SIZE)] for _ in range(MAP_SIZE)]
        except Exception:
            # Fallback: 50x50 zero map (safe placeholder)
            self.map = [[0 for _ in range(50)] for _ in range(50)]
        
        self.font = pygame.font.SysFont("georgia", 16) 
        self.font_msg = pygame.font.SysFont("georgia", 20, bold=True)
        self.font_small_bold = pygame.font.SysFont("georgia", 14, bold=True)
        self.font_massive = pygame.font.SysFont("georgia", 60, bold=True)
        self.font_massive_win = pygame.font.SysFont("georgia", 50, bold=True)
        
        self.game_over_overlay = pygame.Surface((WIDTH, HEIGHT))
        self.game_over_overlay.set_alpha(200)
        self.game_over_overlay.fill((100, 0, 0))
        
        self.level_complete_overlay = pygame.Surface((WIDTH, HEIGHT))
        self.level_complete_overlay.set_alpha(180)
        self.level_complete_overlay.fill((0, 0, 0))
        
        self.stat_points = 5
        self.strength = 10
        self.intelligence = 10
        self.endurance = 10
        self.show_stat_screen = False

    def get_initial_map_data(self):
        # Create a default map bordered by walls just in case the JSON fails
        default_map = [[TileType.EMPTY.value for _ in range(MAP_SIZE)] for _ in range(MAP_SIZE)]
        for i in range(MAP_SIZE):
            default_map[0][i] = default_map[MAP_SIZE-1][i] = default_map[i][0] = default_map[i][MAP_SIZE-1] = TileType.WALL_BRICK.value
        
        try:
            if os.path.exists(MAP_DATA_FILE):
                with open(MAP_DATA_FILE, "r") as f:
                    data = json.load(f)
                    # Verify map dimensions match your settings
                    if len(data) == MAP_SIZE and len(data[0]) == MAP_SIZE:
                        print(f"Map successfully loaded from {MAP_DATA_FILE}.")
                        return data
                    else:
                        print("Map data size mismatch! Falling back to default map.")
        except Exception as e:
            print(f"Failed to load map data from {MAP_DATA_FILE}: {e}")
            
        return default_map

    def recalculate_max_stats(self):
        self.max_health = 50 + (self.endurance * 5)
        self.max_mana = 20 + (self.intelligence * 3)
        self.max_stamina = 50 + (self.endurance * 5)
        self.melee_dmg = 20 + int(self.strength * 1.5)
        self.magic_dmg = 25 + int(self.intelligence * 2.0)

    def run(self):
        while True:
            if self.show_stat_screen:
                for e in pygame.event.get():
                    if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                        return
                    elif e.type == pygame.KEYDOWN and e.key == pygame.K_c:
                        self.show_stat_screen = False

                pygame.display.flip()
                self.clock.tick(FPS)
                continue
            
            for e in pygame.event.get():
                if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                    return
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_c:
                        self.show_stat_screen = True

            pygame.display.flip()
            self.clock.tick(FPS)
