import pygame
import random
import math
from src.settings import *

class PlanetStage:
    def __init__(self):
        self.active = False
        self.state = 'inactive' # inactive, entering, playing, leaving
        self.timer = 0.0
        
        # Configuração do Terreno
        self.segment_height = 20 * SCALE
        self.segments = [] # Lista de dicionários {'x': centro, 'w': largura_canion, 'y': pos_y}
        self.scroll_speed = 180 * SCALE
        self.traveled_distance = 0.0
        self.stage_length = 15000 * SCALE # Distância total da fase
        
        # Geração procedural
        self.current_width = LARGURA * 0.7
        self.current_x = LARGURA / 2
        self.target_x = LARGURA / 2
        self.noise_offset = 0.0
        
        # Nuvens de transição
        self.clouds = []
        
        # Cores (Paleta Rochosa)
        self.color_ground = (60, 50, 40) # Fundo escuro (abismo/chão distante)
        self.color_wall_top = (160, 140, 120) # Topo da parede (mais claro)
        self.color_wall_face = (100, 85, 70) # Face do penhasco (mais escuro)
        self.color_strata = (80, 65, 55) # Linhas de estratificação
        
    def start(self, entry_img=None):
        self.active = True
        self.state = 'entering'
        self.timer = 0.0
        self.segments = []
        self.traveled_distance = 0.0
        self.clouds = []
        self.entry_img = entry_img
        
        # Preenche segmentos iniciais
        self.current_x = LARGURA / 2
        self.current_width = LARGURA * 0.8
        
        num_segs = int(ALTURA / self.segment_height) + 5
        for i in range(num_segs):
            self._add_segment(y_start=ALTURA + i * self.segment_height)

    def _add_segment(self, y_start=None):
        if y_start is None:
            # Adiciona no topo (y negativo)
            last_y = self.segments[-1]['y'] if self.segments else 0
            y = last_y - self.segment_height
        else:
            y = y_start
            
        # Random walk suave para o centro do cânion
        change = math.sin(self.noise_offset) * 30 * SCALE
        self.noise_offset += 0.15
        
        # Mantém dentro da tela com margem
        self.target_x += random.uniform(-20, 20) * SCALE + change
        self.target_x = max(LARGURA * 0.2, min(LARGURA * 0.8, self.target_x))
        
        # Suaviza movimento
        self.current_x += (self.target_x - self.current_x) * 0.1
        
        # Largura do cânion varia levemente
        self.current_width = max(LARGURA * 0.3, min(LARGURA * 0.8, self.current_width + random.uniform(-10, 10)))
        
        self.segments.append({
            'x': self.current_x,
            'w': self.current_width,
            'y': y
        })

    def update(self, dt, player, invul_timer=0.0):
        self.timer += dt
        
        if self.state == 'entering':
            # Fase de reentrada (Zoom no planeta + Nuvens)
            # Nuvens começam a aparecer após 1s
            if self.timer > 0.8:
                self._update_clouds(dt, density=0.9, speed_mult=2.5)
            
            if self.timer > 3.5: # Tempo total de entrada aumentado
                self.state = 'playing'
                self.clouds = [] # Limpa nuvens de entrada
                self.entry_img = None
                
        elif self.state == 'playing':
            self.traveled_distance += self.scroll_speed * dt
            
            # Move segmentos para baixo
            for seg in self.segments:
                seg['y'] += self.scroll_speed * dt
                
            # Remove segmentos que saíram da tela (baixo)
            self.segments = [s for s in self.segments if s['y'] < ALTURA + 100]
            
            # Adiciona novos no topo
            while self.segments[-1]['y'] > -self.segment_height:
                self._add_segment()
                
            # Verifica colisão com paredes
            player_rect = player.retangulo
            hit = False
            for seg in self.segments:
                seg_rect = pygame.Rect(0, seg['y'], LARGURA, self.segment_height)
                if seg_rect.colliderect(player_rect):
                    left_wall = seg['x'] - seg['w']/2
                    right_wall = seg['x'] + seg['w']/2
                    if player.x < left_wall or player.x + player.largura > right_wall:
                        hit = True
                        break
            
            if hit and not invul_timer > 0:
                return True 
                
            # Fim da fase? (Reduzido para teste: 8000)
            if self.traveled_distance > 8000 * SCALE:
                self.state = 'leaving'
                self.timer = 0.0

        elif self.state == 'leaving':
            # Sobe de volta para o espaço (nuvens voltam)
            self._update_clouds(dt, density=0.8, speed_mult=2.5)
            # Acelera nave para cima visualmente
            player.y -= 100 * dt 
            if self.timer > 3.0:
                self.active = False
                return 'finished'
                
        return False

    def _update_clouds(self, dt, density, speed_mult):
        if random.random() < density:
            w = random.randint(100, 400)
            h = random.randint(50, 200)
            x = random.uniform(-100, LARGURA)
            y = -h
            speed = random.uniform(400, 800) * speed_mult
            alpha = random.randint(50, 150)
            self.clouds.append({'rect': pygame.Rect(x, y, w, h), 'speed': speed, 'alpha': alpha})
        for c in self.clouds:
            c['rect'].y += c['speed'] * dt
        self.clouds = [c for c in self.clouds if c['rect'].y < ALTURA]

    def draw(self, screen):
        # Se estiver entrando e tiver imagem, desenha o zoom do planeta
        if self.state == 'entering' and self.entry_img:
            # Efeito de Zoom: recorta uma área central da imagem original que diminui com o tempo
            # e estica para a tela inteira.
            
            # Duração do zoom: 3.5s
            # T vai de 0.0 a 1.0
            t = min(1.0, self.timer / 3.0)
            
            # Fator de zoom: começa mostrando 80% da imagem, termina mostrando 5% (zoom in extremo)
            start_scale = 0.8
            end_scale = 0.05
            current_scale = start_scale - (start_scale - end_scale) * (t ** 2) # t^2 para acelerar o zoom
            
            iw = self.entry_img.get_width()
            ih = self.entry_img.get_height()
            
            # Tamanho do recorte
            rw = int(iw * current_scale)
            rh = int(ih * current_scale)
            
            # Garante tamanho mínimo de 1px
            rw = max(1, rw)
            rh = max(1, rh)
            
            # Centro
            cx = iw // 2
            cy = ih // 2
            
            # Retângulo de recorte
            rect = pygame.Rect(cx - rw//2, cy - rh//2, rw, rh)
            
            try:
                sub = self.entry_img.subsurface(rect)
                scaled = pygame.transform.scale(sub, (LARGURA, ALTURA))
                screen.blit(scaled, (0, 0))
            except Exception:
                # Fallback se der erro no crop/scale
                screen.fill(self.color_ground)
        else:
            # Fundo normal (Abismo)
            screen.fill(self.color_ground)
        
        if self.state == 'playing' or self.state == 'leaving':
            # Desenha terreno
            # Para dar efeito 3D, vamos desenhar faixas horizontais para cada segmento
            # A "face" do penhasco é a diferença entre a largura do cânion e a borda da tela?
            # Não, a face é a parede vertical. Como é top-down 2D, simulamos a face desenhando
            # uma borda grossa interna com cor mais escura.
            
            sorted_segs = sorted(self.segments, key=lambda s: s['y'])
            
            for seg in sorted_segs:
                y = seg['y']
                h = self.segment_height + 2
                
                # Coordenadas
                lx = seg['x'] - seg['w']/2 # Borda esquerda do cânion
                rx = seg['x'] + seg['w']/2 # Borda direita do cânion
                
                # Desenha o TOPO da parede (área não jogável)
                # Esquerda: 0 até lx
                pygame.draw.rect(screen, self.color_wall_top, (0, y, lx, h))
                # Direita: rx até LARGURA
                pygame.draw.rect(screen, self.color_wall_top, (rx, y, LARGURA - rx, h))
                
                # Desenha detalhes de rocha/estratificação no topo
                if int(y / 40) % 2 == 0:
                    # Faixa levemente mais escura
                    cor_detalhe = (140, 120, 100)
                    pygame.draw.rect(screen, cor_detalhe, (0, y, lx, h))
                    pygame.draw.rect(screen, cor_detalhe, (rx, y, LARGURA - rx, h))

                # Desenha a FACE do penhasco (efeito de profundidade)
                # Uma faixa vertical na borda interna
                cliff_width = 15 * SCALE
                
                # Face Esquerda
                pygame.draw.rect(screen, self.color_wall_face, (lx - cliff_width, y, cliff_width, h))
                # Face Direita
                pygame.draw.rect(screen, self.color_wall_face, (rx, y, cliff_width, h))
                
                # Detalhes na face (rachaduras/sombras)
                if int(y / 20) % 3 == 0:
                    pygame.draw.rect(screen, self.color_strata, (lx - cliff_width, y + 5, cliff_width, 4))
                    pygame.draw.rect(screen, self.color_strata, (rx, y + 5, cliff_width, 4))

            # Desenha borda final para acabamento (linhas contínuas)
            if len(sorted_segs) > 1:
                pts_l = [(s['x'] - s['w']/2, s['y']) for s in sorted_segs]
                pts_r = [(s['x'] + s['w']/2, s['y']) for s in sorted_segs]
                pygame.draw.lines(screen, (50, 40, 30), False, pts_l, 2)
                pygame.draw.lines(screen, (50, 40, 30), False, pts_r, 2)

        # Nuvens
        for c in self.clouds:
            s = pygame.Surface((c['rect'].w, c['rect'].h), pygame.SRCALPHA)
            s.fill((255, 255, 255, c['alpha']))
            screen.blit(s, c['rect'])
            
        # Fade In/Out (Branco)
        if self.state == 'entering':
            # Fade out do branco inicial (flash da reentrada)
            # E depois fade in das nuvens/canyon?
            # Vamos fazer um fade branco que começa transparente, fica branco (pico do calor/nuvens) e depois clareia para o jogo
            
            # 0.0 -> 2.0: Zoom (sem fade branco, só plasma)
            # 2.0 -> 2.5: Fade to White (entrando nas nuvens)
            # 2.5 -> 3.5: Fade from White (saindo das nuvens para o canyon)
            
            if self.timer > 2.0:
                if self.timer < 2.8:
                    # Indo para branco
                    alpha = int(255 * (self.timer - 2.0) / 0.8)
                else:
                    # Voltando do branco
                    alpha = int(255 * (1.0 - (self.timer - 2.8) / 0.7))
                
                alpha = max(0, min(255, alpha))
                if alpha > 0:
                    fade = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
                    fade.fill((255, 255, 255, alpha))
                    screen.blit(fade, (0,0))
                    
        elif self.state == 'leaving':
            fade = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
            alpha = int(255 * min(1.0, self.timer / 2.5))
            fade.fill((255, 255, 255, alpha))
            screen.blit(fade, (0,0))
