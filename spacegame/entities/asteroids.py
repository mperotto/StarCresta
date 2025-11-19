import pygame, random, math
from spacegame.entities.base import ObjetoDeJogo
from spacegame.settings import S, SCALE
from spacegame.assets import get_asteroid_sprites

class Asteroide(ObjetoDeJogo):
    def __init__(self, x, y, velocidade=60, categoria=None):
        if categoria is None:
            categoria = random.choices(['small', 'med', 'big'], weights=[3, 2, 1])[0]
        self.categoria = categoria
        tamanho_por_cat = {'tiny': 16, 'small': 24, 'med': 32, 'big': 48}
        tam = tamanho_por_cat[self.categoria]
        super().__init__(x, y, S(tam), S(tam))
        self.velocidade = (velocidade * SCALE) * (0.9 if categoria=='big' else 1.0)
        self.angulo = random.uniform(0, 360)
        self.rot_vel = random.uniform(-90, 90)
        sprites = get_asteroid_sprites((self.largura, self.altura))
        self.base_sprite = random.choice(sprites) if sprites else None

    def mover(self, dt):
        self.y += self.velocidade * dt
        self.angulo = (self.angulo + self.rot_vel * dt) % 360

    def atualizar(self, dt):
        self.mover(dt)
        self.sincronizar_retangulo()

    def receber_dano(self, dano=1):
        ordem = ['tiny', 'small', 'med', 'big']
        idx = ordem.index(self.categoria)
        if idx > 0:
            self.categoria = ordem[idx-1]
            novo_tam = {'tiny': 16, 'small': 24, 'med': 32, 'big': 48}[self.categoria]
            cx, cy = self.x + self.largura/2, self.y + self.altura/2
            self.largura = self.altura = S(novo_tam)
            self.retangulo.size = (self.largura, self.altura)
            self.x, self.y = cx - self.largura/2, cy - self.altura/2
            sprites = get_asteroid_sprites((self.largura, self.altura))
            self.base_sprite = random.choice(sprites) if sprites else None
            self.sincronizar_retangulo()
        else:
            self.matar()

    def desenhar(self, tela):
        if self.base_sprite is not None:
            img = pygame.transform.rotozoom(self.base_sprite, self.angulo, 1.0)
            rect = img.get_rect(center=(int(self.x + self.largura/2), int(self.y + self.altura/2)))
            tela.blit(img, rect.topleft)
        else:
            pygame.draw.circle(tela, (160, 160, 160), (int(self.x + self.largura/2), int(self.y + self.altura/2)), self.largura//2)

