import pygame
import sys
import math
import os
import random
from src.settings import *
from src.assets import carregar_som, get_resource_path
from src.sprites.player import Jogador, TargetModule
from src.sprites.projectile import Tiro, SuperTiro, LaserBeam
from src.sprites.enemy import Asteroide, InimigoDescendo, InimigoZigueZague, InimigoAtirador
from src.sprites.items import Upgrade
from src.sprites.boss import Boss
from src.core.managers import (
    GerenciadorDeTiros, 
    GerenciadorDeInimigos, 
    GerenciadorDeTirosInimigos, 
    GerenciadorDeUpgrades, 
    GerenciadorDeDestrocos
)
from src.core.particles import GerenciadorDeParticulas, CampoEstrelas
from src.core.score import ScoreManager
from src.ui.menu import Menu, GameOverScreen
from src.core.event_handler import processar_eventos

class Jogo:
    def __init__(self):
        # tentar reduzir latência de áudio
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
        except Exception:
            pass
        pygame.init()
        pygame.display.set_caption("StarCresta")
        
        # Detecta resolução do monitor
        info = pygame.display.Info()
        monitor_w, monitor_h = info.current_w, info.current_h
        
        # Define resolução alvo (mantendo aspect ratio se possível, ou usando nativa)
        # Se o monitor for menor que 1920x1080, ajusta
        if monitor_w < LARGURA or monitor_h < ALTURA:
            self.largura_tela = monitor_w
            self.altura_tela = monitor_h
            # Recalcula SCALE para renderização (opcional, mas complexo pois afeta lógica)
            # Melhor abordagem: Renderizar em surface interna 1920x1080 e escalar para tela
            self.usar_escala = True
        else:
            self.largura_tela = LARGURA
            self.altura_tela = ALTURA
            self.usar_escala = False
            
        self.tela_real = pygame.display.set_mode((self.largura_tela, self.altura_tela), pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
        self.tela = pygame.Surface((LARGURA, ALTURA)) # Surface interna lógica
        
        self.relogio = pygame.time.Clock()
        self.fonte = pygame.font.SysFont(None, 22)
        self.fonte_grande = pygame.font.SysFont(None, 48)

        self.score_manager = ScoreManager()
        self.menu = Menu(self)
        self.game_over_screen = GameOverScreen(self)

        self.jogador = Jogador(LARGURA/2 - 18, ALTURA - 80)
        self.tiros = GerenciadorDeTiros()
        self.inimigos = GerenciadorDeInimigos()
        self.inimigos.spawn_delay = 1.0
        self.particulas = GerenciadorDeParticulas()
        # menos estrelas no fundo (cerca de 1/3 do original)
        estrelas_qtd = int(45 * (LARGURA/BASE_LARGURA) * (ALTURA/BASE_ALTURA) / 1.0)
        self.fundo = CampoEstrelas(quantidade=estrelas_qtd, planetas=2)
        self.tiros_inimigos = GerenciadorDeTirosInimigos()
        
        self.pontuacao = 0
        self.estado = 'menu'  # 'menu' | 'jogando' | 'pausado' | 'game_over'
        self.carregando_super = False
        self.tempo_carregando = 0.0
        self.sinalizou_super_pronto = False
        self.upgrade_super_timer = 0.0  # buff temporário (s)
        self.player_shield_timer = 0.0
        self.vidas = 3
        self.invul_timer = 0.0
        
        self.upgrades = GerenciadorDeUpgrades()
        self.destrocos = GerenciadorDeDestrocos()
        
        # carregar sons/música
        self._carregar_audio()
        self._tocar_musica()
        
        # liga som de tiro inimigo (se disponível)
        if hasattr(self, 'sfx_enemy_shot') and self.sfx_enemy_shot:
            setattr(self.tiros_inimigos, 'sfx_shot', self.sfx_enemy_shot)
            
        # controle do som do UFO
        self.ufo_channel = None
        self.ufo_siren_on = False
        # FX de Game Over (explosão lenta)
        self.game_over_fx_active = False
        self.game_over_fx_t = 0.0
        self.game_over_fx_pos = (LARGURA//2, ALTURA//2)
        self.game_over_fx_emit = 0.0
        # textos flutuantes (ex.: "+1 VIDA")
        self.fx_texts = []
        self.entering_initials = False
        self.initials_input = ""
        self.new_score_registered = False
        self.boss_spawn_index = 0
        self.fase = 1
        self.boss_cleared = 0
        self.boss_add_timer = 0.0
        self.fase_banner_timer = 5.0
        self.laser_wave_expire = None
        self.laser_wave_block = None
        self.laser_timer = None
        self.laser_beam_timer = 0.0
        self.laser_beam_active = False
        
        # Variáveis de acoplamento
        self.target_module = None
        self.docking_timer = 0.0
        self.docking_success = False

    def _carregar_audio(self):
        self.sfx_shot = carregar_som('laser1.wav', 0.28) or carregar_som('shot.wav', 0.28)
        self.sfx_super = carregar_som('laser_heavy.wav', 0.34) or carregar_som('super.wav', 0.34)
        self.sfx_explosion_small = carregar_som('explosion_small.wav', 0.45)
        self.sfx_explosion_big = carregar_som('explosion_big.wav', 0.52)
        self.sfx_powerup = carregar_som('powerup.wav', 0.3)
        self.sfx_damage = carregar_som('damage.wav', 0.35)
        self.sfx_enemy_shot = carregar_som('laser2.wav', 0.24) or carregar_som('laser_2.wav', 0.24) or carregar_som('enemy_shot.wav', 0.24)
        # Sirene/ambiente do UFO (opcional). Toca em loop enquanto houver UFO na tela.
        self.sfx_ufo = (
            carregar_som('ufo_siren.wav', 0.18)
            or carregar_som('ufo.wav', 0.18)
            or carregar_som('siren.wav', 0.18)
            or carregar_som('ambulancia.wav', 0.18)
            or carregar_som('ufo_loop.wav', 0.18)
        )
        self.music_path = None
        for cand in ['bg_loop.ogg', 'bg_loop.mp3', 'bg_loop.wav']:
            p = os.path.join('sound', cand)
            full_p = get_resource_path(p)
            if os.path.exists(full_p):
                self.music_path = full_p
                break
                break
        
        self.boss_music_path = None
        for cand in ['boss_theme.mp3', 'boss_theme.ogg', 'boss_theme.wav']:
            p = os.path.join('sound', cand)
            if os.path.exists(p):
                self.boss_music_path = p
                break

    def _tocar_musica(self, path=None):
        target = path if path else self.music_path
        if target:
            try:
                pygame.mixer.music.load(target)
                pygame.mixer.music.set_volume(0.25)
                pygame.mixer.music.play(-1)
            except Exception:
                pass

    def reiniciar(self):
        self.pontuacao = 0
        self.vidas = VIDAS_INICIAIS
        self.jogador = Jogador(LARGURA/2 - 18, ALTURA - 80)
        self.tiros = GerenciadorDeTiros()
        self.inimigos = GerenciadorDeInimigos()
        self.inimigos.spawn_delay = 1.0
        self.tiros_inimigos = GerenciadorDeTirosInimigos()
        # reconectar sfx se necessário
        if hasattr(self, 'sfx_enemy_shot') and self.sfx_enemy_shot:
            setattr(self.tiros_inimigos, 'sfx_shot', self.sfx_enemy_shot)
        self.particulas = GerenciadorDeParticulas()
        self.upgrades = GerenciadorDeUpgrades()
        self.destrocos = GerenciadorDeDestrocos()
        self.carregando_super = False
        self.tempo_carregando = 0.0
        self.sinalizou_super_pronto = False
        self.upgrade_super_timer = 0.0
        self.player_shield_timer = 0.0
        self.invul_timer = 0.0
        self.game_over_fx_active = False
        self.fx_texts = []
        self.entering_initials = False
        self.initials_input = ""
        self.new_score_registered = False
        self.boss_spawn_index = 0
        self.fase = 1
        self.boss_cleared = 0
        self.boss_add_timer = 0.0
        self.fase_banner_timer = 5.0
        self.laser_wave_expire = None
        self.laser_wave_block = None
        self.laser_timer = None
        self.laser_beam_timer = 0.0
        self.laser_beam_active = False
        # parar sons de ufo
        if self.ufo_channel:
            try: self.ufo_channel.stop()
            except: pass
        self.ufo_channel = None
        self.ufo_siren_on = False
        self.boss_spawned = False
        # reiniciar música normal
        self._tocar_musica(self.music_path)
        self.estado = 'jogando'

    def _iniciar_entrada_iniciais(self):
        self.entering_initials = self.score_manager.qualifica(self.pontuacao)
        self.initials_input = ""
        self.new_score_registered = not self.entering_initials

    def _registrar_iniciais(self):
        if self.new_score_registered:
            self.entering_initials = False
            return
        nome = (self.initials_input or "").upper()[:3].ljust(3, '_')
        self.score_manager.registrar(nome, self.pontuacao, fase=self.fase)
        self.entering_initials = False
        self.new_score_registered = True

    def _desenhar_banner_fase(self):
        if self.fase_banner_timer > 0.0:
            fase_txt = self.fonte_grande.render(f"Fase {self.fase}", True, (230, 235, 255))
            box = fase_txt.get_rect(center=(LARGURA//2, ALTURA//2))
            self.tela.blit(fase_txt, box)

# ... (inside atualizar)

        # Spawn automático do Boss (ex: a cada 5 ondas ou tempo)
        # Se onda > 0 e múltiplo de 5, e boss ainda não spawnou nesta sequência
        if self.inimigos.onda > 0 and self.inimigos.onda % BOSS_WAVE_INTERVAL == 0:
            if not self.boss_spawned and not self.inimigos.boss_ativo and self.estado == 'jogando':
                self.inimigos.spawnar_boss()
                self.boss_spawned = True
                if self.boss_music_path:
                    self._tocar_musica(self.boss_music_path)


        # Boss morto: explosão épica e volta música normal
        if getattr(self.inimigos, 'boss_killed', False):
            self.inimigos.boss_killed = False
            pos = getattr(self.inimigos, 'boss_killed_pos', None)
            self.inimigos.boss_killed_pos = None
            self.boss_spawned = False  # Permite spawn de novo boss
            
            # Explosão épica
            if pos is not None:
                cx, cy = pos
            else:
                cx = LARGURA // 2
                cy = 100
                
            # Múltiplas ondas de partículas
            for i in range(3):
                intensidade = 40 - i * 8
                raio = 50 + i * 20
                cores = [(255, 150, 50), (255, 200, 100), (255, 255, 200)]
                self.particulas.spawn_ao_redor(cx, cy, intensidade=intensidade, raio=raio, cores=cores, vel_base=120, vel_var=180)
            
            # Som de explosão grande (volume maior para o boss)
            if hasattr(self, 'sfx_explosion_big') and self.sfx_explosion_big:
                try:
                    # Aumenta temporariamente o volume para o boss
                    original_vol = self.sfx_explosion_big.get_volume()
                    self.sfx_explosion_big.set_volume(0.8)
                    self.sfx_explosion_big.play()
                    # Restaura volume original após 100ms (aproximado)
                    self.sfx_explosion_big.set_volume(original_vol)
                except Exception:
                    pass
            
            # Volta música normal
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
            if self.music_path:
                self._tocar_musica(self.music_path)
            
            # Pontuação bônus
            self.pontuacao += PONTOS_BONUS_BOSS
            
            # Inicia celebração antes do acoplamento
            if self.jogador.stage < 3:
                self.estado = 'celebration'
                self.celebration_timer = 3.0 # 3 segundos de comemoração
                self.inimigos.inimigos.clear()
                self.tiros.tiros.clear()
                self.tiros_inimigos.tiros.clear()
                self.destrocos.destrocos.clear()
            else:
                # Continua jogo normal
                pass

# ... (inside sucesso_acoplamento)

    def sucesso_acoplamento(self):
        self.jogador.stage += 1
        self.jogador.vida = VIDAS_INICIAIS # Recupera vida? Opcional
        self.pontuacao += PONTOS_POR_ACOPLAMENTO
        self.estado = 'jogando'
        self.target_module = None
        
        # Reseta gerenciador de inimigos para reiniciar ondas
        self.inimigos.boss_ativo = False
        self.inimigos.boss_killed = False
        self.inimigos.resetar_spawn(atraso=2.0) # Reinicia dificuldade/ondas com respiro
        self.inimigos.inimigos.clear() # Garante limpo
        self.boss_spawned = False
        
        # Som de powerup
        if hasattr(self, 'sfx_powerup'):
            try: self.sfx_powerup.play()
            except: pass

    def lidar_com_eventos(self):
        processar_eventos(self)

    def atualizar(self, dt):
        # atualiza fundo e partículas mesmo em game over
        self.fundo.atualizar(dt)
        self.particulas.atualizar(dt)
        self.destrocos.atualizar(dt)
        # atualizar textos flutuantes
        novos = []
        for fx in self.fx_texts:
            fx['t'] += dt
            if fx['t'] <= fx.get('dur', 1.6):
                novos.append(fx)
        self.fx_texts = novos
        if self.fase_banner_timer > 0.0:
            self.fase_banner_timer = max(0.0, self.fase_banner_timer - dt)
        
        if self.estado == 'menu':
            return

        # Estados que não são de jogo ativo mas precisam de update específico
        if self.estado == 'docking':
            self.atualizar_acoplamento(dt)
            return
            
        if self.estado == 'celebration':
            self.atualizar_celebracao(dt)
            return

        if self.estado != 'jogando':
            # Atualiza FX de Game Over (explosão lenta)
            if getattr(self, 'game_over_fx_active', False):
                self.game_over_fx_t += dt
                # emitir algumas partículas adicionais nos primeiros 1.6s
                if self.game_over_fx_t < 1.6:
                    self.game_over_fx_emit += dt
                    while self.game_over_fx_emit >= 0.08:
                        self.game_over_fx_emit -= 0.08
                        cx, cy = self.game_over_fx_pos
                        cores = [(255, 220, 180), (255, 240, 220), (200, 230, 255)]
                        self.particulas.spawn_ao_redor(cx, cy, intensidade=6, raio=30, cores=cores, vel_base=60, vel_var=90)
            # se não está jogando, garanta que a sirene do UFO pare
            if getattr(self, 'ufo_siren_on', False):
                try:
                    if self.ufo_channel is not None:
                        self.ufo_channel.stop()
                except Exception:
                    pass
                self.ufo_channel = None
                self.ufo_siren_on = False
            return
            
        # Atualiza timers de power-ups
        if self.player_shield_timer > 0:
            self.player_shield_timer = max(0.0, self.player_shield_timer - dt)

        if self.upgrade_super_timer > 0:
            self.upgrade_super_timer = max(0.0, self.upgrade_super_timer - dt)
            # Se acabou o tempo, volta nível da arma (opcional, ou mantém até morrer)
            # Neste design, parece que o nível da arma é permanente até morrer, 
            # mas o timer pode ser para outro efeito ou apenas visual.
            # Se o 'v' aumenta nivel_arma permanentemente, o timer pode ser só para feedback.
            # Mas se for temporário, deveria reduzir aqui. 
            # O código original do 'v' aumenta self.jogador.nivel_arma.
            # Vamos assumir que o timer é apenas visual ou para um estado 'powered up' futuro.

        # Laser contínuo expira ao fim da próxima onda
        if self.laser_wave_expire is not None and self.inimigos.onda >= self.laser_wave_expire:
            self.laser_wave_expire = None
            self.laser_beam_active = False
            self.laser_timer = None
        if self.laser_wave_block is not None:
            bloco = max(0, self.inimigos.onda) // BOSS_WAVE_INTERVAL
            if bloco != self.laser_wave_block:
                self.laser_wave_block = None
                self.laser_beam_active = False

        self.jogador.atualizar(dt)
        # Laser contínuo (segurar espaço)
        if self.laser_wave_expire is not None or self.laser_wave_block is not None:
            # sempre ativo até expirar a wave/bloco
            self.laser_beam_timer = max(0.0, self.laser_beam_timer - dt)
            if self.laser_beam_timer <= 0.0:
                self._fire_laser_beam()
                self.laser_beam_timer = 0.05

        self.tiros.atualizar(dt)
        # ajusta dificuldade dinâmica para os gerenciadores
        self.inimigos.fase = self.fase
        self.upgrades.fase = getattr(self, 'fase', 1)
        # passa posição do jogador para bosses aplicarem mergulho
        for inim in self.inimigos.inimigos:
            if isinstance(inim, Boss):
                inim.target_player_x = self.jogador.x + self.jogador.largura/2
        self.inimigos.atualizar(dt)
        try:
            player_hitboxes = self.jogador.get_segment_rects()
        except Exception:
            player_hitboxes = [self.jogador.retangulo]
        # controlar sirene do UFO: liga quando houver pelo menos um ativo; desliga quando não houver
        try:
            ufo_ativo = any(isinstance(i, DiscoVoador) and not i.esta_morto() for i in self.inimigos.inimigos)
        except Exception:
            ufo_ativo = False
        if ufo_ativo and not getattr(self, 'ufo_siren_on', False) and getattr(self, 'sfx_ufo', None):
            try:
                ch = pygame.mixer.find_channel()
                if ch is not None:
                    ch.play(self.sfx_ufo, loops=-1)
                    self.ufo_channel = ch
                    self.ufo_siren_on = True
            except Exception:
                pass
        # ajustar volume/pan para efeito de aproximação/afastamento e posição
        if ufo_ativo and getattr(self, 'ufo_siren_on', False) and self.ufo_channel is not None:
            try:
                # pega o UFO mais próximo do centro para basear o áudio
                ufos = [i for i in self.inimigos.inimigos if isinstance(i, DiscoVoador) and not i.esta_morto()]
                if ufos:
                    u = min(ufos, key=lambda obj: abs((obj.x + obj.largura/2) - (LARGURA/2)))
                    ux = u.x + u.largura/2
                    cx = LARGURA / 2.0
                    # normaliza posição (-1 na esquerda, +1 na direita)
                    norm = max(-1.0, min(1.0, (ux - cx) / cx))
                    # envelope de volume: baixo nas bordas, máximo no centro
                    # escala de 0.35 (bordas) a 1.0 (centro)
                    vol_scale = 0.35 + 0.65 * (1.0 - abs(norm)) ** 0.8
                    # leve viés de doppler: um pouco mais alto quando se aproxima, menor ao afastar
                    aproximando = (u.direcao > 0 and ux < cx) or (u.direcao < 0 and ux > cx)
                    vol_scale *= 1.06 if aproximando else 0.94
                    vol_scale = max(0.1, min(1.0, vol_scale))
                    # panorama estéreo
                    left = vol_scale * (1.0 - norm) * 0.5
                    right = vol_scale * (1.0 + norm) * 0.5
                    self.ufo_channel.set_volume(left, right)
            except Exception:
                pass

        if (not ufo_ativo) and getattr(self, 'ufo_siren_on', False):
            try:
                if self.ufo_channel is not None:
                    self.ufo_channel.stop()
            except Exception:
                pass
            self.ufo_channel = None
            self.ufo_siren_on = False
        self.upgrades.atualizar(dt)
        self.tiros_inimigos.atualizar(dt)
        # inimigos podem coletar upgrades
        self.upgrades.verificar_coleta_por_inimigos(self.inimigos)

        # colisões: tiros x inimigos
        abates = self.inimigos.verificar_colisoes_com_tiros(self.tiros, self.destrocos, upgrades=self.upgrades)
        self.pontuacao += abates  # 1 ponto por inimigo morto

        # colisão: jogador x inimigos (perde vida; com invencibilidade curta)
        if self.invul_timer > 0:
            self.invul_timer = max(0.0, self.invul_timer - dt)
        else:
            inimigo = self.inimigos.verificar_colisao_com_jogador(self.jogador)
            if inimigo:
                # se for asteroide e escudo do player estiver ativo, ignora
                if isinstance(inimigo, Asteroide) and self.player_shield_timer > 0:
                    inimigo = None
            if inimigo:
                # chefão não morre por colisão com o jogador
                if not isinstance(inimigo, Boss):
                    inimigo.matar()
                
                # Tenta reduzir estágio primeiro
                perdeu_vida = self.jogador.receber_dano()
                
                if perdeu_vida:
                    self.vidas -= 1
                else:
                    self.invul_timer = 2.0 # Invencibilidade ao perder parte
                    
                # som de dano
                # som de dano
                if hasattr(self, 'sfx_damage') and self.sfx_damage:
                    try:
                        self.sfx_damage.play()
                    except Exception:
                        pass
                # efeito ao ser atingido (mini explosão e partículas)
                cx = self.jogador.x + self.jogador.largura/2
                cy = self.jogador.y + self.jogador.altura/2
                self.particulas.spawn_ao_redor(cx, cy, intensidade=22, raio=30,
                                               cores=[(255, 160, 160), (255, 200, 200), (200, 230, 255)], vel_base=70, vel_var=140)
                if hasattr(self, 'sfx_explosion_small') and self.sfx_explosion_small:
                    try: self.sfx_explosion_small.play()
                    except Exception: pass
                if self.vidas <= 0:
                    # efeito de explosão da nave ao morrer
                    cx = self.jogador.x + self.jogador.largura/2
                    cy = self.jogador.y + self.jogador.altura/2
                    # partículas mais intensas e azuladas/claras
                    self.particulas.spawn_ao_redor(cx, cy, intensidade=36, raio=34,
                                                   cores=[(255, 200, 200), (255, 240, 220), (180, 220, 255)],
                                                   vel_base=80, vel_var=160)
                    # som de explosão grande se disponível
                    if hasattr(self, 'sfx_explosion_big') and self.sfx_explosion_big:
                        try: self.sfx_explosion_big.play()
                        except Exception: pass
                    elif hasattr(self, 'sfx_explosion_small') and self.sfx_explosion_small:
                        try: self.sfx_explosion_small.play()
                        except Exception: pass
                    # fade na música ao entrar em game over
                    try:
                        pygame.mixer.music.fadeout(1200)
                    except Exception:
                        pass
                    # inicia FX de Game Over mais lenta
                    self.game_over_fx_active = True
                    self.game_over_fx_t = 0.0
                    self.game_over_fx_pos = (cx, cy)
                    self.game_over_fx_emit = 0.0
                    self.jogador.matar()
                    self.estado = 'game_over'
                    self._iniciar_entrada_iniciais()
                else:
                    self.invul_timer = 1.8
                    # anima respawn: traz a nave de baixo pra posição padrão
                    self.jogador.y = ALTURA + 30
                    try:
                        self.jogador.spawn_anim = 1.2
                    except Exception:
                        pass

            # colisão: jogador x destroços (também causa dano)
            if self.estado == 'jogando' and self.invul_timer == 0.0:
                for d in self.destrocos.destrocos:
                    hitado = False
                    for hb in player_hitboxes:
                        if d.retangulo.colliderect(hb):
                            hitado = True
                            break
                    if not hitado:
                        continue
                    if self.player_shield_timer > 0:
                        continue

                    # Tenta reduzir estágio primeiro
                    perdeu_vida = self.jogador.receber_dano()
                    if perdeu_vida:
                        self.vidas -= 1
                    else:
                        self.invul_timer = 2.0

                    cx = self.jogador.x + self.jogador.largura/2
                    cy = self.jogador.y + self.jogador.altura/2
                    self.particulas.spawn_ao_redor(cx, cy, intensidade=20, raio=28,
                                                   cores=[(255, 160, 160), (255, 200, 200), (200, 230, 255)], vel_base=70, vel_var=140)
                    if hasattr(self, 'sfx_explosion_small') and self.sfx_explosion_small:
                        try: self.sfx_explosion_small.play()
                        except Exception: pass
                    if self.vidas <= 0:
                        # explosão da nave por dano de destroços
                        cx = self.jogador.x + self.jogador.largura/2
                        cy = self.jogador.y + self.jogador.altura/2
                        self.particulas.spawn_ao_redor(cx, cy, intensidade=32, raio=32,
                                                       cores=[(255, 200, 200), (255, 240, 220), (180, 220, 255)],
                                                       vel_base=80, vel_var=160)
                        if hasattr(self, 'sfx_explosion_big') and self.sfx_explosion_big:
                            try: self.sfx_explosion_big.play()
                            except Exception: pass
                        elif hasattr(self, 'sfx_explosion_small') and self.sfx_explosion_small:
                            try: self.sfx_explosion_small.play()
                            except Exception: pass
                        # fade na música ao entrar em game over
                        try:
                            pygame.mixer.music.fadeout(1200)
                        except Exception:
                            pass
                        # inicia FX de Game Over mais lenta
                        self.game_over_fx_active = True
                        self.game_over_fx_t = 0.0
                        self.game_over_fx_pos = (cx, cy)
                        self.game_over_fx_emit = 0.0
                        self.jogador.matar()
                        self.estado = 'game_over'
                        self._iniciar_entrada_iniciais()
                    else:
                        self.invul_timer = 1.8
                        # anima respawn vindo de baixo
                        self.jogador.y = ALTURA + 30
                        try:
                            self.jogador.spawn_anim = 1.2
                        except Exception:
                            pass
                    break

        # auto-carregamento do super quando n?o est? atirando
        if self.estado == 'jogando' and self.laser_wave_expire is None:
            teclas = pygame.key.get_pressed()
            pressionando_tiro = teclas[pygame.K_SPACE]
            if not pressionando_tiro:
                if not self.carregando_super:
                    self.carregando_super = True
                    self.tempo_carregando = 0.0
                    self.sinalizou_super_pronto = False
            else:
                self.carregando_super = False

        # carregamento do super: acumula tempo e spawna partículas
        if getattr(self, 'carregando_super', False):
            self.tempo_carregando += dt
            cx = self.jogador.x + self.jogador.largura/2
            cy = self.jogador.y + self.jogador.altura/2
            # Só mostra partículas enquanto carrega de verdade (>= 0.2s)
            if self.tempo_carregando >= 0.2:
                # intensidade aumenta até o máximo em 1.0s
                fator = min(1.0, (self.tempo_carregando - 0.2) / 0.8)
                intensidade = 4 + int(8 * fator)
                # cores quentes enquanto < 1.5s, frias quando pronto
                if self.tempo_carregando < 1.0:
                    cores = [(255, 235, 120), (255, 210, 100), (255, 250, 180)]
                else:
                    cores = [(120, 255, 255), (180, 255, 255), (200, 255, 240)]
                self.particulas.spawn_ao_redor(cx, cy, intensidade=intensidade, raio=26, cores=cores, vel_base=20, vel_var=60)
            # Ao atingir 1.5s pela primeira vez, mostrar um burst visual
            if (not self.sinalizou_super_pronto) and self.tempo_carregando >= 1.0:
                self.sinalizou_super_pronto = True
                self.particulas.spawn_ao_redor(cx, cy, intensidade=28, raio=30,
                                               cores=[(150, 255, 255), (220, 255, 255), (255, 255, 255)],
                                               vel_base=80, vel_var=120)

        # Verificar upgrades
        efeitos = self.upgrades.verificar_coleta(self.jogador)
        for efeito in efeitos:
            if efeito == 'v':
                # upgrade de tiro
                if self.jogador.nivel_arma < 3:
                    self.jogador.nivel_arma += 1
                self.upgrade_super_timer += 10.0
                if hasattr(self, 'sfx_powerup') and self.sfx_powerup:
                    try:
                        self.sfx_powerup.play()
                    except Exception:
                        pass
            elif efeito == 'shield':
                self.player_shield_timer += 10.0  # Acumula tempo
                if hasattr(self, 'sfx_powerup') and self.sfx_powerup:
                    try:
                        self.sfx_powerup.play()
                    except Exception:
                        pass
            elif efeito == 'health':
                if self.vidas < 5:
                    self.vidas += 1
                    # Som específico para vida (usa powerup por enquanto)
                    if hasattr(self, 'sfx_powerup') and self.sfx_powerup:
                        try:
                            self.sfx_powerup.play()
                        except Exception:
                            pass
                else:
                    self.pontuacao += 100 # Vida cheia = pontos
            elif efeito == 'laser':
                # dura até o final do bloco de waves atual (antes do próximo boss)
                onda_atual = max(0, self.inimigos.onda)
                self.laser_wave_block = onda_atual // BOSS_WAVE_INTERVAL
                self.laser_wave_expire = None
                self.laser_timer = None
                self.laser_beam_timer = 0.0
                self.laser_beam_active = False
                if hasattr(self, 'sfx_powerup') and self.sfx_powerup:
                    try:
                        self.sfx_powerup.play()
                    except Exception:
                        pass

        # colisão destroços x inimigos (dano e abates incrementados)
        abates_destrocos = self.destrocos.colidir_com_inimigos(self.inimigos)
        if abates_destrocos:
            self.pontuacao += abates_destrocos

        # colisão tiros x destroços (tiny quebram)
        self.destrocos.colidir_com_tiros(self.tiros)

        # recompensa: vida extra ao abater um UFO
        if getattr(self.inimigos, 'ufo_killed', False):
            self.inimigos.ufo_killed = False
            pos = getattr(self.inimigos, 'ufo_killed_pos', None)
            self.inimigos.ufo_killed_pos = None
            self.vidas += 1
            # feedback visual/sonoro
            if pos is not None:
                cx, cy = pos
            else:
                cx = self.jogador.x + self.jogador.largura/2
                cy = self.jogador.y + self.jogador.altura/2
            try:
                cores = [(140, 255, 200), (180, 255, 220), (220, 255, 255)]
                self.particulas.spawn_ao_redor(cx, cy, intensidade=18, raio=28, cores=cores, vel_base=70, vel_var=120)
            except Exception:
                pass
            # drop especial: laser cont?nuo (menos frequente em fases avan?adas)
            drop_chance = max(0.2, 0.6 * (0.8 ** max(0, self.fase - 1)))
            if random.random() < drop_chance:
                try:
                    self.upgrades.criar(Upgrade(cx - S(9), cy, tipo='laser', velocidade=80))
                except Exception:
                    pass
            if hasattr(self, 'sfx_powerup') and self.sfx_powerup:
                try:
                    self.sfx_powerup.play()
                except Exception:
                    pass
        
        # Spawn automático do Boss (ex: a cada 5 ondas ou tempo)
        # Se onda > 0 e múltiplo de 5, e boss ainda não spawnou nesta sequência
        if self.inimigos.onda > 0 and self.inimigos.onda % BOSS_WAVE_INTERVAL == 0:
            if not self.boss_spawned and not self.inimigos.boss_ativo and self.estado == 'jogando':
                quantidade = min(3, 1 + max(0, self.fase - 1))
                self.inimigos.spawnar_boss(quantidade=quantidade, fase=self.fase)
                self.boss_spawn_index += 1
                self.boss_spawned = True
                self.inimigos.boss_ativo = True
                if self.boss_music_path:
                    self._tocar_musica(self.boss_music_path)

        # adds durante bosses após o quarto
        if self.inimigos.boss_ativo and self.boss_spawn_index >= 4:
            self.boss_add_timer = max(0.0, self.boss_add_timer - dt)
            if self.boss_add_timer <= 0.0:
                self.boss_add_timer = 2.2
                tipo = random.choice(['zig', 'atirador', 'desc'])
                x = random.randint(40, LARGURA - 80)
                if tipo == 'atirador':
                    self.inimigos.criar(InimigoAtirador(x, -26, velocidade=70))
                elif tipo == 'zig':
                    self.inimigos.criar(InimigoZigueZague(x, -30, velocidade=80))
                else:
                    self.inimigos.criar(InimigoDescendo(x, -26, velocidade=90))

        # Boss morto: explosão épica e volta música normal
        boss_dead_event = False
        pos = None
        if getattr(self.inimigos, 'boss_killed', False):
            self.inimigos.boss_killed = False
            pos = getattr(self.inimigos, 'boss_killed_pos', None)
            self.inimigos.boss_killed_pos = None
            boss_dead_event = True
        else:
            boss_alive = any(isinstance(i, Boss) and not i.esta_morto() for i in self.inimigos.inimigos)
            if self.boss_spawned and (not boss_alive):
                boss_dead_event = True
                self.inimigos.boss_ativo = False

        if boss_dead_event:
            self.boss_spawned = False  # Permite spawn de novo boss
            self.boss_cleared += 1
            self.fase += 1
            self.fase_banner_timer = 5.0
            self.boss_add_timer = 0.0
            try:
                self.inimigos.bosses_derrotados = getattr(self.inimigos, 'bosses_derrotados', 0) + 1
            except Exception:
                pass

            # Explosão épica
            if pos is not None:
                cx, cy = pos
            else:
                cx = LARGURA // 2
                cy = 100

            # Múltiplas ondas de partículas
            for i in range(3):
                intensidade = 40 - i * 8
                raio = 50 + i * 20
                cores = [(255, 150, 50), (255, 200, 100), (255, 255, 200)]
                self.particulas.spawn_ao_redor(cx, cy, intensidade=intensidade, raio=raio, cores=cores, vel_base=120, vel_var=180)

            # Som de explosão grande (volume maior para o boss)
            if hasattr(self, 'sfx_explosion_big') and self.sfx_explosion_big:
                try:
                    # Aumenta temporariamente o volume para o boss
                    original_vol = self.sfx_explosion_big.get_volume()
                    self.sfx_explosion_big.set_volume(0.8)
                    self.sfx_explosion_big.play()
                    # Restaura volume original após 100ms (aproximado)
                    self.sfx_explosion_big.set_volume(original_vol)
                except Exception:
                    pass

            # Volta música normal
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
            if self.music_path:
                self._tocar_musica(self.music_path)

            # Pontuação bônus
            self.pontuacao += 500

            # Inicia celebração antes do acoplamento
            if self.jogador.stage < 3:
                self.estado = 'celebration'
                self.celebration_timer = 3.0 # 3 segundos de comemoração
                self.inimigos.inimigos.clear()
                self.tiros.tiros.clear()
                self.tiros_inimigos.tiros.clear()
                self.destrocos.destrocos.clear()
            else:
                # Continua jogo normal
                pass

        if self.estado == 'docking':
            self.atualizar_acoplamento(dt)
            return

        # inimigos atiradores disparam
        asts = [i for i in self.inimigos.inimigos if isinstance(i, Asteroide)]
        for i in self.inimigos.inimigos:
            if hasattr(i, 'tentar_atirar'):
                try:
                    i.tentar_atirar(self.tiros_inimigos, self.jogador, asts, getattr(self.inimigos, 'shot_mult', 1.0))
                except Exception:
                    pass

        # tiros inimigos x jogador
        if self.invul_timer == 0.0:
            for t in self.tiros_inimigos.tiros:
                hitado = any(t.retangulo.colliderect(hb) for hb in player_hitboxes)
                if hitado:
                    if self.player_shield_timer <= 0:
                        perdeu_vida = self.jogador.receber_dano()
                        if perdeu_vida:
                            self.vidas -= 1
                        else:
                            # perdeu estágio, mas ainda tem vidas
                            self.invul_timer = 2.0
                        cx = self.jogador.x + self.jogador.largura/2
                        cy = self.jogador.y + self.jogador.altura/2
                        if self.vidas <= 0:
                            # explosão final da nave (tiro inimigo)
                            self.particulas.spawn_ao_redor(cx, cy, intensidade=36, raio=34,
                                                           cores=[(255, 200, 200), (255, 240, 220), (180, 220, 255)],
                                                           vel_base=80, vel_var=160)
                            if hasattr(self, 'sfx_explosion_big') and self.sfx_explosion_big:
                                try: self.sfx_explosion_big.play()
                                except Exception: pass
                            elif hasattr(self, 'sfx_explosion_small') and self.sfx_explosion_small:
                                try: self.sfx_explosion_small.play()
                                except Exception: pass
                            try:
                                pygame.mixer.music.fadeout(1200)
                            except Exception:
                                pass
                            # inicia FX de Game Over mais lenta
                            self.game_over_fx_active = True
                            self.game_over_fx_t = 0.0
                            self.game_over_fx_pos = (cx, cy)
                            self.game_over_fx_emit = 0.0
                            self.jogador.matar(); self.estado = 'game_over'
                            self._iniciar_entrada_iniciais()
                        else:
                            # mini explosão + som e respawn animado
                            self.particulas.spawn_ao_redor(cx, cy, intensidade=20, raio=28,
                                                           cores=[(255, 160, 160), (255, 200, 200), (200, 230, 255)],
                                                           vel_base=70, vel_var=140)
                            if hasattr(self, 'sfx_explosion_small') and self.sfx_explosion_small:
                                try: self.sfx_explosion_small.play()
                                except Exception: pass
                            self.invul_timer = max(self.invul_timer, 1.8)
                            # traz nave de baixo e anima subida
                            self.jogador.y = ALTURA + 30
                            try:
                                self.jogador.spawn_anim = 1.2
                            except Exception:
                                pass
                    t.matar()

        # tiros inimigos x asteroides (encolhem ou destroem; origin env)
        for t in self.tiros_inimigos.tiros:
            if t.esta_morto():
                continue
            for a in asts:
                if a.esta_morto():
                    continue
                if a.retangulo.colliderect(t.retangulo):
                    estava_vivo = a.vivo
                    a.receber_dano(1)
                    if estava_vivo and a.esta_morto():
                        cx = a.x + a.largura/2; cy = a.y + a.altura/2
                        self.destrocos.explosao_asteroide(cx, cy, origin='env', tam_pai=a.largura)
                        # som de explosão ambiente
                        if getattr(self, 'sfx_explosion_small', None):
                            try: self.sfx_explosion_small.play()
                            except Exception: pass
                    t.matar()
                    break

    def desenhar(self):
        self.tela.fill((5, 8, 15))
        self.fundo.desenhar(self.tela)
        
        if self.estado == 'menu':
            self.menu.desenhar(self.tela)
            # Desenha a surface lógica na tela real (com escala se necessário)
            if self.usar_escala:
                pygame.transform.scale(self.tela, (self.largura_tela, self.altura_tela), self.tela_real)
            else:
                self.tela_real.blit(self.tela, (0, 0))
            pygame.display.flip()
            return

        if self.estado == 'celebration':
            self.jogador.desenhar(self.tela)
            
            # Texto de comemoração
            txt = self.fonte_grande.render("BOSS DESTROYED!", True, (255, 215, 0))
            self.tela.blit(txt, (LARGURA//2 - txt.get_width()//2, ALTURA//2 - 40))
            self._desenhar_banner_fase()
            
            # Desenha a surface lógica na tela real (com escala se necessário)
            if self.usar_escala:
                pygame.transform.scale(self.tela, (self.largura_tela, self.altura_tela), self.tela_real)
            else:
                self.tela_real.blit(self.tela, (0, 0))
            pygame.display.flip()
            return

        if self.estado == 'docking':
            self.jogador.desenhar(self.tela)
            if self.target_module:
                self.target_module.desenhar(self.tela)
            
            # Texto de instrução
            txt = self.fonte.render("ACOPLAR! ALINHE O CENTRO", True, (0, 255, 0))
            txt2 = self.fonte.render("Pressione ESPACO para retrofoguetes", True, (200, 230, 255))
            self.tela.blit(txt2, (LARGURA//2 - txt2.get_width()//2, ALTURA//2 + 24))
            self.tela.blit(txt, (LARGURA//2 - txt.get_width()//2, ALTURA//2))
            self._desenhar_banner_fase()
            
            # Desenha a surface lógica na tela real (com escala se necessário)
            if self.usar_escala:
                pygame.transform.scale(self.tela, (self.largura_tela, self.altura_tela), self.tela_real)
            else:
                self.tela_real.blit(self.tela, (0, 0))
            pygame.display.flip()
            return

        self.upgrades.desenhar(self.tela)
        self.destrocos.desenhar(self.tela)
        
        # nave com fade no Game Over
        if self.estado == 'game_over' and getattr(self, 'game_over_fx_active', False) and getattr(self.jogador, 'sprite', None):
            try:
                dur = 1.2
                t = max(0.0, min(1.0, self.game_over_fx_t / dur))
                alpha = int(255 * (1.0 - t))
                if alpha > 0:
                    spr = self.jogador.sprite.copy()
                    spr.set_alpha(alpha)
                    self.tela.blit(spr, self.jogador.retangulo.topleft)
            except Exception:
                self.jogador.desenhar(self.tela)
        else:
            self.jogador.desenhar(self.tela)
            
        self.particulas.desenhar(self.tela)
        # anel pulsante quando super está totalmente carregado
        if self.estado == 'jogando' and self.carregando_super and self.tempo_carregando >= 1.5:
            cx = int(self.jogador.x + self.jogador.largura/2)
            cy = int(self.jogador.y + self.jogador.altura/2)
            base = 28
            osc = 4 * math.sin(self.tempo_carregando * 8.0)
            pygame.draw.circle(self.tela, (150, 255, 255), (cx, cy), int(base + osc), 2)
        self.tiros.desenhar(self.tela)
        self.tiros_inimigos.desenhar(self.tela)
        self.inimigos.desenhar(self.tela)
        
        # desenhar textos flutuantes (ex.: +1 VIDA)
        for fx in self.fx_texts:
            surf = fx.get('surf')
            if surf is None:
                continue
            t = fx.get('t', 0.0)
            dur = fx.get('dur', 1.6)
            pct = max(0.0, min(1.0, t / dur))
            alpha = int(255 * (1.0 - pct))
            dy = -26 * pct  # sobe levemente
            try:
                s2 = surf.copy()
                s2.set_alpha(alpha)
                x = int(fx.get('x', 0) - s2.get_width()/2)
                y = int(fx.get('y', 0) + dy)
                self.tela.blit(s2, (x, y))
            except Exception:
                pass


        if self.fase_banner_timer > 0.0:
            fase_txt = self.fonte_grande.render(f"Fase {self.fase}", True, (230, 235, 255))
            box = fase_txt.get_rect(center=(LARGURA//2, ALTURA//2))
            self.tela.blit(fase_txt, box)

        upg_txt = f"{self.upgrade_super_timer:0.1f}s" if self.upgrade_super_timer > 0 else "—"
        shield_txt = f"{self.player_shield_timer:0.1f}s" if self.player_shield_timer > 0 else "—"
        hud = self.fonte.render(f"Pontuação: {self.pontuacao}  |  Vidas: {self.vidas}  |  Upgrade V: {upg_txt}  |  Shield: {shield_txt}", True, (220, 230, 255))
        self.tela.blit(hud, (10, 10))
        rec_name, rec_score, rec_phase = self.score_manager.get_high_holder()
        rec_phase_txt = f" F{rec_phase}" if rec_phase else ""
        rec_txt = self.fonte.render(f"REC: {rec_name} {rec_score}{rec_phase_txt}", True, (200, 210, 255))
        self.tela.blit(rec_txt, (LARGURA - rec_txt.get_width() - 10, 10))
        # piscar o jogador quando invulnerável
        if self.invul_timer > 0 and self.estado == 'jogando':
            if int(pygame.time.get_ticks() / 100) % 2 == 0:
                pygame.draw.rect(self.tela, (255, 255, 255), self.jogador.retangulo, 2)
        # desenha campo de força do jogador
        if self.player_shield_timer > 0:
            cx = int(self.jogador.x + self.jogador.largura/2)
            cy = int(self.jogador.y + self.jogador.altura/2)
            r = max(self.jogador.largura, self.jogador.altura)
            # Pisca quando está acabando (últimos 3 segundos)
            if self.player_shield_timer <= 3.0:
                # Pisca mais rápido conforme o tempo diminui
                flash_speed = 200 - int(self.player_shield_timer * 50)  # 200ms a 50ms
                if int(pygame.time.get_ticks() / flash_speed) % 2 == 0:
                    pygame.draw.circle(self.tela, (120, 200, 255), (cx, cy), int(r), 2)
            else:
                pygame.draw.circle(self.tela, (120, 200, 255), (cx, cy), int(r), 2)
            
        if self.estado == 'game_over':
            self.game_over_screen.desenhar(
                self.tela,
                self.pontuacao,
                self.score_manager.get_top10(),
                entering_initials=self.entering_initials,
                initials_input=self.initials_input
            )
            # anéis da explosão final por cima do overlay
            if getattr(self, 'game_over_fx_active', False):
                cx, cy = self.game_over_fx_pos
                t = self.game_over_fx_t
                base = 30
                r = int(base + 140 * (1 - math.exp(-1.6 * max(0.0, t))))
                pygame.draw.circle(self.tela, (230, 240, 255), (int(cx), int(cy)), max(1, r), 3)
                if r > 20:
                    pygame.draw.circle(self.tela, (180, 220, 255), (int(cx), int(cy)), max(1, r-12), 2)
        elif self.estado == 'pausado':
            # overlay de pausa com confirmação
            overlay = pygame.Surface((LARGURA, ALTURA))
            overlay.set_alpha(140)
            overlay.fill((10, 10, 16))
            self.tela.blit(overlay, (0, 0))
            t1 = self.fonte_grande.render("PAUSADO", True, (230, 240, 255))
            t2 = self.fonte.render("Tem certeza que deseja sair?", True, (220, 230, 255))
            t3 = self.fonte.render("S para sair  |  N/Esc/Enter/Espaço para continuar", True, (200, 210, 230))
            self.tela.blit(t1, (LARGURA//2 - t1.get_width()//2, ALTURA//2 - 50))
            self.tela.blit(t2, (LARGURA//2 - t2.get_width()//2, ALTURA//2 + 0))
            self.tela.blit(t3, (LARGURA//2 - t3.get_width()//2, ALTURA//2 + 30))
        # Desenha a surface lógica na tela real (com escala se necessário)
        if self.usar_escala:
            pygame.transform.scale(self.tela, (self.largura_tela, self.altura_tela), self.tela_real)
        else:
            self.tela_real.blit(self.tela, (0, 0))
            
        pygame.display.flip()

    def executar(self):
        while True:
            dt = self.relogio.tick(FPS) / 1000.0
            self.lidar_com_eventos()
            self.atualizar(dt)
            self.desenhar()

    def disparar_super(self):
        # configura recarga no jogador
        self.jogador.atirar_super()
        # zera cooldown p/ permitir tiro normal imediato apÃ³s o carregado
        self.jogador.tempo_recarga = 0.0
        # som super
        if hasattr(self, 'sfx_super') and self.sfx_super:
            try:
                self.sfx_super.play()
            except Exception:
                pass
        # padrão: sem upgrade = 1 tiro reto; com upgrade = V + reto (3 tiros)
        base_ang = math.radians(10)
        angulos = [0.0]
        if self.upgrade_super_timer > 0:
            angulos = [-base_ang, 0.0, +base_ang]

        # posição central do cano
        cx = self.jogador.x + self.jogador.largura/2
        topy = self.jogador.y - 18
        speed = abs(VELOCIDADE_TIRO)

        # offsets por estágio (mais canhões quando acoplado)
        if self.jogador.stage >= 3:
            offsets = [-12, 0, +12]
        elif self.jogador.stage == 2:
            offsets = [-8, +8]
        else:
            offsets = [0]

        for off in offsets:
            for ang in angulos:
                vx = speed * math.sin(ang)
                vy = -speed * math.cos(ang)
                self.tiros.criar(SuperTiro(cx + off - 12, topy, vx=vx, vy=vy))

    def _fire_laser_beam(self):
        altura = max(10, self.jogador.y)
        cx = self.jogador.x + self.jogador.largura/2
        beam = LaserBeam(
            cx,
            self.jogador.y,
            altura,
            tracker=lambda: (self.jogador.x + self.jogador.largura/2, self.jogador.y)
        )
        self.tiros.criar(beam)

    def disparar_normal(self):
        # define recarga do tiro normal
        self.jogador.tempo_recarga = 0.1
        # som tiro
        if hasattr(self, 'sfx_shot') and self.sfx_shot:
            try:
                self.sfx_shot.play()
            except Exception:
                pass
        cx = self.jogador.x + self.jogador.largura/2
        topy = self.jogador.y - 12
        speed = abs(VELOCIDADE_TIRO)
        base_ang = math.radians(10)
        angulos = [0.0]
        if self.upgrade_super_timer > 0:
            angulos = [-base_ang, 0.0, +base_ang]

        # offsets por estágio (mais canhões quando acoplado)
        if self.jogador.stage >= 3:
            offsets = [-12, 0, +12]
        elif self.jogador.stage == 2:
            offsets = [-8, +8]
        else:
            offsets = [0]

        for off in offsets:
            for ang in angulos:
                vx = speed * math.sin(ang)
                vy = -speed * math.cos(ang)
                self.tiros.criar(Tiro(cx + off - 3, topy, vx=vx, vy=vy))

    def atualizar_celebracao(self, dt):
        self.fundo.atualizar(dt)
        self.particulas.atualizar(dt)
        self.jogador.atualizar(dt)
        
        self.celebration_timer -= dt
        if self.celebration_timer <= 0:
            self.iniciar_acoplamento()

    def iniciar_acoplamento(self):
        self.estado = 'docking'
        # Limpa inimigos e tiros
        self.inimigos.inimigos.clear()
        self.tiros.tiros.clear()
        self.tiros_inimigos.tiros.clear()
        self.destrocos.destrocos.clear()
        
        # Posiciona jogador na parte inferior
        self.jogador.x = LARGURA / 2 - self.jogador.largura / 2
        self.jogador.y = ALTURA - 100
        
        # Cria módulo alvo no topo
        target_stage = self.jogador.stage + 1
        self.target_module = TargetModule(LARGURA / 2 - S(36)/2, 50, target_stage)

        self.docking_timer = 0.0
        self.docking_success = False
        
        # Som de alerta/sirene
        if hasattr(self, 'sfx_ufo') and self.sfx_ufo:
            try: self.sfx_ufo.play()
            except: pass

    def atualizar_acoplamento(self, dt):
        self.fundo.atualizar(dt)
        self.particulas.atualizar(dt)
        
        # Move jogador (apenas horizontalmente)
        teclas = pygame.key.get_pressed()
        dx = (teclas[pygame.K_RIGHT] - teclas[pygame.K_LEFT]) * VELOCIDADE_JOGADOR * dt
        
        self.jogador.x = max(0, min(LARGURA - self.jogador.largura, self.jogador.x + dx))
        # Trava Y na parte inferior
        self.jogador.y = ALTURA - self.jogador.altura - 10
        self.jogador.sincronizar_retangulo()

        # Move alvo
        if self.target_module:
            if teclas[pygame.K_SPACE] and self.target_module.y > ALTURA / 2:
                self.target_module.aplicar_retro(dt)
                # efeito de chama do retrofoguete
                try:
                    cx = self.target_module.x + self.target_module.largura/2
                    cy = self.target_module.y + self.target_module.altura
                    cores = [(255, 180, 80), (255, 220, 140), (200, 140, 80)]
                    self.particulas.spawn_ao_redor(cx, cy, intensidade=6, raio=18, cores=cores, vel_base=90, vel_var=80)
                except Exception:
                    pass
            self.target_module.atualizar(dt)
            
            # Checa colisão/alinhamento
            if self.jogador.retangulo.colliderect(self.target_module.retangulo):
                # Verifica alinhamento horizontal preciso (tolerância de 10px)
                center_diff = abs((self.jogador.x + self.jogador.largura/2) - (self.target_module.x + self.target_module.largura/2))
                if center_diff < 10:
                    self.sucesso_acoplamento()
                    return
                else:
                    # Colisão desalinhada = explosão das duas naves
                    self.falha_acoplamento_explosao()
                    return
            
            # Se passar do jogador (perdeu a chance)
            if self.target_module.y > ALTURA:
                self.falha_acoplamento()

    def sucesso_acoplamento(self):
        self.jogador.stage += 1
        self.jogador.vida = 3 # Recupera vida? Opcional
        self.pontuacao += 1000
        self.estado = 'jogando'
        self.target_module = None
        self.laser_wave_expire = None
        self.laser_beam_active = False

        # Reseta gerenciador de inimigos para reiniciar ondas
        self.inimigos.boss_ativo = False
        self.inimigos.boss_killed = False
        self.inimigos.tempo_total = 0.0 # Reinicia dificuldade/ondas
        self.inimigos.onda = 0
        self.inimigos.inimigos.clear() # Garante limpo
        self.boss_spawned = False
        
        # Som de powerup
        if hasattr(self, 'sfx_powerup'):
            try: self.sfx_powerup.play()
            except: pass
            
    def falha_acoplamento(self):
        self.estado = 'jogando'
        self.target_module = None
        self.laser_wave_expire = None
        self.laser_beam_active = False
        self.inimigos.boss_ativo = False
        self.inimigos.boss_killed = False
        self.inimigos.resetar_spawn(atraso=2.5)
        self.inimigos.inimigos.clear()
        self.boss_spawned = False
        # Som de erro?

    def falha_acoplamento_explosao(self):
        # Explosão no jogador e no módulo
        cx_p = self.jogador.x + self.jogador.largura/2
        cy_p = self.jogador.y + self.jogador.altura/2
        cx_m = self.target_module.x + self.target_module.largura/2
        cy_m = self.target_module.y + self.target_module.altura/2
        
        # Partículas
        cores = [(255, 100, 50), (255, 200, 100), (255, 255, 255)]
        self.particulas.spawn_ao_redor(cx_p, cy_p, intensidade=30, raio=40, cores=cores, vel_base=100, vel_var=150)
        self.particulas.spawn_ao_redor(cx_m, cy_m, intensidade=30, raio=40, cores=cores, vel_base=100, vel_var=150)
        
        # Som
        if hasattr(self, 'sfx_explosion_big'):
            try: self.sfx_explosion_big.play()
            except: pass
            
        # Penalidade: Perde uma vida e reseta para estágio anterior (ou perde estágio e vida)
        self.vidas -= 1
        self.jogador.stage = max(1, self.jogador.stage - 1)

        self.target_module = None
        self.estado = 'jogando'
        self.laser_wave_expire = None
        self.laser_beam_active = False
        self.inimigos.boss_ativo = False
        self.inimigos.boss_killed = False
        self.inimigos.resetar_spawn(atraso=2.5)
        self.inimigos.inimigos.clear()
        self.boss_spawned = False

        # Se vidas zeraram, game over será tratado no próximo update
        if self.vidas > 0:
            # Respawn anim
            self.invul_timer = 2.0
            self.jogador.y = ALTURA + 30
            self.jogador.spawn_anim = 1.2
            
            # Reseta inimigos também para dar um respiro
            self.inimigos.inimigos.clear()

