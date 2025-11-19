import pygame, random, math
from spacegame.entities.base import ObjetoDeJogo
from spacegame.settings import SCALE
from spacegame.assets import get_asteroid_sprites

class Destroco(ObjetoDeJogo):
    def __init__(self, x, y, raio=6, vx=0.0, vy=0.0, origin='env'):
        r = max(1, int(round(raio * SCALE)))
        super().__init__(x, y, int(r*2), int(r*2))
        self.raio = int(r)
        self.vx = float(vx)
        self.vy = float(vy)
        self.angulo = random.uniform(0, 360)
        self.rot_vel = random.uniform(-180, 180)
        self.cor = (150 + random.randint(-20, 20), 140 + random.randint(-20, 20), 130 + random.randint(-20, 20))
        sprites = get_asteroid_sprites((self.largura, self.altura))
        self.base_sprite = random.choice(sprites) if sprites else None
        self.origem = origin

    def atualizar(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angulo = (self.angulo + self.rot_vel * dt) % 360
        self.vx *= (1 - 0.25 * dt)
        self.vy = self.vy * (1 - 0.25 * dt) + (35 * SCALE) * dt
        self.sincronizar_retangulo()

    def desenhar(self, tela):
        if self.base_sprite is not None:
            img = pygame.transform.rotozoom(self.base_sprite, self.angulo, 1.0)
            rect = img.get_rect(center=(int(self.x), int(self.y)))
            tela.blit(img, rect.topleft)
        else:
            pygame.draw.circle(tela, self.cor, (int(self.x), int(self.y)), self.raio)

class GerenciadorDeDestrocos:
    def __init__(self):
        self.destrocos = []

    def criar(self, d: Destroco):
        self.destrocos.append(d)

    def atualizar(self, dt):
        for d in self.destrocos:
            d.atualizar(dt)
        self.destrocos = [d for d in self.destrocos if not d.esta_morto()]

    def desenhar(self, tela):
        for d in self.destrocos:
            d.desenhar(tela)

