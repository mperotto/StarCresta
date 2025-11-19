import pygame, random
from spacegame.entities.base import ObjetoDeJogo
from spacegame.settings import S, SCALE, H, W
from spacegame.assets import get_powerup_sprite

class Upgrade(ObjetoDeJogo):
    def __init__(self, x, y, velocidade=90, tipo='v'):
        super().__init__(x, y, S(18), S(18))
        self.velocidade = velocidade * SCALE
        self.cor = (140, 200, 255)
        self.tipo = tipo  # 'v' ou 'shield'
        self.sprite = get_powerup_sprite((self.largura, self.altura))

    def atualizar(self, dt):
        self.y += self.velocidade * dt
        if self.y > H:
            self.matar()
        self.sincronizar_retangulo()

    def desenhar(self, tela):
        if self.sprite is not None:
            tela.blit(self.sprite, self.retangulo.topleft)
        else:
            pygame.draw.rect(tela, self.cor, self.retangulo, border_radius=4)

class GerenciadorDeUpgrades:
    def __init__(self):
        self.upgrades = []
        self.tempo = 0.0
        self.intervalo = 1.2

    def criar(self, upgrade: Upgrade):
        self.upgrades.append(upgrade)

    def atualizar(self, dt):
        self.tempo += dt
        if self.tempo >= self.intervalo:
            self.tempo = 0.0
            if random.random() < 0.28:
                x = 20 + int(random.random() * (W - 40))
                tipo = 'shield' if random.random() < 0.35 else 'v'
                self.criar(Upgrade(x, -18, tipo=tipo))
        for u in self.upgrades:
            u.atualizar(dt)
        self.upgrades = [u for u in self.upgrades if not u.esta_morto()]

    def desenhar(self, tela):
        for u in self.upgrades:
            u.desenhar(tela)

