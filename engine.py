import pygame
import json
import os
import random
import copy
from settings import *
from inventory import Inventory
from action_bar import ActionBar
from boss_designer import BossDesigner

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
        for x in range(MAP_SIZE):
            default_map[0][x] = TileType.WALL_BRICK.value
            default_map[MAP_SIZE-1][x] = TileType.WALL_BRICK.value
        for y in range(MAP_SIZE):
            default_map[y][0] = TileType.WALL_BRICK.value
            default_map[y][MAP_SIZE-1] = TileType.WALL_BRICK.value
        return default_map

    def load_game_state(self):
        try:
            with open(SAVEGAME_FILE, 'r') as f:
                data = json.load(f)
                self.level = data.get('level', 1)
                self.experience = data.get('experience', 0)
                self.health = data.get('health', self.max_health)
                self.mana = data.get('mana', self.max_mana)
                self.stamina = data.get('stamina', self.max_stamina)
                self.player_x = data.get('player_x', 25)
                self.player_y = data.get('player_y', 25)
                self.inventory.items = data.get('inventory', {})
                self.strength = data.get('strength', 10)
                self.intelligence = data.get('intelligence', 10)
                self.endurance = data.get('endurance', 10)
                self.stat_points = data.get('stat_points', 0)
                self.recalculate_max_stats()
        except:
            pass

    def save_game_state(self):
        data = {
            'level': self.level,
            'experience': self.experience,
            'health': self.health,
            'mana': self.mana,
            'stamina': self.stamina,
            'player_x': self.player_x,
            'player_y': self.player_y,
            'inventory': self.inventory.items,
            'strength': self.strength,
            'intelligence': self.intelligence,
            'endurance': self.endurance,
            'stat_points': self.stat_points
        }
        try:
            with open(SAVEGAME_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except:
            pass

    def recalculate_max_stats(self):
        self.max_health = 50 + self.endurance * 5
        self.max_mana = 30 + self.intelligence * 3
        self.max_stamina = 40 + self.endurance * 2
        
    def use_hotkey_action(self, slot):
        item = self.inventory.get_item(slot["item_id"])
        if item:
            self.use_item(item)

    def use_item(self, item):
        if item["type"] == "consumable":
            if "health_restore" in item:
                self.health = min(self.health + item["health_restore"], self.max_health)
                if self.sfx.get("pickup"): self.sfx["pickup"].play()
            if "mana_restore" in item:
                self.mana = min(self.mana + item["mana_restore"], self.max_mana)
                if self.sfx.get("pickup"): self.sfx["pickup"].play()
            if "stamina_restore" in item:
                self.stamina = min(self.stamina + item["stamina_restore"], self.max_stamina)
                if self.sfx.get("pickup"): self.sfx["pickup"].play()
            self.inventory.remove_item(item["id"], 1)

    def item_name_to_tile_value(self, name):
        mapping = {
            "Health Potion": TileType.ITEM_HEALTH_POTION.value,
            "Mana Potion": TileType.ITEM_FOOD.value,
            "Stamina Potion": TileType.ITEM_STAMINA_POTION.value,
            "Sword": TileType.ITEM_DAGGER.value,
            "Brass Key": TileType.ITEM_KEY.value,
            "Silver Key": TileType.ITEM_KEY_SILVER.value,
            "Gold Key": TileType.ITEM_KEY_GOLD.value,
            "Dungeon Key": TileType.ITEM_KEY_DUNGEON.value,
            "Rusty Key 2": TileType.ITEM_KEY_RUSTY_2.value    
        }
        return mapping.get(name)

    def run(self):
        while True:
            if self.show_stat_screen:
                for e in pygame.event.get():
                    if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                        self.save_game_state()
                        if MIXER_READY: pygame.mixer.music.stop()
                        return
                    elif e.type == pygame.KEYDOWN and e.key == pygame.K_c:
                        self.show_stat_screen = False
                    elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                        mx, my = pygame.mouse.get_pos()
                        for btn_name, rect in self.stat_btn_rects:
                            if rect.collidepoint((mx, my)):
                                if btn_name == "CLOSE":
                                    self.show_stat_screen = False
                                elif self.stat_points > 0:
                                    if btn_name == "STR": self.strength += 1
                                    elif btn_name == "INT": self.intelligence += 1
                                    elif btn_name == "END": 
                                        self.endurance += 1
                                        self.health += 5 
                                        self.stamina += 5
                                    self.stat_points -= 1
                                    self.recalculate_max_stats()
                                    if self.sfx.get("pickup"): self.sfx["pickup"].play()
                
                self.draw() 
                pygame.display.flip()
                self.clock.tick(FPS)
                continue
            
            h, w = len(self.map), len(self.map[0])
            if self.health <= 0 and not self.game_over:
                self.game_over = True
                self.game_over_timer = 180
                if self.sfx.get("error"): self.sfx["error"].play()
                
            if self.game_over:
                self.game_over_timer -= 1
                if self.game_over_timer <= 0:
                    self.health = self.max_health
                    self.mana = self.max_mana
                    self.stamina = self.max_stamina
                    self.player_x, self.player_y = self.get_safe_spawn()
                    self.game_over = False
                    self.in_combat = False
                    self.save_game_state()

            if self.level_complete and self.level_complete_timer <= 0:
                self.save_game_state()
                if MIXER_READY: pygame.mixer.music.stop()
                if CH_WALK.get_busy(): CH_WALK.stop()
                if CH_RAIN.get_busy(): CH_RAIN.stop()
                if CH_CRICKETS.get_busy(): CH_CRICKETS.stop() 
                if CH_TORCHES.get_busy(): CH_TORCHES.stop() 
                return
                
            for e in pygame.event.get():
                if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE): 
                    self.save_game_state()
                    if MIXER_READY: pygame.mixer.music.stop()
                    if CH_WALK.get_busy(): CH_WALK.stop()
                    if CH_RAIN.get_busy(): CH_RAIN.stop()
                    if CH_CRICKETS.get_busy(): CH_CRICKETS.stop() 
                    if CH_TORCHES.get_busy(): CH_TORCHES.stop() 
                    return
                    
                elif e.type == pygame.KEYDOWN and not self.level_complete and not self.game_over:
                    if e.key == pygame.K_i: self.inventory.toggle()
                    elif e.key == pygame.K_c: self.show_stat_screen = True
                    for slot in self.action_bar.slots:
                        if e.key == slot["key"]: self.use_hotkey_action(slot)

                elif e.type == pygame.MOUSEBUTTONDOWN and not self.level_complete and not self.game_over:
                    pass

            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)
