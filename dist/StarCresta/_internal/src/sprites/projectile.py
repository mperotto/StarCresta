import pygame
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
