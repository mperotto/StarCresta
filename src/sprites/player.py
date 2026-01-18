import pygame
from src.settings import *
from src.sprites.base import ObjetoDeJogo
from src.sprites.projectile import Tiro, SuperTiro
from src.assets import carregar_sprite_nave

class TargetModule(ObjetoDeJogo):
    def __init__(self, x, y, stage_target):
        # stage_target: 2 ou 3 (qual parte é essa)
        super().__init__(x, y, S(36), S(24))
        self.stage_target = stage_target
        self.sprite = carregar_sprite_nave(self.largura, self.altura)
        # Modifica a cor para diferenciar (tint)
        self.sprite.fill((50, 50, 100), special_flags=pygame.BLEND_RGB_ADD) 
        self.vx = 220 * SCALE
        self.vy = 90 * SCALE
        self.vy_boost = 26 * SCALE
        self.vy_max = 260 * SCALE
        self.retro_power = 260 * SCALE
        self.retro_used = False
        self.stop_sway = False
        self.straight_threshold = ALTURA - S(280)
        self.retro_floor = ALTURA * 0.45
        self.direcao_x = 1
        faixa_horizontal = S(360)
        margem = S(40)
        self.x_min = max(margem, x - faixa_horizontal / 2)
        self.x_max = min(LARGURA - self.largura - margem, x + faixa_horizontal / 2)
        if self.x_max <= self.x_min:
            self.x_max = min(LARGURA - self.largura - margem, self.x_min + self.largura + S(20))
        self.x = max(self.x_min, min(self.x_max - self.largura, x))
        self.tempo = 0.0
        
    def atualizar(self, dt):
        self.tempo += dt
        if not self.stop_sway:
            self.x += self.vx * self.direcao_x * dt
            bateu = False
            if self.x <= self.x_min:
                self.x = self.x_min
                self.direcao_x = 1
                bateu = True
            elif self.x + self.largura >= self.x_max:
                self.x = self.x_max - self.largura
                self.direcao_x = -1
                bateu = True
            if bateu:
                self.vy = min(self.vy + self.vy_boost, self.vy_max)

        if self.retro_used and self.y >= self.straight_threshold:
            self.stop_sway = True

        # Acelera a descida a cada borda atingida, mas desacelera perto do acoplamento
        velocidade_y = self.vy
        zona_lenta_inicio = ALTURA - S(260)
        zona_lenta_fim = ALTURA - S(120)
        if self.y >= zona_lenta_inicio:
            progresso = min(1.0, max(0.0, (self.y - zona_lenta_inicio) / max(1.0, (zona_lenta_fim - zona_lenta_inicio))))
            fator_lento = max(0.35, 1.0 - 0.65 * progresso)
            velocidade_y *= fator_lento

        self.y += velocidade_y * dt
        self.sincronizar_retangulo()

    def aplicar_retro(self, dt):
        # sobe um pouco e habilita descida mais controlada (sem balanço) após uso
        self.retro_used = True
        self.y = max(self.retro_floor, self.y - self.retro_power * dt)
        self.vy = max(self.vy * 0.65, 40 * SCALE)
        
    def desenhar(self, tela):
        tela.blit(self.sprite, self.retangulo.topleft)
        # Desenha um indicador de "dock"
        pygame.draw.rect(tela, (0, 255, 0), self.retangulo, 1)

class Jogador(ObjetoDeJogo):
    def __init__(self, x, y):
        super().__init__(x, y, S(36), S(24))
        self.tempo_recarga = 0.0
        self.sprite = carregar_sprite_nave(self.largura, self.altura)
        self.spawn_anim = 0.0
        self.coletou_shield = False
        self.nivel_arma = 0  # 0-3, afeta o número de tiros
        self.stage = 1 # 1, 2, 3 (número de partes acopladas)
        self.sprites_parts = [self.sprite] # Lista de sprites para cada estágio

    def atualizar(self, dt):
        if self.spawn_anim > 0.0:
            alvo_y = ALTURA - S(80)
            # Sobe a nave até o alvo (y diminui para subir na tela)
            if self.y > alvo_y:
                self.y = max(alvo_y, self.y - S(140) * dt)
            self.spawn_anim = max(0.0, self.spawn_anim - dt)
        else:
            teclas = pygame.key.get_pressed()
            dx = (teclas[pygame.K_RIGHT] - teclas[pygame.K_LEFT]) * VELOCIDADE_JOGADOR * dt
            dy = (teclas[pygame.K_DOWN] - teclas[pygame.K_UP]) * VELOCIDADE_JOGADOR * dt
            self.x = max(0, min(LARGURA - self.largura, self.x + dx))
            self.y = max(0, min(ALTURA - self.altura, self.y + dy))
        self.tempo_recarga = max(0, self.tempo_recarga - dt)
        
        # Atualiza dimensões baseado no estágio
        target_h = S(24) * self.stage
        if self.altura != target_h:
            self.altura = target_h
            
        self.sincronizar_retangulo()

    def desenhar(self, tela):
        h_parte = S(24)
        for i in range(self.stage):
            spr = self.sprites_parts[0]
            pos_y = self.y + i * h_parte
            tela.blit(spr, (self.x, pos_y))

    def get_segment_rects(self):
        h_parte = S(24)
        rects = []
        for i in range(self.stage):
            r = pygame.Rect(int(self.x), int(self.y + i * h_parte), self.largura, h_parte)
            rects.append(r)
        return rects

    def pode_atirar(self): return self.tempo_recarga <= 0
    
    def atirar(self):
        self.tempo_recarga = 0.1
        tiros = []
        
        if self.stage == 1:
            tiros.append(Tiro(self.x + self.largura/2 - 3, self.y - 12))
        elif self.stage == 2:
            tiros.append(Tiro(self.x + self.largura/2 - 10, self.y - 12))
            tiros.append(Tiro(self.x + self.largura/2 + 4, self.y - 12))
        elif self.stage == 3:
            tiros.append(Tiro(self.x + self.largura/2 - 3, self.y - 12))
            t_esq = Tiro(self.x + self.largura/2 - 14, self.y - 8)
            t_dir = Tiro(self.x + self.largura/2 + 8, self.y - 8)
            tiros.append(t_esq)
            tiros.append(t_dir)
            
        return tiros

    def atirar_super(self):
        # recarga padrão do super; pode ser zerada externamente se precisar
        self.tempo_recarga = 0.8
        return SuperTiro(self.x + self.largura/2 - 12, self.y - 18)

    def receber_dano(self):
        """Retorna True se perdeu vida, False se apenas perdeu estágio"""
        if self.stage > 1:
            self.stage -= 1
            return False
        return True
