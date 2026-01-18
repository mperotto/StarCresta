import pygame
import random
import math
import os
from src.settings import *
from src.assets import get_resource_path

# Renderer 3D (opcional, fallback se não disponível)
try:
    from src.core.renderer3d import Renderer3D
    HAS_3D_RENDERER = True
except ImportError as e:
    HAS_3D_RENDERER = False
    print(f"[PlanetStage] FALHA IMPORT Renderer3D: {e}")
    # Opcional: imprimir traceback se quiser ver dependências profundas
    import traceback
    traceback.print_exc()
except Exception as e:
    HAS_3D_RENDERER = False
    print(f"[PlanetStage] ERRO GENÉRICO Renderer3D: {e}")
    import traceback
    traceback.print_exc()

class PlanetStage:
    def __init__(self):
        self.active = False
        self.state = 'inactive' # inactive, entering, descending, playing, leaving
        self.timer = 0.0
        
        # Configuração do Terreno
        self.segment_height = 20 * SCALE
        self.segments = [] # Lista de dicionários {'x': centro, 'w': largura_canion, 'y': pos_y}
        self.scroll_speed = 0.0 # Começa parado (controle manual A/Z)
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
        self.use_3d = True
        self.cam_x = LARGURA / 2
        self.cam_y = 300 * SCALE # Começa alto
        self.cam_z = 0.0
        self.pitch_angle = -400.0 # Angulo inicial do nariz (olhando para o horizonte/chão)
        self.banking = 0.0 # Ângulo de inclinação (radianos)
        self.fov = 0.9
        self.jitter_amp = 48 * SCALE
        self.jitter_freq = 0.08
        self.noise_seed_l = random.uniform(0, 1000)
        self.noise_seed_r = random.uniform(0, 1000)
        self.window_rects = []
        self.window_edges = []
        self.plasma_surface = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        self._cockpit_size = None
        self.plasma_streaks = []
        self._plasma_prev_tick = pygame.time.get_ticks()
        self.shot_traces = []
        
        # Renderer 3D para fase de descida
        self.renderer3d = None
        self.descent_surface = None
        self.planet_model_path = None
        self.renderer3d_error = None
        self._init_3d_renderer()
        try:
            # Carrega imagem que já possui transparência (alpha channel)
            pth = get_resource_path(os.path.join('assets', 'cockpit_transparent.png'))
            self.cockpit_center = pygame.image.load(pth).convert_alpha()
            
        except Exception:
            try:
                pth = get_resource_path(os.path.join('assets', 'cockpit_center_chroma.png'))
                self.cockpit_center = pygame.image.load(pth).convert_alpha()
            except Exception:
                try:
                    pth = get_resource_path(os.path.join('assets', 'cockpit_center.png'))
                    self.cockpit_center = pygame.image.load(pth).convert_alpha()
                except Exception:
                    try:
                        self.cockpit_center = pygame.image.load(r"C:\Users\usuario\examplegamepoo\assets\cockpit_center.png").convert_alpha()
                    except Exception:
                        self.cockpit_center = None

        try:
            self._detect_cockpit_windows()
        except Exception:
            self.window_rects = []
            self.window_edges = []
        
    def start(self, entry_img=None, no_shield=False):
        self.active = True
        self.state = 'entering'
        self.timer = 0.0
        self.segments = []
        self.traveled_distance = 0.0
        self.clouds = []
        self.entry_img = entry_img
        self.no_shield_entry = bool(no_shield)
        self.cam_x = LARGURA / 2
        self.cam_y = 300 * SCALE # Começa alto e seguro
        self.cam_z = 0.0
        self.scroll_speed = 0.0 
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.traveled_distance = 0.0
        self.enemies_killed = 0
        
        # Inicialização do Pool de Inimigos e Tiros
        self.enemies = []
        self.shots = []
        self.enemy_spawn_timer = 0.0
        self.reload_timer = 0.0
        
        if self.renderer3d and self.renderer3d.initialized:
            # Garante protótipos
            if 'enemy_proto' not in self.renderer3d.models:
                # Inimigo Esfera Ciano (Visível)
                self.renderer3d.create_sphere('enemy_proto', radius=80 * SCALE, color=(0.0, 1.0, 1.0), segments=12, rings=8)
                self.renderer3d.set_model_visible('enemy_proto', False)
            
            # Recria Pool de Inimigos (SEMPRE)
            self.enemies = [] # Garante limpo
            for i in range(20):
                name = f'enemy_{i}'
                # Duplicar sobrescreve se já existir, o que é OK
                self.renderer3d.duplicate_model('enemy_proto', name)
                self.renderer3d.set_model_visible(name, False)
                self.enemies.append({'active': False, 'x': 0, 'y': 0, 'z': 0, 'id': name})

            if 'shot_proto' not in self.renderer3d.models:
                # Tiro Amarelo Rápido
                self.renderer3d.create_sphere('shot_proto', radius=15 * SCALE, color=(1.0, 1.0, 0.0), segments=6, rings=6)
                self.renderer3d.set_model_visible('shot_proto', False)
            
            # Recria Pool de Tiros (SEMPRE)
            self.shots = []
            for i in range(30):
                name = f'shot_{i}'
                self.renderer3d.duplicate_model('shot_proto', name)
                self.renderer3d.set_model_visible(name, False)
                self.shots.append({'active': False, 'x': 0, 'y': 0, 'z': 0, 'vx': 0, 'vy': 0, 'vz': 0, 'id': name})
        
        # Preenche segmentos iniciais
        self.current_x = LARGURA / 2
        self.current_width = LARGURA * 0.8
        
        num_segs = int(ALTURA / self.segment_height) + 5
        for i in range(num_segs):
            self._add_segment(y_start=ALTURA + i * self.segment_height)

    def _perspective_factor(self, y):
        horizon = ALTURA * 0.35
        yy = y if y > horizon else horizon
        t = (yy - horizon) / max(1, (ALTURA - horizon))
        minf = 0.35
        return minf + (1.0 - minf) * t

    def _width_at_y(self, base_w, y):
        return base_w * self._perspective_factor(y)

    def _project(self, x, y, z):
        rx = x - self.cam_x
        ry = y - self.cam_y
        rz = z - self.cam_z + 1.0
        if rz <= 0.001:
            rz = 0.001
        s = (LARGURA * self.fov)
        sx = int(LARGURA / 2 + (rx / rz) * s)
        sy = int(ALTURA / 2 - (ry / rz) * s)
        
        # Apply banking rotation around screen center
        if self.banking != 0:
            cx = sx - LARGURA / 2
            cy = sy - ALTURA / 2
            cos_b = math.cos(self.banking)
            sin_b = math.sin(self.banking)
            
            nsx = cx * cos_b - cy * sin_b + LARGURA / 2
            nsy = cx * sin_b + cy * cos_b + ALTURA / 2
            return int(nsx), int(nsy), rz
            
        return sx, sy, rz

    def _jitter(self, y, side):
        seed = self.noise_seed_l if side == 'l' else self.noise_seed_r
        return math.sin(self.jitter_freq * y + seed) * self.jitter_amp

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
        self._update_shot_traces(dt)
        
        if self.state == 'entering':
            # Fase de reentrada (Zoom no planeta + Nuvens)
            # Nuvens começam a aparecer após 1s
            if self.timer > 0.8:
                self._update_clouds(dt, density=0.9, speed_mult=2.5)
            
            # Sem escudo: falha de reentrada no meio do processo
            if self.no_shield_entry and self.timer > 2.2:
                return 'failed'
            if self.timer > 3.5: # Tempo total de entrada aumentado
                # Transição para fase de descida 3D (se disponível)
                if self.renderer3d and self.renderer3d.initialized:
                    self.state = 'descending'
                    self.timer = 0.0
                    self.clouds = []
                    # Guarda imagem para crossfade
                    self._last_2d_img = self.entry_img
                else:
                    self.state = 'playing'
                    self.clouds = []
                    self._last_2d_img = None
                self.entry_img = None
        
        elif self.state == 'descending':
            # Fase de descida 3D com fog
            self._update_descent(dt)
            
            # Após 2.5s, transição para o cânion
            if self.timer > 2.5:
                self.state = 'playing'
                self.timer = 0.0
                self.descent_surface = None
                
        elif self.state == 'leveling':
            # Fase de Autopilot: Alinha a nave com o cânion antes de dar controle
            self.timer += dt
            
            # Movimento 3D (Câmera avança)
            if self.renderer3d and self.renderer3d.initialized and self.use_3d:
                self._update_3d_environment(dt)
            else:
                self.traveled_distance += self.scroll_speed * dt
                # Fallback updates...

            # Interpolação suave para o centro
            target_x = LARGURA / 2 # Centro da tela
            target_y = 150.0 # Altura de cruzeiro ideal
            target_bank = 0.0

            # Aproximação suave (Lerp)
            self.cam_x += (target_x - self.cam_x) * 2.0 * dt
            self.cam_y += (target_y - self.cam_y) * 2.0 * dt
            self.banking += (target_bank - self.banking) * 3.0 * dt

            # Duração do nivelamento: 3 segundos
            if self.timer > 3.0:
                self.state = 'playing'
                self.timer = 0.0
                print("[PlanetStage] Controle Manual Ativado!")

        elif self.state == 'playing':
            # Input do Jogador (Agora funciona para 3D e 2D)
            keys = pygame.key.get_pressed()
            move_speed = 150 * SCALE # Reduzido para controle fino
            move_speed_y = 80 * SCALE # Reduzido muito para evitar colisões bruscas
            
            # THROTTLE (Acelerador Manual)
            # A = Acelera (frente), Z = Freia
            # Ajuste para "Sensação de Gigante": Velocidade menor = Mundo maior.
            max_speed = 600 * SCALE 
            cruise_speed = max_speed * 0.6
            
            if keys[pygame.K_a]:
                self.scroll_speed += 300 * SCALE * dt 
            elif keys[pygame.K_z]:
                self.scroll_speed -= 500 * SCALE * dt 
            # else: Mantém velocidade atual (Fixo)
            
            # Limites de Velocidade
            self.scroll_speed = max(0, min(max_speed, self.scroll_speed))
            
            # Controle de PITCH (Bico da Nave)
            # S = Baixo (Negativo), X = Cima (Positivo)
            pitch_speed = 1500 * SCALE
            if keys[pygame.K_s]:
                self.pitch_angle -= pitch_speed * dt
            elif keys[pygame.K_x]:
                self.pitch_angle += pitch_speed * dt
            # else: NADA. Mantém o ângulo atual (Comportamento de Trim/Hold)
            
            # Limites amplos: -3000 (Olhar pro pé) a +3000 (Olhar pro céu)
            self.pitch_angle = max(-3000.0, min(3000.0, self.pitch_angle))

            # DEBUG: Screenshot (F10)
            if keys[pygame.K_F10]:
                try:
                    import time # Local import to avoid messing with top of file if not needed elsewhere
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    filename = f"screenshot_{timestamp}.png"
                    surf = self.renderer3d.render()
                    if surf:
                        pygame.image.save(surf, filename)
                        print(f"[DEBUG] Screenshot salvo: {filename}")
                except Exception as e:
                    print(f"[DEBUG] Erro ao salvar screenshot: {e}")

            # --- FÍSICA DE VOO COM INÉRCIA ---
            
            accel_x = 900 * SCALE
            accel_y = 700 * SCALE
            
            # Controle Lateral (Ailerons)
            if keys[pygame.K_LEFT]:
                self.vel_x -= accel_x * dt
            elif keys[pygame.K_RIGHT]:
                self.vel_x += accel_x * dt
            else:
                self.vel_x *= 0.92 # Atrito/Estabilização
                
            # Controle Vertical (Elevators) - Invertido (Manche)
            if keys[pygame.K_UP]: # Empurra manche -> Desce
                self.vel_y -= accel_y * dt
            elif keys[pygame.K_DOWN]: # Puxa manche -> Sobe
                self.vel_y += accel_y * dt
            else:
                self.vel_y *= 0.95 # Estabilização suave
                
            # AUTO-TERRAIN FOLLOWING (Colisão Real com Heightmap)
            # 1. Onde estamos no mundo?
            # world_x é calculado igual ao render update
            curr_world_x = (self.cam_x - LARGURA / 2) * 2.0
            
            # 2. Qual a altura do chão aqui?
            terrain_h = self.renderer3d.get_terrain_height(curr_world_x, self.cam_z)
            
            # 3. Evita colisão se detectou chão válido
            if terrain_h > -50000:
                # Converte altura do mundo (Y) para altura da câmera (Pixel Y)
                # Fórmula inversa de: world_y = (cam_y - 300) * 2
                ground_cam_y = (terrain_h / 2.0) + 300.0
                
                # Altura mínima segura (Ground + Margin)
                min_safe_y = ground_cam_y + (10 * SCALE)
                
                if self.cam_y < min_safe_y:
                    # Estamos abaixo do chão! Empurra pra cima.
                    delta = min_safe_y - self.cam_y
                    
                    # Força proporcional
                    lift = delta * 15.0 * dt
                    
                    if self.vel_y < 0: # Descendo
                        # Freio de emergência
                        self.vel_y += lift * 20.0 * SCALE
                    else:
                        # Mantém altitude
                        self.vel_y += lift * 5.0 * SCALE
                    
                    # Amortecimento forte
                    self.vel_y *= 0.85

            # Integração da Posição
            self.cam_x += self.vel_x * dt
            self.cam_y += self.vel_y * dt
            
            # Limites Físicos de Altura (Segurança visual)
            self.cam_y = max(10 * SCALE, min(600 * SCALE, self.cam_y))
            
            # Sem limitador lateral (Mundo Infinito)
            # if self.cam_x < 0: ... (Removido)

            # Banking Dinâmico (Roll)
            # Baseado na velocidade lateral. 
            # Esquerda (vel_x < 0) -> Roll positivo? Vamos testar.
            target_bank = (self.vel_x / (800.0 * SCALE)) * 0.4
            # Clamp no ângulo (max ~25 graus)
            target_bank = max(-0.45, min(0.45, target_bank))
            
            # Suavização do movimento de banking
            self.banking += (target_bank - self.banking) * 3.0 * dt
            
            # --- COMBATE 3D ---
            # Tiro (Espaço)
            self.reload_timer -= dt
            if keys[pygame.K_SPACE] and self.reload_timer <= 0:
                self._fire_shot_3d()
                self.reload_timer = 0.15 
            
            # Atualiza Inimigos e Tiros
            self._update_enemies_3d(dt)
            self._update_shots_3d(dt)

            # Lógica de Renderização e Colisão
            if self.renderer3d and self.renderer3d.initialized and self.use_3d:
                self._update_3d_environment(dt) # Apenas atualiza cenário
                
                # Sincroniza Player 2D (se existir) com Câmera para colisão
                # (Lógica simplificada: Câmera É o player)
                if self.check_collision_3d(invul_timer):
                     if not invul_timer > 0:
                        return True
                        
                # Verifica Fim (Pela Missão de Kills)
                if self.enemies_killed >= 5:
                    self.state = 'leaving'
                    self.timer = 0.0
                return False
            else:
                # Fallback 2D Legado
                self.traveled_distance += self.scroll_speed * dt
                # ... lógica de segmentos 2D antiga ...
                # (Mantendo simples para não quebrar compatibilidade, mas focado no 3D)
                # Move segmentos para baixo
                for seg in self.segments:
                    seg['y'] += self.scroll_speed * dt
                self.segments = [s for s in self.segments if s['y'] < ALTURA + 100]
                while self.segments[-1]['y'] > -self.segment_height:
                    self._add_segment()

            
            # Move segmentos para baixo
            for seg in self.segments:
                seg['y'] += self.scroll_speed * dt
                
            # Remove segmentos que saíram da tela (baixo)
            self.segments = [s for s in self.segments if s['y'] < ALTURA + 100]
            
            # Adiciona novos no topo
            while self.segments[-1]['y'] > -self.segment_height:
                self._add_segment()
                
            # Verifica colisão com paredes
            # Collision is now based on cam_x (player position in world) vs segment x
            # We check the segment closest to the "camera plane" (z=0 equivalent, or where player is)
            # In this projection, player is effectively at z=0 (or close to it).
            # We need to find segments that are "close" to the viewer.
            # Since segments move down (increasing y), and cam_y is 80, the player is "flying" over them.
            # But visually, the player is at the bottom of the screen? No, in this 3D view, the camera IS the player.
            # So we check collision with segments that are at y ~ cam_y or slightly ahead.
            
            hit = False
            # Check segments near the camera Y position
            # Since we project relative to cam_y, segments at cam_y are "under" us.
            # We probably want to check segments that are slightly in front (z > 0) or at the same y.
            # In this 2.5D setup, 'y' is actually depth (distance from top of screen in 2D, but here it's moving down).
            # The segments have 'y' in screen coordinates (sort of).
            # Let's check segments that are roughly at the bottom of the screen (closest to player).
            
            for seg in self.segments:
                # We only care about segments that are "close" to the player.
                # In this scrolling logic, segments with high Y are closer to the bottom of the screen.
                # The camera is at cam_y = 80 (top?), wait.
                # _project: ry = y - self.cam_y.
                # If y increases (moves down), ry increases.
                # sy = ALTURA/2 - (ry/rz)*s.
                # If ry is positive large, sy is small (top of screen?).
                # Wait, standard 3D: y is usually up/down.
                # Here, segments move 'y' += speed.
                # If y is large, it's "close" or "far"?
                # Let's look at _add_segment: y starts at ALTURA and goes negative.
                # So segments start at bottom (ALTURA) and go up? No, y_start=ALTURA + i*height.
                # They are added below the screen?
                # _add_segment(y_start=None) -> y = last_y - height.
                # So new segments are added at LOWER y (negative).
                # They move DOWN (y increases).
                # So they come from top (negative y) and move to bottom (positive y).
                # Player is effectively at the bottom?
                # Let's assume collision happens with segments that are near the "player's z" which is implicitly 0 or near the camera.
                # Actually, let's just check if the camera X is within the canyon width for the segment that is "at the player's position".
                # Visually, the player is "flying through".
                # Let's check segments that are currently visible and "passing" the player.
                # Since the camera is at cam_y=80, and segments move down.
                # Let's check segments around y=ALTURA (bottom of screen) or wherever the "hit plane" is.
                # Assuming the player is at the "bottom" of the visual field.
                
                if seg['y'] > ALTURA - 100 and seg['y'] < ALTURA + 50:
                    # This segment is passing the player (at bottom of screen)
                    # Check if cam_x is within the canyon
                    # Canyon center is seg['x'], width is seg['w']
                    # But wait, seg['w'] is the width at that point.
                    # We need to check if cam_x is inside [seg['x'] - w/2, seg['x'] + w/2]
                    
                    # Also need to account for perspective width? No, logic is in world coordinates.
                    # seg['x'] and seg['w'] are world coordinates.
                    
                    left_wall = seg['x'] - seg['w']/2
                    right_wall = seg['x'] + seg['w']/2
                    
                    # Margin for ship size (approx 30 units?)
                    margin = 30 * SCALE
                    
                    if self.cam_x - margin < left_wall or self.cam_x + margin > right_wall:
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
            # Acelera nave para cima visualmente (neste caso, sobe a camera ou apenas efeito)
            # player.y -= 100 * dt # Não usamos mais player.y
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
        elif self.state == 'descending':
            # Fase de descida 3D com fog
            self._draw_descent(screen)
        else:
            # Interior escuro da cabine (base para máscara)
            screen.fill((12, 14, 18))
        
        if self.state == 'playing' or self.state == 'leaving':
            if self.renderer3d and self.renderer3d.initialized and self.use_3d:
                # Renderiza a cena 3D (Céu Azul Claro)
                surf = self.renderer3d.render(clear_color=(0.4, 0.6, 0.9, 1.0))
                if surf:
                    screen.blit(surf, (0, 0))
            else:
                 # Fallback 2D Simplificado
                 h = ALTURA // 2
                 pygame.draw.rect(screen, self.color_wall_top, (0, 0, LARGURA, h))
                 pygame.draw.rect(screen, self.color_ground, (0, h, LARGURA, ALTURA - h))
            
            # Desenha traços de tiro
            self._draw_shot_traces(screen)

    def draw_cockpit(self, screen):
        # Nuvens (Ação/Ambiente) desenhadas ANTES do cockpit para ficarem "lá fora"
        for c in self.clouds:
            s_cloud = pygame.Surface((c['rect'].w, c['rect'].h), pygame.SRCALPHA)
            s_cloud.fill((255, 255, 255, c['alpha']))
            screen.blit(s_cloud, c['rect'])

        s = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        
        # overlay de cockpit fullscreen (Nave por cima de tudo)
        if self.cockpit_center:
            # Escala para tela cheia
            img = pygame.transform.smoothscale(self.cockpit_center, (LARGURA, ALTURA))
            s.blit(img, (0, 0))
        else:
            # Fallback se não tiver imagem: desenha moldura simples
            t = int(ALTURA * 0.32)
            frame_pts = [
                (0, t),
                (int(LARGURA*0.22), int(ALTURA*0.30)),
                (int(LARGURA*0.78), int(ALTURA*0.30)),
                (LARGURA, t)
            ]
            pygame.draw.lines(s, (18, 20, 26, 220), False, frame_pts, 8)
            pygame.draw.rect(s, (25, 28, 36, 210), (0, ALTURA-130, LARGURA, 130))

        # Radar / HUD de Terreno (Overlay)
        self._draw_radar_hud(s)
        self._draw_tactical_map(s)

        screen.blit(s, (0, 0))
        if self.state == 'entering':
            self._draw_window_plasma(screen)
            
        # Fade In/Out (Branco) - Efeitos de tela cheia por cima de tudo (opcional, mas faz sentido ser pós-processamento)
        if self.state == 'entering':
            if self.timer > 2.0:
                if self.timer < 2.8:
                    alpha = int(255 * (self.timer - 2.0) / 0.8)
                else:
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

    def _apply_lighting(self, base_col, z, x):
        d = max(0.25, min(1.0, 1.25 - 0.0025 * z))
        sun = 0.15 + 0.25 * (x / LARGURA)
        k = max(0.2, min(1.0, d + sun))
        r, g, b = base_col
        return (min(255, int(r * k)), min(255, int(g * k)), min(255, int(b * k)))

    def _detect_cockpit_windows(self):
        """Detecta regiões transparentes grandes (janelas) no cockpit e salva contornos."""
        self.window_rects = []
        self.window_edges = []
        if not self.cockpit_center:
            return

        self._cockpit_size = self.cockpit_center.get_size()

        mask_opaque = pygame.mask.from_surface(self.cockpit_center, 10)
        mask_transparent = mask_opaque.copy()
        mask_transparent.invert()

        w, h = self.cockpit_center.get_size()
        min_area = max(8000, int(w * h * 0.01))

        for comp in mask_transparent.connected_components(minimum=min_area):
            rects = comp.get_bounding_rects()
            if not rects:
                continue
            rect = rects[0]

            # Ignora áreas que encostam na borda (bordas externas da imagem)
            if rect.left <= 0 or rect.top <= 0 or rect.right >= w or rect.bottom >= h:
                continue

            area = rect.width * rect.height
            if area < min_area:
                continue

            # Garante que a região é majoritariamente transparente (buraco real)
            fill_ratio = comp.count() / float(area)
            if fill_ratio < 0.65:
                continue

            outline = comp.outline()
            if len(outline) < 3:
                continue

            self.window_rects.append(rect)
            self.window_edges.append(outline)

        self.window_rects.sort(key=lambda r: r.left)

    def _draw_window_plasma(self, screen):
        """Efeito de plasma como chuva nas janelas durante a reentrada."""
        if self.state != 'entering':
            self.plasma_streaks.clear()
            self._plasma_prev_tick = pygame.time.get_ticks()
            return
        if not self.window_rects or not self._cockpit_size:
            return

        now = pygame.time.get_ticks()
        dt = max(0.001, (now - self._plasma_prev_tick) / 1000.0)
        self._plasma_prev_tick = now

        self.plasma_surface.fill((0, 0, 0, 0))

        sx = LARGURA / float(self._cockpit_size[0])
        sy = ALTURA / float(self._cockpit_size[1])

        # Spawns proporcionais às janelas para formar "chuva" no contorno
        spawn_rate = 60 * max(1, len(self.window_rects))
        total_new = int(spawn_rate * dt)

        for _ in range(total_new):
            rect = random.choice(self.window_rects)
            px = random.uniform(rect.left, rect.right)
            py = random.uniform(rect.top - rect.height * 0.05, rect.top + rect.height * 0.18)
            x = px * sx + random.uniform(-3, 3) * SCALE
            y = py * sy + random.uniform(-6, 6) * SCALE
            vy = random.uniform(900, 1400) * SCALE
            vx = random.uniform(-60, 60) * SCALE
            life = random.uniform(0.25, 0.45)
            length = random.uniform(30, 70) * SCALE
            self.plasma_streaks.append({
                "x": x, "y": y, "vx": vx, "vy": vy,
                "life": life, "max": life, "len": length
            })

        alive = []
        for p in self.plasma_streaks:
            p["life"] -= dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vx"] *= 0.985
            p["vy"] *= 1.01
            p["x"] += math.sin(p["y"] * 0.01 + now * 0.01) * 6 * SCALE * dt

            if p["life"] > 0 and p["y"] < ALTURA + 40:
                alive.append(p)
                fade = max(0.0, min(1.0, p["life"] / p["max"]))
                alpha = int(200 * fade)
                color = (255, min(255, int(180 + 60 * fade)), min(255, int(90 + 70 * fade)))
                end_y = p["y"] - p["len"]
                pygame.draw.line(
                    self.plasma_surface,
                    (*color, alpha),
                    (int(p["x"]), int(p["y"])),
                    (int(p["x"]), int(end_y)),
                    max(2, int(3 * SCALE))
                )

        self.plasma_streaks = alive
        if self.plasma_streaks:
            screen.blit(self.plasma_surface, (0, 0), special_flags=pygame.BLEND_ADD)

    def registrar_tiro_cockpit(self, offsets, angulos):
        """Registra rastros de tiro para exibição na janela 3D."""
        base_y = ALTURA * 0.72
        vanishing_y = ALTURA * 0.50  # traz horizonte mais baixo
        for off in offsets:
            for ang in angulos:
                cx = LARGURA / 2 + off
                # mira para o centro do horizonte, sem desvio lateral aleatório
                target_x = (LARGURA / 2) + off * 0.1
                target_y = vanishing_y
                dir_x = target_x - cx
                dir_y = target_y - base_y
                alcance = ALTURA * 0.29  # encurta ~10% para manter visível mesmo com bank
                # leve roll para variar (mantém só a orientação do canhão)
                dir_x += math.sin(ang) * 8 * SCALE
                norm = max(0.001, math.hypot(dir_x, dir_y))
                dir_x /= norm
                dir_y /= norm
                ex = cx + dir_x * alcance
                ey = base_y + dir_y * alcance
                self.shot_traces.append({
                    "start": (cx, base_y),
                    "end": (ex, ey),
                    "life": 0.18,
                    "max": 0.18
                })

    def _update_shot_traces(self, dt):
        if not self.shot_traces:
            return
        vivos = []
        for s in self.shot_traces:
            s["life"] -= dt
            if s["life"] > 0:
                vivos.append(s)
        self.shot_traces = vivos

    def _draw_shot_traces(self, surf):
        if not self.shot_traces:
            return
        for s in self.shot_traces:
            t = max(0.0, min(1.0, s["life"] / s["max"]))
            alpha = int(210 * t)
            color = (130 + int(110 * t), 230, 255)
            start = (float(s["start"][0]), float(s["start"][1]))
            end = (float(s["end"][0]), float(s["end"][1]))
            if self.banking != 0.0:
                start = self._apply_bank_to_point(start)
                end = self._apply_bank_to_point(end)
            w0 = max(6, int(10 * SCALE))
            w1 = max(1, int(3 * SCALE))
            self._draw_tapered_beam(surf, start, end, color, alpha, w0, w1)

    def _draw_tapered_beam(self, surf, start, end, color, alpha, w0, w1):
        """Desenha um feixe que afina para longe para dar sensação de profundidade."""
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 1:
            return
        nx = -dy / dist
        ny = dx / dist
        w0 *= 0.5
        w1 *= 0.5
        p1 = (x1 + nx * w0, y1 + ny * w0)
        p2 = (x1 - nx * w0, y1 - ny * w0)
        p3 = (x2 - nx * w1, y2 - ny * w1)
        p4 = (x2 + nx * w1, y2 + ny * w1)
        pygame.draw.polygon(surf, (*color, alpha), [p1, p2, p3, p4])
        # glow externo
        glow_a = int(alpha * 0.5)
        glow_color = (color[0], color[1], color[2], glow_a)
        pygame.draw.polygon(surf, glow_color, [p1, p2, p3, p4], max(1, int(2 * SCALE)))

    def _apply_bank_to_point(self, pt):
        """Aplica a rotação de banking em torno do centro da tela."""
        cx, cy = LARGURA / 2, ALTURA / 2
        x, y = pt
        dx = x - cx
        dy = y - cy
        cos_b = math.cos(self.banking)
        sin_b = math.sin(self.banking)
        rx = dx * cos_b - dy * sin_b + cx
        ry = dx * sin_b + dy * cos_b + cy
        return (rx, ry)

    def _init_3d_renderer(self):
        """Inicializa o renderer 3D para a fase de descida."""
        if not HAS_3D_RENDERER:
            self.renderer3d = None
            self.renderer3d_error = "Renderer3D não disponível (import falhou)"
            return
        
        try:
            self.renderer3d = Renderer3D(LARGURA, ALTURA)
            if self.renderer3d.initialized:
                self.renderer3d_error = None
                # Tenta carregar modelo .glb do planeta
                model_path = get_resource_path(os.path.join('assets', 'models', 'planet.glb'))
                if os.path.exists(model_path):
                    if self.renderer3d.load_glb('planet', model_path):
                        print(f"[PlanetStage] Modelo 3D carregado: {model_path}")
                    else:
                        # Fallback: esfera procedural
                        self.renderer3d.create_sphere('planet', radius=2.0, segments=48, rings=32, 
                                                      color=(0.6, 0.5, 0.4))
                        print("[PlanetStage] Usando esfera procedural (fallback)")
                else:
                    # Fallback: esfera procedural
                    self.renderer3d.create_sphere('planet', radius=2.0, segments=48, rings=32, 
                                                  color=(0.6, 0.5, 0.4))
                    print("[PlanetStage] Modelo não encontrado, usando esfera procedural")
                
                self.renderer3d.set_model_transform('planet', position=(0, 0, 0), scale=1.0)
                
                # Carrega modelo do canyon/deserto
                canyon_path = get_resource_path(os.path.join('assets', 'models', 'Desert 1 (.glb).glb'))
                if os.path.exists(canyon_path):
                    # Tenta carregar SEM rotação primeiro, pois o usuário reportou "paredão" (chão vertical)
                    if self.renderer3d.load_glb('canyon', canyon_path, rotate_x_90=False):
                        print(f"[PlanetStage] Canyon 3D carregado (sem rot): {canyon_path}")
                        # Posiciona o canyon abaixo da nave
                        self.renderer3d.set_model_transform('canyon', 
                            position=(0, -20, 0), 
                            scale=0.05)  # Ajuste de escala conforme necessário
                        tex_path = get_resource_path(os.path.join('assets', 'models', 'textures', 'GOOGLE_SAT_WM.tif'))
                        if os.path.exists(tex_path):
                            if self.renderer3d.load_texture('desert_tex', tex_path):
                                self.renderer3d.set_model_texture('canyon', 'desert_tex')
                                # Tenta usar UV mapping (modo 0) para textura de satélite
                                self.renderer3d.set_model_tex_mode('canyon', 0)
                                print(f"[PlanetStage] Textura aplicada ao canyon: {tex_path}")
                            else:
                                print(f"[PlanetStage] Falha ao carregar textura: {tex_path}")
                        else:
                            print(f"[PlanetStage] Textura não encontrada: {tex_path}")
                    else:
                        print("[PlanetStage] Falha ao carregar canyon")
                else:
                    print(f"[PlanetStage] Canyon não encontrado em: {canyon_path}")
                
                print("[PlanetStage] Renderer 3D inicializado com sucesso")
            else:
                try:
                    self.renderer3d_error = getattr(self.renderer3d, "last_error", None) or "Falha ao inicializar contexto OpenGL"
                except Exception:
                    self.renderer3d_error = "Falha ao inicializar contexto OpenGL"
                self.renderer3d = None
        except Exception as e:
            print(f"[PlanetStage] Falha ao inicializar renderer 3D: {e}")
            self.renderer3d_error = str(e)
            self.renderer3d = None
    
    def _update_3d_environment(self, dt):
        """Atualiza o ambiente 3D (movimento do terreno em Z) sem afetar a câmera X/Y."""
        
        # Garante que NÃO vemos o lado de dentro das montanhas (Backface Culling ATIVADO)
        self.renderer3d.set_culling(True)
        
        # Modo Debug Viewer (Tecla V)
        # Modo Debug Viewer (Tecla V) - DESATIVADO (self.game não existe)
        # if getattr(self, 'game', None) and getattr(self.game, 'debug_viewer_active', False):
        #     # Usa a câmera de debug controlada pelo usuário
        #     dist = self.game.debug_dist
        #     yaw = self.game.debug_yaw
        #     pitch = self.game.debug_pitch
        #     tgt = self.game.debug_target
        #     
        #     # Calcula posição esférica
        #     cx = tgt[0] + dist * math.sin(yaw) * math.cos(pitch)
        #     cy = tgt[1] + dist * math.sin(pitch)
        #     cz = tgt[2] + dist * math.cos(yaw) * math.cos(pitch)
        #     
        #     self.renderer3d.set_camera(pos=(cx, cy, cz), target=tuple(tgt))
        #     
        #     # Se quiser continuar movendo o cenário no fundo, remova o return.
        #     # Mas geralmente pause ou freecam não move o jogo.
        #     return

        self.traveled_distance += self.scroll_speed * dt
        
        # Loop Infinito do Terreno
        # Escala 8.0 -> Tamanho ~19600. Usamos 19200.
        SEGMENT_LENGTH = 19200.0 
        
        base_idx = math.ceil(self.cam_z / SEGMENT_LENGTH)
        z1 = base_idx * SEGMENT_LENGTH
        z2 = (base_idx - 1) * SEGMENT_LENGTH
        
        # Helper params para escala 8.0 (Planeta Colossal)
        Y_POS = -12000 
        SCALE_VAL = 8.0
        OFFSET_LAT = 38400.0 
        # Aumentando sobreposição para esconder "paredes" laterais
        # De 38000 para 30000. Sobreposição massiva.
        OFFSET_LAT_OVERLAP = 30000.0 

        # Sincroniza apenas a Câmera 3D
        # World X agora é livre (sem clamp de tela). 1 pixel = 2 metros
        world_x = (self.cam_x - LARGURA / 2) * 2.0
        # Converte cam_y de pixels para Mundo 3D (Mapeamento Expandido)
        world_y = (self.cam_y - 300.0) * 2.0
        
        # PITCH MANUAL (Nariz da nave - Sobe/Desce)
        target_look_y = world_y + self.pitch_angle
        
        # YAW VISUAL (Nariz da nave - Esquerda/Direita)
        yaw_offset = math.sin(self.banking) * 6000.0 # Curva visual ajustada para escala
        target_look_x = world_x + yaw_offset # Somar offset corrige a direção do nariz (Direita = +) 
        
        # Lógica de Tiling Lateral Infinito (Minecraft Style)
        col_idx = round(target_look_x / OFFSET_LAT_OVERLAP)
        center_x_pos = col_idx * OFFSET_LAT_OVERLAP

        if 'canyon' in self.renderer3d.models:
            # Garante clones laterais
            if 'canyon_L' not in self.renderer3d.models:
                self.renderer3d.duplicate_model('canyon', 'canyon_L')
                self.renderer3d.duplicate_model('canyon', 'canyon_R')
                
            # Flatten Y scale (0.4 relative to main scale)
            flat_scale = (SCALE_VAL, SCALE_VAL * 0.4, SCALE_VAL)
            flat_scale_mirror = (-SCALE_VAL, SCALE_VAL * 0.4, SCALE_VAL)
            
            Y_POS_FLAT = -5000 
            
            # Atualiza Central (Ping Pong)
            if col_idx % 2 == 0:
                center_scale = flat_scale
                side_scale = flat_scale_mirror
            else:
                center_scale = flat_scale_mirror
                side_scale = flat_scale
                
            self.renderer3d.set_model_transform('canyon', position=(center_x_pos, Y_POS_FLAT, z1), scale=center_scale)
            # Laterais seguem o padrão alternado
            self.renderer3d.set_model_transform('canyon_L', position=(center_x_pos - OFFSET_LAT_OVERLAP, Y_POS_FLAT, z1), scale=side_scale)
            self.renderer3d.set_model_transform('canyon_R', position=(center_x_pos + OFFSET_LAT_OVERLAP, Y_POS_FLAT, z1), scale=side_scale)
            
        if 'canyon_next' in self.renderer3d.models:
             # Garante clones laterais
            if 'canyon_next_L' not in self.renderer3d.models:
                self.renderer3d.duplicate_model('canyon_next', 'canyon_next_L')
                self.renderer3d.duplicate_model('canyon_next', 'canyon_next_R')
            
            flat_scale = (SCALE_VAL, SCALE_VAL * 0.4, SCALE_VAL)
            flat_scale_mirror = (-SCALE_VAL, SCALE_VAL * 0.4, SCALE_VAL)
            Y_POS_FLAT = -5000

            # Mesma lógica Ping-Pong
            if col_idx % 2 == 0:
                center_scale = flat_scale
                side_scale = flat_scale_mirror
            else:
                center_scale = flat_scale_mirror
                side_scale = flat_scale

            self.renderer3d.set_model_transform('canyon_next', position=(center_x_pos, Y_POS_FLAT, z2), scale=center_scale)
            self.renderer3d.set_model_transform('canyon_next_L', position=(center_x_pos - OFFSET_LAT_OVERLAP, Y_POS_FLAT, z2), scale=side_scale)
            self.renderer3d.set_model_transform('canyon_next_R', position=(center_x_pos + OFFSET_LAT_OVERLAP, Y_POS_FLAT, z2), scale=side_scale)
        
        # Limpa o Fog da entrada (Fundo Azul Claro - Céu Diurno)
        self.renderer3d.set_fog(0.0005, (0.4, 0.6, 0.9)) 
        
        self.cam_z -= self.scroll_speed * dt * 0.1 # Ajuste de velocidade
        
        # Atualiza Câmera
        # Target: (X com Yaw, Y com Pitch, Z longe)
        # UP Vector: Rotacionado pelo Banking para inclinar o horizonte
        up_x = -math.sin(self.banking)
        up_y = math.cos(self.banking)
        
        self.renderer3d.set_camera(pos=(world_x, world_y, self.cam_z), 
                                   target=(target_look_x, target_look_y, self.cam_z - 2000),
                                   up=(up_x, up_y, 0.0))

    # --- LÓGICA DE COMBATE 3D ---
    
    def _update_enemies_3d(self, dt):
        # Limite de inimigos simultâneos para não poluir
        active_count = sum(1 for e in self.enemies if e['active'])
        
        # Spawn
        self.enemy_spawn_timer -= dt
        if self.enemy_spawn_timer <= 0 and active_count < 3:
            # Procura slot vazio
            for e in self.enemies:
                if not e['active']:
                    e['active'] = True
                    # Posição de Spawn: Longe na frente
                    # X aleatório no range visível
                    world_x = (self.cam_x - LARGURA / 2) * 2.0
                    yaw_offset = math.sin(self.banking) * 6000.0
                    target_look_x = world_x + yaw_offset
                    
                    spawn_x = target_look_x + random.uniform(-4000, 4000)
                    spawn_z = self.cam_z - 15000 # 15km a frente
                    
                    # Spawn no SOLO (Canhão)
                    h = -2000
                    if self.renderer3d:
                        h = self.renderer3d.get_terrain_height(spawn_x, spawn_z)
                    
                    if h > -50000:
                         spawn_y = h + (50 * SCALE) # No chão
                    else:
                         spawn_y = -2000 # Fallback ar
                    
                    e['x'] = spawn_x
                    e['y'] = spawn_y
                    e['z'] = spawn_z
                    
                    # Torna visível
                    if self.renderer3d:
                        self.renderer3d.set_model_visible(e['id'], True)
                        self.renderer3d.set_model_transform(e['id'], position=(spawn_x, spawn_y, spawn_z), scale=1.0)
                    
                    self.enemy_spawn_timer = random.uniform(2.0, 4.0) # Spawn a cada 2-4s
                    break
        
        # Update
        for e in self.enemies:
            if e['active']:
                # Move levemente em direção ao player? Não, estático é melhor pra começar (minas flutuantes)
                # Apenas verifica se passou da câmera
                if e['z'] > self.cam_z + 500:
                    e['active'] = False
                    if self.renderer3d:
                        self.renderer3d.set_model_visible(e['id'], False)
                else:
                    # Update visual (pode oscilar ou girar)
                    if self.renderer3d:
                         self.renderer3d.set_model_transform(e['id'], position=(e['x'], e['y'], e['z']), scale=1.0)

    def _fire_shot_3d(self):
        # Procura slot
        for s in self.shots:
            if not s['active']:
                s['active'] = True
                
                # Posição inicial: Câmera + Offset (Nariz)
                world_x = (self.cam_x - LARGURA / 2) * 2.0
                world_y = (self.cam_y - 300.0) * 2.0
                
                # Yaw visual
                yaw_offset = math.sin(self.banking) * 6000.0
                # Vetor Forward normalizado aproximado
                # (Isso é um hack, idealmente usariamos matrizes de rotação completas)
                # Para simplificar: Tiro vai para "Onde estou olhando"
                
                target_look_x = world_x + yaw_offset
                target_look_y = world_y + self.pitch_angle
                target_look_z = self.cam_z - 2000.0
                
                # Vetor Direção
                dx = target_look_x - world_x
                dy = target_look_y - world_y
                dz = target_look_z - self.cam_z
                inv_len = 1.0 / math.sqrt(dx*dx + dy*dy + dz*dz)
                
                speed = 20000.0 * SCALE # Tiro muito rápido
                
                s['vx'] = dx * inv_len * speed
                s['vy'] = dy * inv_len * speed
                s['vz'] = dz * inv_len * speed
                
                s['x'] = world_x
                s['y'] = world_y
                s['z'] = self.cam_z - 100 # Começa um pouco a frente
                
                if self.renderer3d:
                    self.renderer3d.set_model_visible(s['id'], True)
                break

    def _update_shots_3d(self, dt):
        for s in self.shots:
            if s['active']:
                s['x'] += s['vx'] * dt
                s['y'] += s['vy'] * dt
                s['z'] += s['vz'] * dt
                
                # Timeout / Distância
                if s['z'] < self.cam_z - 30000: # Longe demais
                    s['active'] = False
                    if self.renderer3d:
                        self.renderer3d.set_model_visible(s['id'], False)
                    continue

                # Colisão com Inimigos (Esfera-Esfera simples)
                hit = False
                shot_r = 50 * SCALE
                enemy_r = 120 * SCALE # Hitbox generosa
                
                for e in self.enemies:
                    if e['active']:
                        dx = s['x'] - e['x']
                        dy = s['y'] - e['y']
                        dz = s['z'] - e['z'] # Importante Z collision
                        dist_sq = dx*dx + dy*dy + dz*dz
                        
                        if dist_sq < (shot_r + enemy_r)**2:
                            # BOOM
                            e['active'] = False
                            if self.renderer3d:
                                self.renderer3d.set_model_visible(e['id'], False)
                            hit = True
                            self.enemies_killed += 1
                            print(f"HIT CONFIRMED! Kills: {self.enemies_killed}")
                            break
                
                if hit:
                    s['active'] = False
                    if self.renderer3d:
                        self.renderer3d.set_model_visible(s['id'], False)
                else:
                    if self.renderer3d:
                        self.renderer3d.set_model_transform(s['id'], position=(s['x'], s['y'], s['z']), scale=1.0)
    
    def check_collision_3d(self, invul_timer):
        """Verifica colisão simples nas paredes laterais."""
        # Se cam_x sair muito do centro, colide
        # Limite do Cânion (Ajustado para escala 8.0)
        # Largura total = 38000. Centro = 0.
        # Paredes em +/- 19000? Não, o canyon tem paredes inclinadas.
        # Vamos ser generosos: se passar de +/- 15000 do centro do TILE ATUAL.
        
        # O sistema de tiling centraliza o player visualmente no canyon "ativo".
        # Então se o player se afastar muito do target_look_x (que segue o centro do tile), ele bate.
        # Mas como a câmera SE move, na verdade o perigo é bater no chao, o que já tratamos (lift).
        # Paredes laterais: vamos ignorar por enquanto ou usar get_terrain_height muito alto?
        
        # A lógica antiga usava limit_x fixo.
        limit_x = 10000.0 * SCALE
        
        # Como o mundo é infinito lateralmente agora, não existe "parede" exceto se voar baixo d+.
        # O "chão" sobe nas laterais.
        
        # Colisão com o solo já é tratada no update (empurra pra cima).
        # Mas queremos DANO se bater forte?
        # Por enquanto retorna False (sem colisão explosiva, apenas física de empurrão).
        return False
        
    def _draw_tactical_map(self, surf):
        """Desenha minimapa tático 2D (Top-Down) no canto."""
        margin = 20
        w = 200
        h = 200
        x = margin
        y = 150 
        
        # Fundo
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 20, 30, 160)) 
        pygame.draw.rect(s, (0, 100, 255), (0, 0, w, h), 1)
        
        # Player (Seta)
        cx = w / 2
        cy = h - 30
        pygame.draw.polygon(s, (255, 255, 0), [(cx, cy-5), (cx-6, cy+8), (cx, cy+4), (cx+6, cy+8)])
        
        range_x = 24000.0 * SCALE
        range_z = 40000.0 * SCALE
        
        ship_world_x = (self.cam_x - LARGURA/2) * 2.0
        
        if hasattr(self, 'enemies'):
            for e in self.enemies:
                if e['active']:
                    dx = e['x'] - ship_world_x
                    dz = self.cam_z - e['z'] # Positivo para Frente
                    
                    # Calcula posição teórica no mapa
                    # range_x e range_z definem o zoom.
                    # Se estiver muito longe (> range), vai cair fora da caixa.
                    raw_px = cx + (dx / range_x) * w
                    raw_py = cy - (dz / range_z) * (h - 40)
                    
                    # Verifica Clamping (Bordas)
                    pad = 8
                    clamped_x = max(pad, min(w - pad, raw_px))
                    clamped_y = max(pad, min(h - pad, raw_py))
                    
                    is_outside = (raw_px != clamped_x) or (raw_py != clamped_y)
                    
                    # Se estiver atrás da câmera (dz < 0), raw_py será > cy.
                    # Queremos mostrar inimigos atrás? O map desenha até h.
                    # Se dz < -5000 (muito atrás), ignorar? O range check original cuidava disso.
                    # Vamos manter o range check APENAS para o limite "muito atrás" onde não importa mais.
                    
                    if dz > -5000: # Ignora o que já ficou muito pra trás
                        if is_outside:
                            # Desenha Indicador de Borda (Laranja)
                            pygame.draw.circle(s, (255, 120, 0), (int(clamped_x), int(clamped_y)), 3)
                        else:
                            # Desenha Ponto Normal (Ciano)
                            pygame.draw.circle(s, (0, 255, 255), (int(raw_px), int(raw_py)), 4)
                             
        surf.blit(s, (x, y))
        font = pygame.font.SysFont("Arial", 12, bold=True)
        lbl = font.render("TACTICAL MAP", True, (0, 200, 255))
        surf.blit(lbl, (x + 5, y + 5))
        
        lbl_kills = font.render(f"TARGETS: {self.enemies_killed}/5", True, (255, 50, 50))
        surf.blit(lbl_kills, (x + 5, y + 20))
    
    def _update_descent(self, dt):
        """Atualiza a fase de descida 3D com fog."""
        if not self.renderer3d:
            return
        
        # Progresso da descida (0.0 a 1.0)
        descent_duration = 2.5
        progress = min(1.0, self.timer / descent_duration)
        
        # Câmera começa PERTO do planeta (grande) e mergulha nele
        # Inicia com planeta ocupando quase toda a tela, depois "entra" na superfície
        cam_z = 3.0 - progress * 2.5  # 3 -> 0.5 (muito perto no final)
        cam_y = 0.3 - progress * 0.5  # 0.3 -> -0.2 (desce em direção à superfície)
        self.renderer3d.set_camera(pos=(0, cam_y, cam_z), target=(0, 0, 0))
        
        # Rotação lenta do planeta
        if 'planet' in self.renderer3d.models:
            rot_y = self.timer * 0.2
            # Escala grande para o planeta preencher a tela
            self.renderer3d.set_model_transform('planet', rotation=(0, rot_y, 0.05), scale=2.5)
        
        # Animação do canyon - aparece conforme desce
        if 'canyon' in self.renderer3d.models:
            canyon_scale = 0.05 + progress * 0.1  # Aumenta a escala conforme desce
            canyon_y = -20 + progress * 15  # Sobe conforme a nave desce
            canyon_rot = self.timer * 0.1  # Rotação lenta
            self.renderer3d.set_model_transform('canyon', 
                position=(0, canyon_y, 0), 
                rotation=(0, canyon_rot, 0),
                scale=canyon_scale)
        
        # Fog aumenta conforme desce (simula atmosfera)
        fog_density = progress * 0.4  # 0 -> 0.4
        fog_color = (0.75 + progress * 0.15, 0.7 + progress * 0.2, 0.6 + progress * 0.3)
        self.renderer3d.set_fog(fog_density, fog_color)
        
        # Renderiza para surface
        self.descent_surface = self.renderer3d.render(clear_color=(0.05, 0.05, 0.08, 1.0))
    
    def _draw_descent(self, screen):
        """Desenha a fase de descida 3D com crossfade do 2D."""
        # Crossfade: nos primeiros 0.8s, mistura 2D com 3D
        crossfade_duration = 0.8
        
        if self.timer < crossfade_duration and hasattr(self, '_last_2d_img') and self._last_2d_img:
            # Desenha imagem 2D com zoom máximo (como terminou)
            alpha_2d = int(255 * (1.0 - self.timer / crossfade_duration))
            
            iw = self._last_2d_img.get_width()
            ih = self._last_2d_img.get_height()
            # Zoom máximo (5% da imagem = zoom extremo)
            rw = max(1, int(iw * 0.05))
            rh = max(1, int(ih * 0.05))
            cx, cy = iw // 2, ih // 2
            rect = pygame.Rect(cx - rw//2, cy - rh//2, rw, rh)
            
            try:
                sub = self._last_2d_img.subsurface(rect)
                scaled_2d = pygame.transform.scale(sub, (LARGURA, ALTURA))
                
                # Desenha 3D primeiro
                if self.descent_surface:
                    screen.blit(self.descent_surface, (0, 0))
                
                # Sobrepõe 2D com fade out
                scaled_2d.set_alpha(alpha_2d)
                screen.blit(scaled_2d, (0, 0))
            except Exception:
                if self.descent_surface:
                    screen.blit(self.descent_surface, (0, 0))
        elif self.descent_surface:
            screen.blit(self.descent_surface, (0, 0))
        else:
            # Fallback: gradiente simples
            for i in range(20):
                t = i / 19.0
                progress = min(1.0, self.timer / 2.5)
                fog = int(180 + 75 * progress * (1 - t))
                color = (fog, int(fog * 0.9), int(fog * 0.8))
                h = ALTURA // 20
                pygame.draw.rect(screen, color, (0, i * h, LARGURA, h + 1))

    def _draw_radar_hud(self, surf):
        """Desenha instrumentos de navegação no cockpit."""
        if not self.active or self.state == 'inactive':
            return

        # Posição do Radar (Centro Inferior)
        cx = LARGURA // 2
        cy = ALTURA - 80 * SCALE
        w = 300 * SCALE
        h = 100 * SCALE
        
        # Fundo do Radar
        rect = pygame.Rect(cx - w//2, cy - h//2, w, h)
        pygame.draw.rect(surf, (0, 20, 10, 180), rect)
        
        # --- HORIZONTE ARTIFICIAL (ADI) ---
        # Desenha o céu (azul) e chão (marrom) inclinados
        # Pitch move o horizonte verticalmente: Pitch UP -> Horizonte Desce
        # Bank roda o horizonte: Bank Left -> Horizonte Roda Right
        
        # Fator de escala do pitch no horizonte (ajuste visual)
        horizon_y_offset = (self.pitch_angle / 50.0) * (rect.height / 4)
        hor_cy = rect.centery + horizon_y_offset
        
        # Cria um polígono grande para o horizonte
        # Largura suficiente para cobrir rotação
        big_w = rect.width * 2
        
        # Pontos do horizonte (Esquerda, Direita) antes da rotação
        p1 = pygame.math.Vector2(-big_w, 0)
        p2 = pygame.math.Vector2(big_w, 0)
        
        # Rotação (Inverso do banking da nave)
        angle_deg = math.degrees(self.banking)
        p1 = p1.rotate(-angle_deg)
        p2 = p2.rotate(-angle_deg)
        
        # Translação para o centro
        center = pygame.math.Vector2(rect.centerx, hor_cy)
        p1 += center
        p2 += center
        
        # Desenha Céu e Terra (Recortado pelo rect do radar)
        # Usamos clip area temporária se possível, ou desenhamos e depois desenhamos a borda por cima
        # Pygame set_clip é útil aqui
        old_clip = surf.get_clip()
        surf.set_clip(rect)
        
        # Céu (Polígono acima da linha)
        # P3 e P4 muito acima para fechar o polígono
        p3 = p2 + pygame.math.Vector2(0, -1000).rotate(-angle_deg)
        p4 = p1 + pygame.math.Vector2(0, -1000).rotate(-angle_deg)
        pygame.draw.polygon(surf, (50, 80, 120), [p1, p2, p3, p4]) # Azul Céu
        
        # Terra (Polígono abaixo da linha)
        p5 = p2 + pygame.math.Vector2(0, 1000).rotate(-angle_deg)
        p6 = p1 + pygame.math.Vector2(0, 1000).rotate(-angle_deg)
        pygame.draw.polygon(surf, (80, 60, 40), [p1, p2, p5, p6]) # Marrom Terra
        
        # Linha do Horizonte
        pygame.draw.line(surf, (200, 200, 200), p1, p2, 2)
        
        # Restaura clip
        surf.set_clip(old_clip)
        
        # Borda do Radar (Redesenha por cima)
        pygame.draw.rect(surf, (50, 200, 100), rect, 2)
        
        # --- FIM HORIZONTE ARTIFICIAL ---
        
        # Scanner de Terreno Real (Terrain Profile)
        scan_points = []
        num_samples = 40
        look_ahead = 1000.0 # Olha 1km à frente
        scan_world_width = 12000.0 # Largura da varredura extendida para ver inimigos
        
        ship_world_x = (self.cam_x - LARGURA / 2) * 2.0
        
        # Converte altitude da nave (pixel space -> world space aproximado para visualização)
        # World Y = (cam_y - 300) * 2
        ship_world_y = (self.cam_y - 300.0) * 2.0

        for i in range(num_samples):
            # Normalizado -0.5 a 0.5
            t = i / (num_samples - 1)
            offset_factor = (t - 0.5)
            
            # Ponto no mundo para amostrar
            sample_x = ship_world_x + offset_factor * scan_world_width
            sample_z = self.cam_z - look_ahead
            
            # Obtém altura
            if self.renderer3d:
                h = self.renderer3d.get_terrain_height(sample_x, sample_z)
            else:
                h = -99999
            
            # Se h for muito baixo (buraco/erro), clampa para visualização
            if h < -5000: h = -5000
            
            # Calcula posição Y no radar
            # Queremos mostrar a "Distância Vertical" (Clearance)
            # Se clearance = 0 (colisão), ponto está no CENTRO do radar (linha do horizonte/nave)
            # Não, melhor: Radar mostra PERFIL.
            # Base do radar = Nave Y - 1000.
            # Topo do radar = Nave Y + 200.
            # Assim, montanhas acima da nave aparecem altas.
            
            # Relativo à nave
            rel_h = h - ship_world_y
            
            # Escala visual do radar
            # Se rel_h = 0 (mesma altura), desenha no meio.
            # Se rel_h = -500 (chão longe), desenha em baixo.
            # Se rel_h = +200 (pico acima), desenha em cima.
            
            radar_scale_y = 0.15 # Ajuste visual
            px = rect.left + t * rect.width
            py = rect.centery - (rel_h * radar_scale_y)
            
            # Clampa no rect
            py = max(rect.top + 2, min(rect.bottom - 2, py))
            
            # Converte para int para evitar erro do Pygame com tipos numpy
            scan_points.append((int(px), int(py)))
            
        # Desenha linha do terreno
        if len(scan_points) > 1:
            pygame.draw.lines(surf, (0, 255, 0), False, scan_points, 2)

        # Inimigos no Radar (Canhões)
        if hasattr(self, 'enemies'):
            for e in self.enemies:
                if e['active']:
                    # Distância Frente (Z)
                    # cam_z diminui indo para frente. e['z'] é menor que cam_z.
                    dist = self.cam_z - e['z']
                    if 0 < dist < 20000:
                        # Mapeamento X (Mesma lógica do terreno)
                        # ship_world_x = (cam_x...) 
                        # relative_x = e['x'] - ship_world_x
                        # scan_world_width = 4000 (precisa ser maior para ver inimigos laterais?)
                        # O radar scan width era 4000. Se inimigo spawnar a 4000 de offset, aparece na borda.
                        
                        rel_x = e['x'] - ship_world_x
                        # Normaliza para -0.5 a 0.5 dentro do scan width
                        # scan_world_width = 4000 definido acima
                        norm_x = rel_x / scan_world_width
                        
                        # Mapeamento Y (Altitude relativa)
                        rel_h = e['y'] - ship_world_y
                        
                        px = rect.centerx + (norm_x * rect.width)
                        py = rect.centery - (rel_h * 0.15) # radar_scale_y
                        
                        # Clamp e Desenha
                        if rect.left <= px <= rect.right and rect.top <= py <= rect.bottom:
                            # Pisca
                            color = (255, 0, 0) if (pygame.time.get_ticks() % 500) < 250 else (150, 0, 0)
                            pygame.draw.circle(surf, color, (int(px), int(py)), 4)
            
        # Símbolo da Nave (Referência Fixa - "W" Amarelo)
        cw, ch = 30 * SCALE, 10 * SCALE
        cx, cy = rect.centerx, rect.centery
        ship_points = [
            (cx - cw/2, cy),           # Asa Esquerda Ponta
            (cx - cw/4, cy + ch),      # Asa Esquerda Baixo
            (cx, cy),                  # Centro
            (cx + cw/4, cy + ch),      # Asa Direita Baixo
            (cx + cw/2, cy)            # Asa Direita Ponta
        ]
        pygame.draw.lines(surf, (255, 220, 0), False, ship_points, 3) # Amarelo grosso
        # Ponto central (nariz)
        pygame.draw.circle(surf, (255, 220, 0), (int(cx), int(cy)), 2)

        # Altímetro (Barra lateral)
        # Altura normalizada (0 a 2000 * SCALE)
        # Ajuste para nova escala gigante
        max_alt_display = 600.0 * SCALE
        alt_norm = max(0, min(1.0, self.cam_y / max_alt_display))
        bar_h = rect.height * 0.8
        bar_x = rect.right + 10 * SCALE
        bar_y = rect.centery - bar_h/2
        
        # Moldura Alt
        pygame.draw.rect(surf, (50, 200, 100), (bar_x, bar_y, 10 * SCALE, bar_h), 1)
        # Preenchimento
        fill_h = bar_h * alt_norm
        
        # Garante inteiros para o Rect
        pygame.draw.rect(surf, (50, 255, 100), (int(bar_x), int(bar_y + bar_h - fill_h), int(10 * SCALE), int(fill_h)))
        
        # Texto ALT
        font = pygame.font.SysFont("Arial", int(16 * SCALE), bold=True)
        txt = font.render(f"ALT: {int(self.cam_y + 20)}", True, (150, 255, 180))
        surf.blit(txt, (bar_x + 15 * SCALE, bar_y))
        
        # Texto VEL
        v_kmh = int(self.scroll_speed / 10)
        txt_v = font.render(f"SPD: {v_kmh} MACH", True, (150, 255, 180))
        surf.blit(txt_v, (rect.left - 120 * SCALE, bar_y))

        # Texto STATUS
        status = "AUTOPILOT" if self.state == 'leveling' else "MANUAL"
        col = (255, 200, 50) if status == "MANUAL" else (100, 200, 255)
        txt_st = font.render(status, True, col)
        
        # Piscar se status manual acabou de ativar
        if status == "MANUAL" and (pygame.time.get_ticks() // 500) % 2 == 0:
             surf.blit(txt_st, (cx - txt_st.get_width()//2, rect.top - 20 * SCALE))
        elif status == "AUTOPILOT":
             surf.blit(txt_st, (cx - txt_st.get_width()//2, rect.top - 20 * SCALE))
