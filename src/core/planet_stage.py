import pygame
import random
import math
import os
from src.settings import *
from src.assets import get_resource_path

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
        self.use_3d = True
        self.cam_x = LARGURA / 2
        self.cam_y = 80 * SCALE
        self.cam_z = 0.0
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
        self.banking = 0.0
        
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
                self.state = 'playing'
                self.clouds = [] # Limpa nuvens de entrada
                self.entry_img = None
                
        elif self.state == 'playing':
            self.traveled_distance += self.scroll_speed * dt
            
            # Input handling for Viewfinder mode
            keys = pygame.key.get_pressed()
            move_speed = 300 * SCALE
            move_speed_y = 220 * SCALE
            dx = 0
            dy = 0
            target_bank = 0.0
            
            if keys[pygame.K_LEFT]:
                dx = -move_speed * dt
                target_bank = 0.15 # Bank right (horizon tilts right) when turning left? Or bank left?
                # Usually banking left (turning left) means the horizon tilts right (right side goes up).
                # Let's try positive angle = clockwise rotation.
                # If I bank left (turn left), the world rotates clockwise relative to me.
                target_bank = 0.12 
            elif keys[pygame.K_RIGHT]:
                dx = move_speed * dt
                target_bank = -0.12
            if keys[pygame.K_UP]:
                dy = move_speed_y * dt
            elif keys[pygame.K_DOWN]:
                dy = -move_speed_y * dt
            
            self.cam_x += dx
            self.cam_y = max(10 * SCALE, min(ALTURA - 50 * SCALE, self.cam_y + dy))
            # Smooth banking
            self.banking += (target_bank - self.banking) * 5.0 * dt
            
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
        else:
            # Interior escuro da cabine (base para máscara)
            screen.fill((12, 14, 18))
        
        if self.state == 'playing' or self.state == 'leaving':
            # renderiza cena 3D em surface offscreen
            scene = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
            target = scene
            if self.use_3d:
                self._draw_sky(target)
                segs = sorted(self.segments, key=lambda s: s['y'])
                tris = []
                if len(segs) >= 2:
                    h = 120 * SCALE
                    step = max(8, int(self.segment_height))
                    subdiv = 3
                    n = len(segs)
                    for i in range(1, n):
                        a = segs[i-1]
                        b = segs[i]
                        z1 = (n - i) * step
                        z2 = (n - i - 1) * step
                        w1 = a['w']
                        w2 = b['w']
                        cx1, cx2 = a['x'], b['x']
                        for sidx in range(subdiv):
                            t0 = sidx / subdiv
                            t1 = (sidx + 1) / subdiv
                            zA = z1 + (z2 - z1) * t0
                            zB = z1 + (z2 - z1) * t1
                            wA = w1 + (w2 - w1) * t0
                            wB = w1 + (w2 - w1) * t1
                            cA = cx1 + (cx2 - cx1) * t0
                            cB = cx1 + (cx2 - cx1) * t1
                            lx1 = cA - wA/2 + self._jitter(zA * 1.2, 'l')
                            rx1 = cA + wA/2 + self._jitter(zA * 1.2, 'r')
                            lx2 = cB - wB/2 + self._jitter(zB * 1.2, 'l')
                            rx2 = cB + wB/2 + self._jitter(zB * 1.2, 'r')
                            p1 = self._project(lx1, 0, zA)
                            p2 = self._project(rx1, 0, zA)
                            p3 = self._project(lx2, 0, zB)
                            p4 = self._project(rx2, 0, zB)
                            tris.append(((p1, p2, p3), (170, 150, 130)))
                            tris.append(((p2, p4, p3), (170, 150, 130)))
                            wl = [(lx1, 0, zA), (lx1, h, zA), (lx2, h, zB), (lx2, 0, zB)]
                            wr = [(rx1, 0, zA), (rx1, h, zA), (rx2, h, zB), (rx2, 0, zB)]
                            pl = [self._project(*v) for v in wl]
                            pr = [self._project(*v) for v in wr]
                            tris.append(((pl[0], pl[1], pl[2]), (100, 85, 70)))
                            tris.append(((pl[0], pl[2], pl[3]), (100, 85, 70)))
                            tris.append(((pr[0], pr[1], pr[2]), (100, 85, 70)))
                            tris.append(((pr[0], pr[2], pr[3]), (100, 85, 70)))
                            floor = [(lx1, h, zA), (rx1, h, zA), (rx2, h, zB), (lx2, h, zB)]
                            pf = [self._project(*v) for v in floor]
                            tris.append(((pf[0], pf[1], pf[2]), (70, 60, 50)))
                            tris.append(((pf[0], pf[2], pf[3]), (70, 60, 50)))
                tris.sort(key=lambda t: sum(p[2] for p in t[0]) / 3.0, reverse=True)
                for tri, col in tris:
                    pts = [(p[0], p[1]) for p in tri]
                    avgz = sum(p[2] for p in tri) / 3.0
                    avgx = sum(p[0] for p in tri) / 3.0
                    shade = self._apply_lighting(col, avgz, avgx)
                    pygame.draw.polygon(target, shade, pts)
            else:
                # 2D Fallback (not really used but kept for safety)
                pass
            
            self._draw_shot_traces(scene)
            # Blita a cena 3D diretamente na tela (sem máscara procedural)
            screen.blit(scene, (0, 0))

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

    def _draw_sky(self, surf):
        """Céu com gradiente e leve ruído para evitar aparência de teto."""
        bands = 36
        horizon = int(ALTURA * 0.42)
        top_col = (10, 12, 18)
        mid_col = (22, 26, 34)
        low_col = (32, 36, 44)
        for i in range(bands):
            t = i / float(bands - 1)
            if t < 0.6:
                c0 = top_col
                c1 = mid_col
                tt = t / 0.6
            else:
                c0 = mid_col
                c1 = low_col
                tt = (t - 0.6) / 0.4
            r = int(c0[0] + (c1[0] - c0[0]) * tt)
            g = int(c0[1] + (c1[1] - c0[1]) * tt)
            b = int(c0[2] + (c1[2] - c0[2]) * tt)
            y0 = int(t * horizon)
            y1 = int((t + 1.0 / bands) * horizon)
            pygame.draw.rect(surf, (r, g, b), (0, y0, LARGURA, max(1, y1 - y0)))
        # leve ruído
        noise_points = 200
        for _ in range(noise_points):
            x = random.randrange(0, LARGURA)
            y = random.randrange(0, horizon)
            a = random.randint(8, 18)
            col = (255, 255, 255, a)
            surf.fill(col, (x, y, 1, 1))

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
