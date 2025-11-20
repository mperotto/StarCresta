import pygame
import math
import random
from src.settings import *
from src.sprites.enemy import Inimigo, TiroInimigo
from src.assets import carregar_sprite_boss

class Boss(Inimigo):
    def __init__(self, x, y):
        # Boss grande e resistente
        super().__init__(x, y, largura=128, altura=128, vida=400, cor=(100, 0, 100))
        self.sprite = carregar_sprite_boss(self.largura, self.altura)
        self.estado = 'entrando' # entrando, ocioso, atacando
        self.tempo_estado = 0.0
        self.alvo_y = 80
        self.velocidade_x = 100 * SCALE
        self.direcao_x = 1
        
        # Sistema de ataque
        self.cd_ataque = 2.0
        self.padrao_atual = 0
        
        # Animação de inclinação (banking)
        self.angulo = 0.0
        self.max_angulo = 15.0
        self.vel_angular = 60.0
        
        # Visual hit feedback
        self.hit_flash = 0.0
        
        # Enrage quando vida baixa
        self.enraged = False
        
    def mover(self, dt):
        self.tempo_estado += dt
        
        # Diminui o flash de hit
        if self.hit_flash > 0:
            self.hit_flash = max(0.0, self.hit_flash - dt)
        
        target_angle = 0.0
        
        # Modifica velocidade se enraged
        vel_mult = 1.5 if self.enraged else 1.0
        
        if self.estado == 'entrando':
            # Desce suavemente até a posição de combate
            if self.y < self.alvo_y:
                self.y += 60 * dt * SCALE
            else:
                self.estado = 'ocioso'
                self.tempo_estado = 0.0
                
        elif self.estado == 'ocioso':
            # Move de um lado para o outro
            self.x += self.velocidade_x * vel_mult * self.direcao_x * dt
            if self.x <= 0 or self.x + self.largura >= LARGURA:
                self.direcao_x *= -1
                self.x = max(0, min(LARGURA - self.largura, self.x))
            
            # Inclina na direção do movimento
            # Se move para direita (1), inclina para direita (-angulo em pygame)
            target_angle = -self.max_angulo * self.direcao_x
                
            # Decide atacar periodicamente (mais rápido se enraged)
            intervalo_ataque = 1.0 if self.enraged else 1.5
            if self.tempo_estado > intervalo_ataque:
                self.estado = 'atacando'
                self.tempo_estado = 0.0
                self.padrao_atual = random.randint(0, 2) # 0: Spread, 1: Laser/Rápido, 2: Chuva
                
        elif self.estado == 'atacando':
            # Continua movendo enquanto ataca (ou para, dependendo do design)
            # Vamos fazer ele parar para atacar em alguns padrões
            if self.padrao_atual != 1: # Se não for o ataque rápido, move devagar
                self.x += (self.velocidade_x * 0.3 * vel_mult) * self.direcao_x * dt
                if self.x <= 0 or self.x + self.largura >= LARGURA:
                    self.direcao_x *= -1
                target_angle = -self.max_angulo * 0.3 * self.direcao_x
            else:
                target_angle = 0.0
            
            # Volta a ocioso após um tempo de ataque (mais rápido se enraged)
            duracao_ataque = 2.0 if self.enraged else 3.0
            if self.tempo_estado > duracao_ataque:
                self.estado = 'ocioso'
                self.tempo_estado = 0.0

        # Atualiza ângulo suavemente
        diff = target_angle - self.angulo
        if abs(diff) > 0.1:
            change = self.vel_angular * dt
            if abs(diff) < change:
                self.angulo = target_angle
            else:
                self.angulo += change * (1 if diff > 0 else -1)

    def tentar_atirar(self, gerenciador_tiros, jogador, asteroides, dif_mult=1.0):
        if self.estado != 'atacando':
            return

        self.cd_ataque -= 0.016 # Aproximação de dt, idealmente passaria dt aqui
        if self.cd_ataque <= 0:
            # Reduz cooldown se enraged
            cd_mult = 0.5 if self.enraged else 1.0
            if self.padrao_atual == 0:
                self._ataque_spread(gerenciador_tiros)
                self.cd_ataque = 0.8 * cd_mult # Intervalo entre disparos do spread
            elif self.padrao_atual == 1:
                self._ataque_direto(gerenciador_tiros, jogador)
                self.cd_ataque = 0.4 * cd_mult
            elif self.padrao_atual == 2:
                self._ataque_chuva(gerenciador_tiros)
                self.cd_ataque = 0.2 * cd_mult
    
    def receber_dano(self, quantidade):
        super().receber_dano(quantidade)
        # Flash visual ao receber dano
        self.hit_flash = 0.1
        
        # Ativa enrage se vida < 10%
        if not self.enraged and self.vida <= self.vida_max * 0.1:
            self.enraged = True

    def _ataque_spread(self, gerenciador_tiros):
        # Dispara leque de tiros
        cx = self.x + self.largura/2
        cy = self.y + self.altura
        angulos = [-30, -15, 0, 15, 30]
        for ang in angulos:
            rad = math.radians(ang + self.angulo) # Ajusta tiro com a inclinação
            vx = 200 * math.sin(rad)
            vy = 200 * math.cos(rad)
            gerenciador_tiros.criar(TiroInimigo(cx, cy, vx=vx, vy=vy))

    def _ataque_direto(self, gerenciador_tiros, jogador):
        # Tiro rápido na direção do jogador
        cx = self.x + self.largura/2
        cy = self.y + self.altura
        dx = (jogador.x + jogador.largura/2) - cx
        dy = (jogador.y + jogador.altura/2) - cy
        dist = math.hypot(dx, dy)
        if dist > 0:
            vx = (dx / dist) * 350
            vy = (dy / dist) * 350
            gerenciador_tiros.criar(TiroInimigo(cx, cy, vx=vx, vy=vy))

    def _ataque_chuva(self, gerenciador_tiros):
        # Tiros para cima que caem (simulado com tiros lentos ou espalhados)
        # Vamos fazer tiros aleatórios para baixo
        cx = self.x + random.uniform(0, self.largura)
        cy = self.y + self.altura
        gerenciador_tiros.criar(TiroInimigo(cx, cy, vx=random.uniform(-50, 50), vy=250))

    def desenhar(self, tela):
        # Desenha sprite rotacionado
        if self.sprite:
            sprite_rot = pygame.transform.rotate(self.sprite, self.angulo)
            
            # Aplica efeito de flash ao receber dano (respeitando transparência)
            if self.hit_flash > 0:
                # Usa máscara para criar uma silhueta vermelha perfeita
                mask = pygame.mask.from_surface(sprite_rot)
                intensity = int(100 * (self.hit_flash / 0.1))
                # Cria surface vermelha onde a máscara está setada (opaca) e transparente onde não está
                # setcolor=(R, G, B, A) -> Vermelho com alpha total
                flash_overlay = mask.to_surface(setcolor=(intensity, 0, 0, 255), unsetcolor=(0, 0, 0, 0))
                # Adiciona o vermelho ao sprite original
                sprite_rot.blit(flash_overlay, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            
            rect_rot = sprite_rot.get_rect(center=(self.x + self.largura/2, self.y + self.altura/2))
            tela.blit(sprite_rot, rect_rot.topleft)
        else:
            super().desenhar(tela)
            
        # Barra de vida do Boss (grande no topo ou em cima dele)
        # Vamos desenhar em cima dele
        w = self.largura
        h = 8
        x = self.x
        y = self.y - 12
        pct = max(0.0, self.vida / self.vida_max)
        # Cor da barra muda se enraged
        cor_vida = (255, 50, 50) if self.enraged else (200, 0, 50)
        pygame.draw.rect(tela, (60, 0, 0), (x, y, w, h))
        pygame.draw.rect(tela, cor_vida, (x, y, w * pct, h))
        pygame.draw.rect(tela, (255, 255, 255), (x, y, w, h), 1)
