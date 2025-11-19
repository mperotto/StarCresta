import pygame, math
from spacegame.core.scene import Scene
from spacegame.core import ui
from spacegame.entities.stars import CampoEstrelas
from spacegame.entities.player import Jogador as NewPlayer
from spacegame.entities.bullets import Tiro as PTiro, SuperTiro as PSuperTiro
from spacegame.settings import VELOCIDADE_TIRO
from spacegame.entities.enemies import GerenciadorDeTirosInimigos
from spacegame.entities.particles import GerenciadorDeParticulas
from spacegame.entities.pickups import GerenciadorDeUpgrades
from spacegame.systems.spawner import Spawner
from spacegame.systems.combat import resolve as resolve_combat
from spacegame.core.ecs import EventBus
from spacegame.systems.audio import AudioSystem

class GameScene(Scene):
    def __init__(self):
        self._legacy = None
        self._font = None
        self._font_big = None
        self._bg = None
        self._player = None
        self._shots = []
        self.enemies = []
        self.enemy_shots = GerenciadorDeTirosInimigos()
        self.particles = GerenciadorDeParticulas()
        self.upgrades = GerenciadorDeUpgrades()
        self._spawner = Spawner()
        self.bus = EventBus()
        self.audio = AudioSystem(self.bus)
        self._ufo_active = False
        self._last_state = None

    def enter(self):
        # For Phase 1, delegate to existing game to keep behavior
        try:
            import joguinho_poo as legacy
            self._legacy = legacy.Jogo()
            # sinaliza para não desenhar o próprio fundo
            setattr(self._legacy, 'external_background', True)
            # sinaliza para não desenhar o player (vamos desenhar o nosso)
            setattr(self._legacy, 'external_player', True)
            # sinaliza para não desenhar HUD/overlays
            setattr(self._legacy, 'external_ui', True)
            # redireciona criação de tiros do player para o nosso gerenciador
            self._install_firing_redirects()
            # neutraliza managers do legacy para evitar duplicidade
            self._neutralize_legacy_managers()
        except Exception:
            self._legacy = None
        self._font = ui.get_font(22)
        self._font_big = ui.get_font(48)
        # nosso fundo modular
        self._bg = CampoEstrelas(quantidade=70)
        # nosso player (usado para desenhar); posição será sincronizada do legacy
        if self._legacy is not None:
            j = self._legacy.jogador
            self._player = NewPlayer(j.x, j.y)
            # conectar a lista de tiros do legacy a uma shim apontando para nossos tiros
            class ShotsShim:
                def __init__(self, shared_list):
                    self.tiros = shared_list
                def criar(self, *_args, **_kwargs):
                    return
                def atualizar(self, *_args, **_kwargs):
                    return
                def desenhar(self, *_args, **_kwargs):
                    return
            self._legacy.tiros = ShotsShim(self._shots)

    def handle_event(self, ev):
        # eventos são processados pelo jogo legacy via lidar_com_eventos()
        return

    def update(self, dt: float):
        if self._legacy is not None:
            # Legacy game keeps its own event loop; here we just run its update paths
            # We mimic its main loop phases (without events) to keep drawing and logic moving
            if self._bg is not None:
                self._bg.atualizar(dt)
            # processar eventos pelo legacy
            try:
                self._legacy.lidar_com_eventos()
            except Exception:
                pass
            # atualiza nossos tiros antes do update do legacy, para colisões usarem posições certas
            self._update_shots(dt)
            # atualiza nossos managers
            self._dt = dt
            self._spawner.update(dt, self.enemies)
            for e in list(self.enemies):
                e.atualizar(dt)
            # inimigos que atiram (inclui UFO/Atirador)
            try:
                dif_mult = min(1.3, 1.0 + self._spawner.tempo_total * 0.01)
            except Exception:
                dif_mult = 1.0
            for e in self.enemies:
                if hasattr(e, 'tentar_atirar'):
                    try:
                        e.tentar_atirar(self.enemy_shots, self._legacy.jogador, dif_mult)
                    except Exception:
                        pass
            self.upgrades.atualizar(dt)
            self.enemy_shots.atualizar(dt)
            self.particles.atualizar(dt)
            # resolver combate
            resolve_combat(self)
            # eventos: UFO spawn/gone
            ufo_now = any(getattr(e, 'is_ufo', False) and not e.esta_morto() for e in self.enemies)
            if ufo_now and not self._ufo_active:
                self.bus.emit('ufo_spawned')
            if (not ufo_now) and self._ufo_active:
                self.bus.emit('ufo_gone')
            self._ufo_active = ufo_now
            # eventos: pause/resume via estado do legacy
            try:
                st = getattr(self._legacy, 'estado', None)
            except Exception:
                st = None
            if st != self._last_state:
                if st == 'pausado':
                    self.bus.emit('pause')
                elif st == 'jogando':
                    self.bus.emit('resume')
                elif st == 'game_over':
                    self.bus.emit('ufo_gone')
                    self.bus.emit('pause')
                self._last_state = st
            # atualizar áudio (doppler/pan)
            self.audio.update(self)
            # atualizar legacy minimamente (para HUD/FX)
            try:
                self._legacy.atualizar(0.0)
            except Exception:
                pass
            # sincroniza posição do player novo com o legacy para desenhar
            try:
                if self._player is not None and self._legacy is not None:
                    self._player.x = self._legacy.jogador.x
                    self._player.y = self._legacy.jogador.y
                    self._player.sincronizar_retangulo()
            except Exception:
                pass

    def draw(self, screen):
        if self._legacy is not None:
            # Draw using legacy renderer onto the same screen
            screen.fill((5, 8, 15))
            if self._bg is not None:
                self._bg.desenhar(screen)
            self._legacy.tela = screen  # share screen
            # desenhar nosso player antes do restante
            try:
                if self._player is not None:
                    self._player.desenhar(screen)
            except Exception:
                pass
            # desenhar nossos tiros
            self._draw_shots(screen)
            # desenhar nossos managers
            try:
                self.upgrades.desenhar(screen)
                self.enemy_shots.desenhar(screen)
                for e in self.enemies:
                    e.desenhar(screen)
                self.particles.desenhar(screen)
            except Exception:
                pass
            # nosso HUD e overlays
            self._draw_hud_and_overlays(screen)

    # -----------------
    # Tiros do player
    # -----------------
    def _install_firing_redirects(self):
        # substitui as funções de disparo do legacy para usarem nosso gerenciador
        def fire_normal():
            self._fire_normal()
        def fire_super():
            self._fire_super()
        try:
            self._legacy.disparar_normal = fire_normal
            self._legacy.disparar_super = fire_super
        except Exception:
            pass

    def _fire_normal(self):
        # define recarga do tiro normal no legacy
        try:
            self._legacy.jogador.tempo_recarga = 0.1
        except Exception:
            pass
        # som tiro
        s = getattr(self._legacy, 'sfx_shot', None)
        if s:
            try: s.play()
            except Exception: pass
        # criar tiros
        j = self._legacy.jogador
        cx = j.x + j.largura/2
        topy = j.y - 12
        speed = abs(VELOCIDADE_TIRO)
        base_ang = math.radians(12)
        if getattr(self._legacy, 'upgrade_super_timer', 0.0) > 0:
            angulos = [-base_ang, 0.0, +base_ang]
        else:
            angulos = [0.0]
        for ang in angulos:
            vx = speed * math.sin(ang)
            vy = -speed * math.cos(ang)
            self._shots.append(PTiro(cx - 3, topy, vx=vx, vy=vy))

    def _fire_super(self):
        # recarga via jogador
        try:
            # só ajustar recarga (evita criar objeto do legacy)
            self._legacy.jogador.tempo_recarga = 0.8
        except Exception:
            pass
        # som super
        s = getattr(self._legacy, 'sfx_super', None)
        if s:
            try: s.play()
            except Exception: pass
        # padrão: 1 reto ou V+reto
        j = self._legacy.jogador
        cx = j.x + j.largura/2
        topy = j.y - 18
        speed = abs(VELOCIDADE_TIRO)
        base_ang = math.radians(12)
        if getattr(self._legacy, 'upgrade_super_timer', 0.0) > 0:
            angulos = [-base_ang, 0.0, +base_ang]
        else:
            angulos = [0.0]
        for ang in angulos:
            vx = speed * math.sin(ang)
            vy = -speed * math.cos(ang)
            self._shots.append(PSuperTiro(cx - 12, topy, vx=vx, vy=vy))

    def _update_shots(self, dt: float):
        for t in self._shots:
            t.atualizar(dt)
        self._shots = [t for t in self._shots if not t.esta_morto()]

    def _draw_shots(self, screen):
        for t in self._shots:
            t.desenhar(screen)

    def _neutralize_legacy_managers(self):
        # Replace legacy managers to no-op where possible
        try:
            self._legacy.inimigos = []
            self._legacy.tiros_inimigos = type('TI', (), {'criar': lambda *_: None, 'atualizar': lambda *_: None, 'desenhar': lambda *_: None, 'tiros': []})()
            self._legacy.upgrades = type('U', (), {'criar': lambda *_: None, 'atualizar': lambda *_: None, 'desenhar': lambda *_: None, 'verificar_coleta_por_inimigos': lambda *_: None})()
            self._legacy.destrocos = type('D', (), {'criar': lambda *_: None, 'atualizar': lambda *_: None, 'desenhar': lambda *_: None})()
            self._legacy.particulas = type('P', (), {'criar': lambda *_: None, 'atualizar': lambda *_: None, 'desenhar': lambda *_: None})()
        except Exception:
            pass

    def _draw_hud_and_overlays(self, screen):
        # HUD basico
        try:
            upg = getattr(self._legacy, 'upgrade_super_timer', 0.0)
            sh = getattr(self._legacy, 'player_shield_timer', 0.0)
            upg_txt = f"{upg:0.1f}s" if upg > 0 else "—"
            shield_txt = f"{sh:0.1f}s" if sh > 0 else "—"
            hud = self._font.render(
                f"Pontuação: {self._legacy.pontuacao}  |  Vidas: {self._legacy.vidas}  |  Upgrade V: {upg_txt}  |  Shield: {shield_txt}",
                True, (220, 230, 255))
            screen.blit(hud, (10, 10))
        except Exception:
            pass
        # invulnerável blink
        try:
            if getattr(self._legacy, 'invul_timer', 0.0) > 0 and getattr(self._legacy, 'estado', '') == 'jogando':
                if int(pygame.time.get_ticks() / 100) % 2 == 0:
                    pygame.draw.rect(screen, (255,255,255), self._player.retangulo, 2)
        except Exception:
            pass
        # shield circle
        try:
            if getattr(self._legacy, 'player_shield_timer', 0.0) > 0:
                cx = int(self._player.x + self._player.largura/2)
                cy = int(self._player.y + self._player.altura/2)
                r = max(self._player.largura, self._player.altura)
                pygame.draw.circle(screen, (120,200,255), (cx, cy), int(r), 2)
        except Exception:
            pass
        # floating texts (+1 VIDA)
        try:
            fxs = getattr(self._legacy, 'fx_texts', [])
            for fx in fxs:
                surf = fx.get('surf'); t = fx.get('t',0.0); dur = fx.get('dur',1.6)
                if surf is None: continue
                pct = max(0.0, min(1.0, t / dur))
                alpha = int(255 * (1.0 - pct))
                dy = -26 * pct
                s2 = surf.copy(); s2.set_alpha(alpha)
                x = int(fx.get('x',0) - s2.get_width()/2)
                y = int(fx.get('y',0) + dy)
                screen.blit(s2, (x, y))
        except Exception:
            pass
        # overlays
        estado = getattr(self._legacy, 'estado', '')
        if estado == 'game_over':
            overlay = pygame.Surface(screen.get_size())
            overlay.set_alpha(140)
            overlay.fill((10,10,16))
            screen.blit(overlay, (0,0))
            texto1 = self._font_big.render("GAME OVER", True, (255, 230, 230))
            texto2 = self._font.render("Pressione R/Enter/Espaço para reiniciar", True, (220, 230, 255))
            texto3 = self._font.render("ESC para sair", True, (200, 210, 230))
            W = screen.get_width(); H = screen.get_height()
            screen.blit(texto1, (W//2 - texto1.get_width()//2, H//2 - 40))
            screen.blit(texto2, (W//2 - texto2.get_width()//2, H//2 + 10))
            screen.blit(texto3, (W//2 - texto3.get_width()//2, H//2 + 36))
            # shockwave rings
            try:
                if getattr(self._legacy, 'game_over_fx_active', False):
                    cx, cy = self._legacy.game_over_fx_pos
                    t = self._legacy.game_over_fx_t
                    base = 30
                    r = int(base + 140 * (1 - math.exp(-1.6 * max(0.0, t))))
                    pygame.draw.circle(screen, (230,240,255), (int(cx), int(cy)), max(1,r), 3)
                    if r>20:
                        pygame.draw.circle(screen, (180,220,255), (int(cx), int(cy)), max(1,r-12), 2)
            except Exception:
                pass
        elif estado == 'pausado':
            overlay = pygame.Surface(screen.get_size())
            overlay.set_alpha(140)
            overlay.fill((10,10,16))
            screen.blit(overlay, (0,0))
            t1 = self._font_big.render("PAUSADO", True, (230, 240, 255))
            t2 = self._font.render("Tem certeza que deseja sair?", True, (220, 230, 255))
            t3 = self._font.render("S para sair  |  N/Esc/Enter/Espaço para continuar", True, (200, 210, 230))
            W = screen.get_width(); H = screen.get_height()
            screen.blit(t1, (W//2 - t1.get_width()//2, H//2 - 50))
            screen.blit(t2, (W//2 - t2.get_width()//2, H//2 + 0))
            screen.blit(t3, (W//2 - t3.get_width()//2, H//2 + 30))
        else:
            screen.fill((10, 10, 16))
            ui.draw_text_centered(screen, "Game bootstrap (legacy missing)", self._font, (230,240,255), screen.get_width()//2, screen.get_height()//2)

    def exit(self):
        pass
