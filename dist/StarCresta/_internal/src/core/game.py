import pygame
import sys
import math
import os
from src.settings import *
from src.assets import carregar_som, get_resource_path
from src.sprites.player import Jogador
from src.sprites.projectile import Tiro, SuperTiro
from src.sprites.enemy import Asteroide
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

class Jogo:
    def __init__(self):
        # tentar reduzir latência de áudio
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
        except Exception:
            pass
        pygame.init()
        pygame.display.set_caption("StarCresta")
        self.tela = pygame.display.set_mode((LARGURA, ALTURA), pygame.FULLSCREEN)
        self.relogio = pygame.time.Clock()
        self.fonte = pygame.font.SysFont(None, 22)
        self.fonte_grande = pygame.font.SysFont(None, 48)

        self.score_manager = ScoreManager()
        self.menu = Menu(self)
        self.game_over_screen = GameOverScreen(self)

        self.jogador = Jogador(LARGURA/2 - 18, ALTURA - 80)
        self.tiros = GerenciadorDeTiros()
        self.inimigos = GerenciadorDeInimigos()
        self.particulas = GerenciadorDeParticulas()
        # menos estrelas no fundo (metade do anterior)
        estrelas_qtd = int(70 * (LARGURA/BASE_LARGURA) * (ALTURA/BASE_ALTURA) / 1.0)
        self.fundo = CampoEstrelas(quantidade=estrelas_qtd)
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
        self.vidas = 3
        self.jogador = Jogador(LARGURA/2 - 18, ALTURA - 80)
        self.tiros = GerenciadorDeTiros()
        self.inimigos = GerenciadorDeInimigos()
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

    def lidar_com_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            
            if self.estado == 'menu':
                acao = self.menu.lidar_evento(evento)
                if acao == 'jogar':
                    self.reiniciar()
                    self.estado = 'jogando'
                elif acao == 'sair':
                    pygame.quit(); sys.exit()

            elif self.estado == 'jogando':
                # Pausa com confirmação (ESC/Q abre pausa)
                if evento.type == pygame.KEYDOWN and evento.key in (pygame.K_ESCAPE, pygame.K_q):
                    # entrar no modo pausado
                    self.estado = 'pausado'
                    # cancelar qualquer carregamento de super em andamento
                    self.carregando_super = False
                    self.tempo_carregando = 0.0
                    self.sinalizou_super_pronto = False
                    try:
                        pygame.mixer.music.pause()
                    except Exception:
                        pass
                    # pausar sirene do UFO, se tocando
                    try:
                        if self.ufo_channel is not None:
                            self.ufo_channel.pause()
                    except Exception:
                        pass
                    return
                if evento.type == pygame.KEYDOWN and evento.key == pygame.K_SPACE:
                    if self.jogador.pode_atirar() and not getattr(self, 'carregando_super', False):
                        self.carregando_super = True
                        self.tempo_carregando = 0.0
                        self.sinalizou_super_pronto = False
                if evento.type == pygame.KEYUP and evento.key == pygame.K_SPACE:
                    if getattr(self, 'carregando_super', False):
                        # dispara conforme tempo carregado
                        if self.tempo_carregando >= 1.0:
                            # dispara padrão em V conforme o nível
                            self.disparar_super()
                        else:
                            self.disparar_normal()
                        self.carregando_super = False
                        self.tempo_carregando = 0.0
                        self.sinalizou_super_pronto = False
                # Debug: Spawn Boss com tecla B
                if evento.type == pygame.KEYDOWN and evento.key == pygame.K_b:
                    if not self.boss_spawned:
                        self.inimigos.spawnar_boss()
                        self.boss_spawned = True
                        # Trocar música para boss
                        if self.boss_music_path:
                            self._tocar_musica(self.boss_music_path)

            elif self.estado == 'pausado':
                if evento.type == pygame.KEYDOWN:
                    # confirmação explícita: S para sair; N/ESC/Enter/Espaço/P/R/C para continuar
                    if evento.key in (pygame.K_s,):
                        pygame.quit(); sys.exit()
                    if evento.key in (pygame.K_n, pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE, pygame.K_p, pygame.K_r, pygame.K_c):
                        self.estado = 'jogando'
                        try:
                            pygame.mixer.music.unpause()
                        except Exception:
                            pass
                        # retomar sirene do UFO, se existirem UFOs ativos
                        try:
                            if self.ufo_channel is not None:
                                self.ufo_channel.unpause()
                        except Exception:
                            pass
            elif self.estado == 'game_over':
                if evento.type == pygame.KEYDOWN:
                    if evento.key in (pygame.K_r, pygame.K_SPACE, pygame.K_RETURN):
                        self.reiniciar()
                    elif evento.key == pygame.K_m:
                        self.estado = 'menu'
                        # Retornar música normal no menu
                        self._tocar_musica(self.music_path)
                    elif evento.key in (pygame.K_ESCAPE, pygame.K_q):
                        pygame.quit(); sys.exit()

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
        
        if self.estado == 'menu':
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
            
        # Spawn do Boss
        if self.pontuacao >= 500 and not self.boss_spawned:
            self.inimigos.spawnar_boss()
            self.boss_spawned = True
            # Trocar música para boss
            if self.boss_music_path:
                self._tocar_musica(self.boss_music_path)
            
        self.jogador.atualizar(dt)
        self.tiros.atualizar(dt)
        self.inimigos.atualizar(dt)
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
        abates = self.inimigos.verificar_colisoes_com_tiros(self.tiros, self.destrocos)
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
                inimigo.matar()
                self.vidas -= 1
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
                    # Salvar High Score
                    self.score_manager.salvar(self.pontuacao)
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
                    if d.retangulo.colliderect(self.jogador.retangulo):
                        if self.player_shield_timer > 0:
                            continue
                        self.vidas -= 1
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
                            # Salvar High Score
                            self.score_manager.salvar(self.pontuacao)
                        else:
                            self.invul_timer = 1.8
                            # anima respawn vindo de baixo
                            self.jogador.y = ALTURA + 30
                            try:
                                self.jogador.spawn_anim = 1.2
                            except Exception:
                                pass
                        break

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
                self.upgrade_super_timer = 10.0
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
            if hasattr(self, 'sfx_powerup') and self.sfx_powerup:
                try:
                    self.sfx_powerup.play()
                except Exception:
                    pass

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
            self.pontuacao += 500

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
                if t.retangulo.colliderect(self.jogador.retangulo):
                    if self.player_shield_timer <= 0:
                        self.vidas -= 1
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
                            # Salvar High Score
                            self.score_manager.salvar(self.pontuacao)
                        else:
                            # mini explosão + som e respawn animado
                            self.particulas.spawn_ao_redor(cx, cy, intensidade=20, raio=28,
                                                           cores=[(255, 160, 160), (255, 200, 200), (200, 230, 255)],
                                                           vel_base=70, vel_var=140)
                            if hasattr(self, 'sfx_explosion_small') and self.sfx_explosion_small:
                                try: self.sfx_explosion_small.play()
                                except Exception: pass
                            self.invul_timer = 1.8
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

        upg_txt = f"{self.upgrade_super_timer:0.1f}s" if self.upgrade_super_timer > 0 else "—"
        shield_txt = f"{self.player_shield_timer:0.1f}s" if self.player_shield_timer > 0 else "—"
        hud = self.fonte.render(f"Pontuação: {self.pontuacao}  |  Vidas: {self.vidas}  |  Upgrade V: {upg_txt}  |  Shield: {shield_txt}", True, (220, 230, 255))
        self.tela.blit(hud, (10, 10))
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
            self.game_over_screen.desenhar(self.tela, self.pontuacao, self.score_manager.get_high_score())
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
        # som super
        if hasattr(self, 'sfx_super') and self.sfx_super:
            try:
                self.sfx_super.play()
            except Exception:
                pass
        # padrão: sem upgrade = 1 tiro reto; com upgrade = V + reto (3 tiros)
        base_ang = math.radians(12)
        if self.upgrade_super_timer > 0:
            angulos = [-base_ang, 0.0, +base_ang]
        else:
            angulos = [0.0]

        # posição central do cano
        cx = self.jogador.x + self.jogador.largura/2
        topy = self.jogador.y - 18
        speed = abs(VELOCIDADE_TIRO)
        for ang in angulos:
            vx = speed * math.sin(ang)
            vy = -speed * math.cos(ang)
            # centraliza cada supertiro (24px de largura)
            self.tiros.criar(SuperTiro(cx - 12, topy, vx=vx, vy=vy))

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
        base_ang = math.radians(12)
        if self.upgrade_super_timer > 0:
            angulos = [-base_ang, 0.0, +base_ang]
        else:
            angulos = [0.0]
        for ang in angulos:
            vx = speed * math.sin(ang)
            vy = -speed * math.cos(ang)
            self.tiros.criar(Tiro(cx - 3, topy, vx=vx, vy=vy))
