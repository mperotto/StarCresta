import pygame
import random
import math
from src.settings import *
from src.sprites.base import ObjetoDeJogo
from src.assets import carregar_sprite_powerup, carregar_sprites_asteroide_opcoes, carregar_sprite_powerup_vida

class Upgrade(ObjetoDeJogo):
    def __init__(self, x, y, velocidade=90, tipo='v'):
        super().__init__(x, y, S(18), S(18))
        self.velocidade = velocidade * SCALE
        self.cor = (140, 200, 255)
        self.tipo = tipo  # 'v', 'shield', 'health', 'laser'
        self.label = tipo.upper()[:1]
        if tipo == 'health':
            self.base_color = (120, 255, 160)
            self.glow_color = (80, 200, 120)
        elif tipo == 'shield':
            self.base_color = (120, 200, 255)
            self.glow_color = (80, 150, 220)
        elif tipo == 'laser':
            self.base_color = (255, 120, 230)
            self.glow_color = (200, 70, 200)
        else:  # 'v' padrão
            self.base_color = (255, 200, 80)
            self.glow_color = (220, 140, 40)
        
        # escolhe sprite por tipo
        if tipo == 'health':
            self.sprite = carregar_sprite_powerup_vida(self.largura, self.altura)
        else:
            self.sprite = carregar_sprite_powerup(self.largura, self.altura)

    def atualizar(self, dt):
        self.y += self.velocidade * dt
        if self.y > ALTURA:
            self.matar()
        self.sincronizar_retangulo()

    def desenhar(self, tela):
        cx = int(self.retangulo.centerx)
        cy = int(self.retangulo.centery)
        # glow suave pulsante para health, mais discreto para outros
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.008)
        glow_r = max(self.largura, self.altura)//2 + 6
        alpha = int(80 + 60 * pulse) if self.tipo == 'health' else 60
        try:
            surf = pygame.Surface((glow_r*2+4, glow_r*2+4), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*self.glow_color, alpha), (glow_r+2, glow_r+2), glow_r)
            tela.blit(surf, (cx - glow_r - 2, cy - glow_r - 2))
        except Exception:
            pygame.draw.circle(tela, self.glow_color, (cx, cy), glow_r)
        # corpo
        if self.sprite is not None and self.tipo == 'health':
            tela.blit(self.sprite, self.retangulo.topleft)
        else:
            pygame.draw.rect(tela, self.base_color, self.retangulo, border_radius=4)
        # letra identificadora
        try:
            fonte = pygame.font.SysFont(None, 16)
            txt = fonte.render(self.label, True, (20, 20, 30))
            tela.blit(txt, txt.get_rect(center=(cx, cy)))
        except Exception:
            pass

class Destroco(ObjetoDeJogo):
    def __init__(self, x, y, raio=6, vx=0.0, vy=0.0, origin='env'):
        r = int(round(raio * SCALE))
        r = max(1, r)
        super().__init__(x, y, int(r*2), int(r*2))
        self.raio = int(r)
        self.vx = float(vx)
        self.vy = float(vy)
        self.angulo = random.uniform(0, 360)
        self.rot_vel = random.uniform(-180, 180)
        self.cor = (150 + random.randint(-20, 20), 140 + random.randint(-20, 20), 130 + random.randint(-20, 20))
        # poder do fragmento: maior raio => mais dano
        self.poder = 1 if self.raio < 10 else (2 if self.raio < 15 else 3)
        # sprite opcional (meteoro), escalado ao diâmetro
        sprites = carregar_sprites_asteroide_opcoes(self.largura, self.altura)
        self.base_sprite = random.choice(sprites) if sprites else None
        # origem: 'player' faz dano em inimigos, 'env' não
        self.origem = origin

    def atualizar(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angulo = (self.angulo + self.rot_vel * dt) % 360
        # leve desaceleração, mas nunca parar totalmente; viés para baixo
        self.vx *= (1 - 0.25 * dt)
        self.vy = self.vy * (1 - 0.25 * dt) + (35 * SCALE) * dt
        # velocidade mínima para sair da tela
        if abs(self.vx) < 8*SCALE: self.vx = (8*SCALE) if self.vx >= 0 else -(8*SCALE)
        if abs(self.vy) < 20*SCALE: self.vy = 20*SCALE
        # só somem fora da tela
        if (self.y > ALTURA + self.raio) or (self.y < -self.raio) or (self.x < -self.raio) or (self.x > LARGURA + self.raio):
            self.matar()
        self.sincronizar_retangulo()

    def desenhar(self, tela):
        if self.base_sprite is not None:
            img = pygame.transform.rotozoom(self.base_sprite, self.angulo, 1.0)
            rect = img.get_rect(center=(int(self.x), int(self.y)))
            tela.blit(img, rect.topleft)
        else:
            pygame.draw.circle(tela, self.cor, (int(self.x), int(self.y)), self.raio)
