import os
import pygame
from spacegame.settings import ASSETS_DIR

_img_cache = {}
_snd_cache = {}

def load_image(path: str, size=None, alpha: bool = True):
    key = (path, size, alpha)
    surf = _img_cache.get(key)
    if surf is not None:
        return surf
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    surf = pygame.image.load(path)
    surf = surf.convert_alpha() if alpha else surf.convert()
    if size:
        surf = pygame.transform.smoothscale(surf, size)
    _img_cache[key] = surf
    return surf

def load_sound(path: str, vol: float = 0.35):
    snd = _snd_cache.get(path)
    if snd is not None:
        return snd
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    snd = pygame.mixer.Sound(path)
    snd.set_volume(vol)
    _snd_cache[path] = snd
    return snd

# Convenience helpers mirroring legacy loaders (no ZIP, direct files)
def _path(*parts):
    return os.path.join(*parts)

def get_player_sprite(size):
    path = _path(ASSETS_DIR, 'player.png')
    if os.path.exists(path):
        return load_image(path, size=size, alpha=True)
    # fallback: draw a simple ship
    w, h = size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx = w // 2
    body = [(cx, 0), (w-4, h-6), (cx, h-2), (4, h-6)]
    pygame.draw.polygon(surf, (180,220,255), body)
    pygame.draw.polygon(surf, (80,140,220), body, 2)
    pygame.draw.ellipse(surf, (255,255,255), (cx-6, 6, 12, 10))
    pygame.draw.ellipse(surf, (100,200,255), (cx-5, 7, 10, 8))
    return surf

def get_enemy_a_sprite(size):
    path = _path(ASSETS_DIR, 'enemy_a.png')
    return load_image(path, size=size, alpha=True) if os.path.exists(path) else None

def get_enemy_b_sprite(size):
    path = _path(ASSETS_DIR, 'enemy_b.png')
    return load_image(path, size=size, alpha=True) if os.path.exists(path) else None

def get_asteroid_sprites(size):
    rels = [
        _path(ASSETS_DIR, 'kenney', 'PNG', 'Meteors', 'meteorBrown_big1.png'),
        _path(ASSETS_DIR, 'kenney', 'PNG', 'Meteors', 'meteorBrown_big2.png'),
        _path(ASSETS_DIR, 'kenney', 'PNG', 'Meteors', 'meteorBrown_big3.png'),
        _path(ASSETS_DIR, 'kenney', 'PNG', 'Meteors', 'meteorGrey_big1.png'),
        _path(ASSETS_DIR, 'kenney', 'PNG', 'Meteors', 'meteorGrey_big2.png'),
        _path(ASSETS_DIR, 'kenney', 'PNG', 'Meteors', 'meteorGrey_big3.png'),
    ]
    out = []
    for p in rels:
        if os.path.exists(p):
            out.append(load_image(p, size=size, alpha=True))
    if not out:
        p = _path(ASSETS_DIR, 'asteroid.png')
        if os.path.exists(p):
            out.append(load_image(p, size=size, alpha=True))
    return out

def get_powerup_sprite(size):
    rels = [
        _path(ASSETS_DIR, 'kenney', 'PNG', 'Power-ups', 'powerupBlue_bolt.png'),
        _path(ASSETS_DIR, 'kenney', 'PNG', 'Power-ups', 'powerupYellow_bolt.png'),
        _path(ASSETS_DIR, 'kenney', 'PNG', 'Power-ups', 'powerupGreen_bolt.png'),
        _path(ASSETS_DIR, 'kenney', 'PNG', 'Power-ups', 'powerupBlue_star.png'),
        _path(ASSETS_DIR, 'kenney', 'PNG', 'Power-ups', 'powerupBlue_shield.png'),
        _path(ASSETS_DIR, 'kenney', 'PNG', 'Power-ups', 'powerupRed_shield.png'),
    ]
    for p in rels:
        if os.path.exists(p):
            return load_image(p, size=size, alpha=True)
    p = _path(ASSETS_DIR, 'powerup.png')
    return load_image(p, size=size, alpha=True) if os.path.exists(p) else None
