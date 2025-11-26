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

class TiroPlaneta(ObjetoDeJogo):
    def __init__(self, x, y, player_x, player_y, ground_speed=0):
        # Começa como 1 pixel
        super().__init__(x, y, 1, 1)
        
        # Alvo e velocidades
        self.ground_vy = ground_speed
        
        # Vetor base de perseguição
        dx = player_x - x
        dy = player_y - y
        dist = math.hypot(dx, dy)
        
        # Velocidade inicial mais alta para permitir o "arco"
        max_speed = 350 * SCALE
        if dist > 0:
            self.vx_base = (dx / dist) * max_speed
            # Lança um pouco para cima (negativo Y) para criar o arco
            self.vy_base = ((dy / dist) * max_speed) - (100 * SCALE)
        else:
            self.vx_base = 0
            self.vy_base = max_speed
            
        self.target_r = S(6) # Tamanho final
        self.current_r = 1.0
        
        # Controle de profundidade (Z)
        self.z = 0.0 
        # Zoom bem lento e progressivo
        self.z_speed = 0.02 
        self.z_accel = 0.15
        
        # Gravidade simulada na tela (faz o tiro cair/curvar)
        self.gravity = 180 * SCALE
        
        self.dangerous = False
        self.cor = (255, 60, 60)

    def atualizar(self, dt):
        # Atualiza profundidade
        if self.z < 1.0:
            self.z_speed += self.z_accel * dt
            self.z += self.z_speed * dt
            if self.z >= 1.0:
                self.z = 1.0
                self.dangerous = True
        else:
            self.dangerous = True
            
        # Tamanho baseado no Z
        self.current_r = 1.0 + (self.target_r - 1.0) * self.z
        
        # Perspectiva
        perspective_factor = 0.1 + 0.9 * (self.z ** 2)
        
        # Aplica gravidade na velocidade base Y (cria o arco)
        self.vy_base += self.gravity * dt
        
        # Movimento
        self.x += self.vx_base * perspective_factor * dt
        self.y += (self.ground_vy + self.vy_base * perspective_factor) * dt
        
        # Atualiza hitbox
        d = int(self.current_r * 2)
        self.largura = d
        self.altura = d
        
        if self.y > ALTURA + self.altura or self.x < -self.largura or self.x > LARGURA + self.largura or self.y < -self.altura:
            self.matar()
        self.sincronizar_retangulo()

    def desenhar(self, tela):
        # Alpha/Cor baseado na profundidade
        if self.z < 0.2:
            cor = (60, 10, 10)
        elif not self.dangerous:
            f = (self.z - 0.2) / 0.65
            f = max(0.0, min(1.0, f))
            r = int(60 + (255 - 60) * f)
            g = int(10 + (60 - 10) * f)
            b = int(10 + (60 - 10) * f)
            cor = (r, g, b)
        else:
            cor = self.cor
            
        cx, cy = int(self.retangulo.centerx), int(self.retangulo.centery)
        r = max(1, int(self.current_r))
        
        pygame.draw.circle(tela, cor, (cx, cy), r)
        
        if self.dangerous:
            pygame.draw.circle(tela, (255, 200, 200), (cx, cy), max(1, int(r * 0.5)))
