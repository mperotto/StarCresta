import pygame
from src.settings import *
from src.sprites.base import ObjetoDeJogo
from src.sprites.projectile import Tiro, SuperTiro
from src.assets import carregar_sprite_nave

class Jogador(ObjetoDeJogo):
    def __init__(self, x, y):
        super().__init__(x, y, S(36), S(24))
        self.tempo_recarga = 0.0
        self.sprite = carregar_sprite_nave(self.largura, self.altura)
        self.spawn_anim = 0.0
        self.coletou_shield = False
        self.nivel_arma = 0  # 0-3, afeta o número de tiros

    def atualizar(self, dt):
        if self.spawn_anim > 0.0:
            alvo_y = ALTURA - 80
            self.y = max(alvo_y, self.y - 140 * dt)
            self.spawn_anim = max(0.0, self.spawn_anim - dt)
        else:
            teclas = pygame.key.get_pressed()
            dx = (teclas[pygame.K_RIGHT] - teclas[pygame.K_LEFT]) * VELOCIDADE_JOGADOR * dt
            dy = (teclas[pygame.K_DOWN] - teclas[pygame.K_UP]) * VELOCIDADE_JOGADOR * dt
            self.x = max(0, min(LARGURA - self.largura, self.x + dx))
            self.y = max(0, min(ALTURA - self.altura, self.y + dy))
        self.tempo_recarga = max(0, self.tempo_recarga - dt)
        self.sincronizar_retangulo()

    def desenhar(self, tela):
        tela.blit(self.sprite, self.retangulo.topleft)

    def pode_atirar(self): return self.tempo_recarga <= 0
    def atirar(self):
        self.tempo_recarga = 0.1
        # centraliza o tiro no topo do jogador
        return Tiro(self.x + self.largura/2 - 3, self.y - 12)
    def atirar_super(self):
        # recarga maior para super tiro
        self.tempo_recarga = 0.8
        return SuperTiro(self.x + self.largura/2 - 12, self.y - 18)
