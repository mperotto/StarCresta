import pygame
import math
import random
from abc import ABC, abstractmethod
from src.settings import *
from src.sprites.base import ObjetoDeJogo
from src.sprites.projectile import TiroInimigo
from src.assets import (
    carregar_sprite_inimigo_a, 
    carregar_sprite_inimigo_b, 
    carregar_sprites_asteroide_opcoes
)

# Forward declaration to avoid circular import in type hinting if needed, 
# but Python handles it dynamically. We'll use 'GerenciadorDeTirosInimigos' string.

class Inimigo(ObjetoDeJogo, ABC):
    def __init__(self, x, y, largura=28, altura=20, vida=1, cor=(255, 120, 120)):
        super().__init__(x, y, S(largura), S(altura))
        self.vida = vida
        self.vida_max = vida
        self.cor = cor

    @abstractmethod
    def mover(self, dt): ...

    def atualizar(self, dt):
        self.mover(dt)
        if self.y > ALTURA:  # saiu da tela
            self.matar()
        self.sincronizar_retangulo()

    def desenhar(self, tela):
        sprite = getattr(self, 'sprite', None)
        if sprite is not None:
            tela.blit(sprite, self.retangulo.topleft)
        else:
            pygame.draw.rect(tela, self.cor, self.retangulo)
        # barra de vida para inimigos com mais de 1 de vida
        if self.vida_max > 1 and self.vida < self.vida_max and self.vivo:
            w = self.largura
            h = 4
            x = int(self.x)
            y = int(self.y) - 6
            # fundo
            pygame.draw.rect(tela, (100, 40, 40), pygame.Rect(x, y, w, h))
            # preenchimento
            pct = max(0.0, min(1.0, self.vida / self.vida_max))
            pygame.draw.rect(tela, (60, 220, 90), pygame.Rect(x, y, int(w * pct), h))
        # escudo visual se ativo
        if hasattr(self, 'shield_timer') and self.shield_timer > 0 and self.vivo:
            cx = int(self.x + self.largura/2)
            cy = int(self.y + self.altura/2)
            r = max(self.largura, self.altura)//2 + 2
            pygame.draw.circle(tela, (120, 200, 255), (cx, cy), int(r), 2)

    def receber_dano(self, dano=1):
        self.vida -= dano
        if self.vida <= 0:
            self.matar()

    # upgrades padrão: inimigo pode ter shield e vshot
    def coletar_upgrade(self, tipo):
        if tipo == 'shield':
            setattr(self, 'shield_timer', 10.0)
        elif tipo == 'v':
            setattr(self, 'vshot_timer', 10.0)

class InimigoDescendo(Inimigo):
    def __init__(self, x, y, velocidade=90):
        super().__init__(x, y, vida=1, cor=(250, 90, 90))
        self.velocidade = velocidade * SCALE
        self.sprite = carregar_sprite_inimigo_a(self.largura, self.altura)

    def mover(self, dt):
        self.y += self.velocidade * dt

class InimigoZigueZague(Inimigo):
    def __init__(self, x, y, velocidade=80, amplitude=60, frequencia=3.0):
        super().__init__(x, y, vida=2, cor=(255, 170, 90))
        self.velocidade = velocidade * SCALE
        self.amplitude = amplitude * SCALE
        self.frequencia = frequencia
        self.tempo = 0.0
        self.x_inicial = x
        self.sprite = carregar_sprite_inimigo_b(self.largura, self.altura)

    def mover(self, dt):
        self.tempo += dt
        self.y += self.velocidade * dt
        self.x = self.x_inicial + self.amplitude * math.sin(self.tempo * self.frequencia)

class InimigoAtirador(Inimigo):
    def __init__(self, x, y, velocidade=70):
        super().__init__(x, y, largura=28, altura=22, vida=3, cor=(255, 120, 200))
        self.velocidade = velocidade * SCALE
        self.tempo = 0.0
        # cadência base aleatória por inimigo; será ajustada por dificuldade
        self.cd_tiro_base = random.uniform(0.6, 1.1)
        self.shoot_timer = 0.0
        self.sprite = carregar_sprite_inimigo_b(self.largura, self.altura)
        self.shield_timer = 0.0
        self.vshot_timer = 0.0

    def mover(self, dt):
        self.y += self.velocidade * dt
        self.shoot_timer += dt
        if self.shield_timer > 0:
            self.shield_timer = max(0.0, self.shield_timer - dt)
        if self.vshot_timer > 0:
            self.vshot_timer = max(0.0, self.vshot_timer - dt)

    def tentar_atirar(self, tiros_inimigos, jogador, asteroides: list, dif_mult: float = 1.0):
        # quanto maior dif_mult, mais rápida (menor intervalo). Mantém um piso para não virar metralhadora.
        effective_cd = max(0.22, self.cd_tiro_base / max(0.1, dif_mult))
        if self.shoot_timer < effective_cd:
            return
        self.shoot_timer = 0.0
        # alvo: 70% jogador, 30% asteroide próximo (com ruído para reduzir precisão)
        alvo_x, alvo_y = jogador.x + jogador.largura/2, jogador.y + jogador.altura/2
        if asteroides and random.random() < 0.3:
            a = min(asteroides, key=lambda a: (a.y - self.y)**2 + (a.x - self.x)**2)
            alvo_x, alvo_y = a.x + a.largura/2, a.y + a.altura/2
        # ruído na mira para evitar acertos inevitáveis
        alvo_x += random.uniform(-100, 100)
        alvo_y += random.uniform(-60, 60)
        # calcula vetores a partir do topo do inimigo
        cx = self.x + self.largura/2
        topy = self.y + self.altura
        dx = alvo_x - cx
        dy = max(20.0, alvo_y - topy)
        mag = (dx*dx + dy*dy) ** 0.5
        # velocidade base do projétil, levemente escalada pela dificuldade (até ~+30%)
        speed = 240.0 * SCALE * (1.0 + 0.1 * (max(1.0, dif_mult) - 1.0))
        vx, vy = dx/mag*speed, dy/mag*speed
        padrao = [-math.radians(10), 0.0, +math.radians(10)] if self.vshot_timer > 0 else [0.0]
        for ang in padrao:
            svx = vx*math.cos(ang) - vy*math.sin(ang)
            svy = vx*math.sin(ang) + vy*math.cos(ang)
            tiros_inimigos.criar(TiroInimigo(cx-2, topy, vx=svx, vy=svy))

    def receber_dano(self, dano=1):
        if self.shield_timer > 0:
            return
        super().receber_dano(dano)

class DiscoVoador(Inimigo):
    def __init__(self, x, y, velocidade=380, direcao=1):
        # OVNI rápido que cruza a tela na horizontal e atira
        super().__init__(x, y, largura=34, altura=18, vida=3, cor=(200, 180, 255))
        self.velocidade = velocidade * SCALE
        self.direcao = 1 if direcao >= 0 else -1
        self.shoot_timer = 0.0
        self.cd_tiro_base = 0.42
        # sprite simples em forma de disco (ellipse)
        try:
            surf = pygame.Surface((self.largura, self.altura), pygame.SRCALPHA)
            pygame.draw.ellipse(surf, (200, 190, 255), (0, 2, self.largura, self.altura-4))
            pygame.draw.ellipse(surf, (120, 110, 200), (0, 2, self.largura, self.altura-4), 2)
            pygame.draw.ellipse(surf, (255, 255, 255), (self.largura//2-6, 0, 12, 8))
            self.sprite = surf
        except Exception:
            self.sprite = None

    def mover(self, dt):
        self.x += self.direcao * self.velocidade * dt
        self.shoot_timer += dt
        if self.x < -self.largura - 8 or self.x > LARGURA + 8:
            self.matar()

    def tentar_atirar(self, tiros_inimigos, jogador, asteroides: list, dif_mult: float = 1.0):
        # dispara rajadas rápidas para baixo em direção aproximada ao jogador
        cd = max(0.14, self.cd_tiro_base / max(0.1, dif_mult))
        if self.shoot_timer < cd:
            return
        self.shoot_timer = 0.0
        cx = self.x + self.largura/2
        cy = self.y + self.altura
        # mira com leve imprecisão
        alvo_x = jogador.x + jogador.largura/2 + random.uniform(-100, 100)
        alvo_y = jogador.y + jogador.altura/2 + random.uniform(-40, 60)
        dx = max(-400, min(400, alvo_x - cx))
        dy = max(20.0, alvo_y - cy)
        mag = (dx*dx + dy*dy) ** 0.5
        # leve aumento com dificuldade (até ~+30%)
        speed = 260.0 * SCALE * (1.0 + 0.1 * (max(1.0, dif_mult) - 1.0))
        vx, vy = dx/mag*speed, dy/mag*speed
        # dispara apenas 1 projétil (menos pressão)
        off = 0.0
        svx = vx*math.cos(off) - vy*math.sin(off)
        svy = vx*math.sin(off) + vy*math.cos(off)
        tiros_inimigos.criar(TiroInimigo(cx-2, cy, vx=svx, vy=svy))

class Asteroide(Inimigo):
    def __init__(self, x, y, velocidade=60, categoria=None):
        # categorias: 'tiny','small','med','big'
        if categoria is None:
            categoria = random.choices(['small', 'med', 'big'], weights=[3, 2, 1])[0]
        self.categoria = categoria
        tamanho_por_cat = {'tiny': 16, 'small': 24, 'med': 32, 'big': 48}
        tam = tamanho_por_cat[self.categoria]
        super().__init__(x, y, largura=tam, altura=tam, vida=1, cor=(180, 160, 140))
        self.velocidade = (velocidade * SCALE) * (0.9 if categoria=='big' else 1.0)
        self.angulo = random.uniform(0, 360)
        self.rot_vel = random.uniform(-90, 90)
        sprites = carregar_sprites_asteroide_opcoes(self.largura, self.altura)
        self.base_sprite = random.choice(sprites) if sprites else None

    def mover(self, dt):
        self.y += self.velocidade * dt
        self.angulo = (self.angulo + self.rot_vel * dt) % 360

    def receber_dano(self, dano=1):
        # ao ser atingido, reduz categoria (big->med->small->tiny), só morre no tiny
        ordem = ['tiny', 'small', 'med', 'big']
        idx = ordem.index(self.categoria)
        if idx > 0:
            # encolhe uma categoria
            self.categoria = ordem[idx-1]
            novo_tam = {'tiny': 16, 'small': 24, 'med': 32, 'big': 48}[self.categoria]
            cx, cy = self.x + self.largura/2, self.y + self.altura/2
            self.largura = self.altura = novo_tam
            self.retangulo.size = (novo_tam, novo_tam)
            self.x, self.y = cx - novo_tam/2, cy - novo_tam/2
            # atualiza sprite escalado
            sprites = carregar_sprites_asteroide_opcoes(self.largura, self.altura)
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
