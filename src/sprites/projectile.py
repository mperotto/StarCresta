import pygame
import math
from src.settings import *
from src.sprites.base import ObjetoDeJogo

class Tiro(ObjetoDeJogo):
    def __init__(self, x, y, vx=0.0, vy=VELOCIDADE_TIRO):
        super().__init__(x, y, S(6), S(12))
        self.vx = float(vx)
        self.vy = float(vy)

    def atualizar(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.y < -self.altura or self.x < -self.largura or self.x > LARGURA:
            self.matar()
        self.sincronizar_retangulo()

    def desenhar(self, tela):
        pygame.draw.rect(tela, (255, 240, 120), self.retangulo)

class SuperTiro(ObjetoDeJogo):
    def __init__(self, x, y, vx=0.0, vy=VELOCIDADE_TIRO):
        # 4x mais largo que o tiro normal (6 -> 24)
        super().__init__(x, y, S(24), S(18))
        self.perfurante = True
        self.vx = float(vx)
        self.vy = float(vy)

    def atualizar(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.y < -self.altura or self.x < -self.largura or self.x > LARGURA:
            self.matar()
        self.sincronizar_retangulo()

    def desenhar(self, tela):
        pygame.draw.rect(tela, (180, 255, 255), self.retangulo)

class LaserBeam(ObjetoDeJogo):
    def __init__(self, x, y, altura, tracker=None):
        largura = S(16)
        super().__init__(x - largura//2, y - altura, largura, int(altura))
        self.vida = 0.08
        self.perfurante = True
        self.t = 0.0
        self.tracker = tracker  # callable retornando (cx, y_top)
        self.altura_ref = int(altura)

    def atualizar(self, dt):
        self.t += dt
        if self.tracker:
            try:
                cx, topy = self.tracker()
                self.x = cx - self.largura/2
                self.y = topy - self.altura_ref
            except Exception:
                pass
        self.vida -= dt
        if self.vida <= 0:
            self.matar()
        self.sincronizar_retangulo()

    def desenhar(self, tela):
        rect = self.retangulo
        t = self.t
        # surface com alpha para glow e ondas
        surf = pygame.Surface((rect.width + 12, rect.height + 10), pygame.SRCALPHA)
        halo_color = (120, 40, 160, 90)
        core_color = (255, 140, 255, 210)
        # halo base
        pygame.draw.rect(surf, halo_color, (0, 0, surf.get_width(), surf.get_height()), border_radius=6)
        # núcleo
        pygame.draw.rect(surf, core_color, (6, 5, rect.width, rect.height), border_radius=3)
        # ondas sinuosas laterais
        cx = surf.get_width() // 2
        for i in range(3):
            phase = t * 10 + i * 0.8
            amp = 3 + i * 1.5
            color = (255, 200 - i * 20, 255, 180)
            y_step = 18 - i * 2
            y = 0
            while y < surf.get_height():
                dx = int(math.sin(phase + y * 0.08) * amp)
                pygame.draw.line(surf, color, (cx + dx - 2, y), (cx + dx + 2, y + y_step), 3)
                y += y_step
        tela.blit(surf, (rect.x - 6, rect.y - 5))

class TiroInimigo(ObjetoDeJogo):
    def __init__(self, x, y, vx=0.0, vy=180):
        super().__init__(x, y, S(4), S(10))
        self.vx = float(vx)
        self.vy = float(vy) * SCALE

    def atualizar(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.y > ALTURA + self.altura or self.x < -self.largura or self.x > LARGURA:
            self.matar()
        self.sincronizar_retangulo()

    def desenhar(self, tela):
        pygame.draw.rect(tela, (255, 100, 120), self.retangulo)
