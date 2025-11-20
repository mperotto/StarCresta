import pygame
import os
from src.settings import *

def _carregar_sprite(caminho, largura, altura, force_transparent=False):
    try:
        if os.path.exists(caminho):
            img = pygame.image.load(caminho)
            if force_transparent:
                img = img.convert()
                img.set_colorkey((0, 0, 0))
            else:
                img = img.convert_alpha()
            return pygame.transform.smoothscale(img, (largura, altura))
    except Exception:
        pass
    return None

def criar_sprite_nave(largura, altura):
    surf = pygame.Surface((largura, altura), pygame.SRCALPHA)
    cx = largura // 2
    # corpo principal (nave estilizada)
    corpo = [(cx, 0), (largura-4, altura-6), (cx, altura-2), (4, altura-6)]
    pygame.draw.polygon(surf, (180, 220, 255), corpo)
    pygame.draw.polygon(surf, (80, 140, 220), corpo, 2)
    # cabine
    pygame.draw.ellipse(surf, (255, 255, 255), (cx-6, 6, 12, 10))
    pygame.draw.ellipse(surf, (100, 200, 255), (cx-5, 7, 10, 8))
    # asas
    asa_esq = [(4, altura-8), (cx-8, altura-12), (cx-10, altura-6)]
    asa_dir = [(largura-4, altura-8), (cx+8, altura-12), (cx+10, altura-6)]
    pygame.draw.polygon(surf, (160, 200, 255), asa_esq)
    pygame.draw.polygon(surf, (160, 200, 255), asa_dir)
    # bico destacando
    pygame.draw.circle(surf, (255, 255, 255), (cx, 2), 2)
    return surf

def carregar_sprite_nave(largura, altura):
    # tenta assets/player.png
    sprite = _carregar_sprite(os.path.join('assets', 'player.png'), largura, altura)
    if sprite:
        return sprite
    return criar_sprite_nave(largura, altura)

def carregar_sprite_inimigo_a(largura, altura):
    sprite = _carregar_sprite(os.path.join('assets', 'enemy_a.png'), largura, altura)
    if sprite:
        return sprite
    return None

def carregar_sprite_inimigo_b(largura, altura):
    sprite = _carregar_sprite(os.path.join('assets', 'enemy_b.png'), largura, altura)
    if sprite:
        return sprite
    return None

def carregar_sprite_boss(largura, altura):
    # Forçar transparência preta para o boss gerado
    sprite = _carregar_sprite(os.path.join('assets', 'boss.png'), largura, altura, force_transparent=True)
    if sprite:
        return sprite
    return None

def carregar_sprites_asteroide_opcoes(largura, altura):
    # tenta vários meteoros do pack Kenney
    opcoes = [
        'PNG/Meteors/meteorBrown_big1.png',
        'PNG/Meteors/meteorBrown_big2.png',
        'PNG/Meteors/meteorBrown_big3.png',
        'PNG/Meteors/meteorGrey_big1.png',
        'PNG/Meteors/meteorGrey_big2.png',
        'PNG/Meteors/meteorGrey_big3.png',
    ]
    sprites = []
    for nm in opcoes:
        s = _carregar_sprite(os.path.join('assets', 'kenney', nm), largura, altura)
        if s:
            sprites.append(s)
    # fallback: tentará um arquivo único em assets/asteroid.png
    if not sprites:
        s = _carregar_sprite(os.path.join('assets', 'asteroid.png'), largura, altura)
        if s:
            sprites.append(s)
    return sprites

def carregar_sprite_powerup(largura, altura):
    # tenta algumas opções típicas do pack Kenney Power-ups
    candidatos = [
        'PNG/Power-ups/powerupBlue_bolt.png',
        'PNG/Power-ups/powerupYellow_bolt.png',
        'PNG/Power-ups/powerupGreen_bolt.png',
        'PNG/Power-ups/powerupBlue_star.png',
    ]
    # inclui também opções de shield
    candidatos.extend([
        'PNG/Power-ups/powerupBlue_shield.png',
        'PNG/Power-ups/powerupRed_shield.png',
    ])
    for nm in candidatos:
        s = _carregar_sprite(os.path.join('assets', 'kenney', nm), largura, altura)
        if s:
            return s
    return _carregar_sprite(os.path.join('assets', 'powerup.png'), largura, altura)

def carregar_sprite_powerup_vida(largura, altura):
    # Forçar transparência preta para o powerup gerado
    s = _carregar_sprite(os.path.join('assets', 'powerup_health.png'), largura, altura, force_transparent=True)
    if s:
        return s
    # fallback
    surf = pygame.Surface((largura, altura), pygame.SRCALPHA)
    pygame.draw.circle(surf, (255, 50, 50), (largura//2, altura//2), largura//2)
    pygame.draw.rect(surf, (255, 255, 255), (largura//2 - 2, altura//2 - 6, 4, 12))
    pygame.draw.rect(surf, (255, 255, 255), (largura//2 - 6, altura//2 - 2, 12, 4))
    return surf

def carregar_som(nome, vol=0.35):
    caminho = os.path.join('sound', nome)
    if os.path.exists(caminho):
        try:
            s = pygame.mixer.Sound(caminho)
            s.set_volume(vol)
            return s
        except Exception:
            return None
    return None
