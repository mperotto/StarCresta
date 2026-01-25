import pygame
import random
import math
from src.settings import *
from src.sprites.enemy import InimigoAtirador, InimigoZigueZague, Asteroide, DiscoVoador
from src.sprites.boss import Boss
from src.sprites.items import Upgrade, Destroco

class GerenciadorDeTiros:
    def __init__(self):
        self.tiros = []

    def criar(self, tiro):
        self.tiros.append(tiro)

    def atualizar(self, dt):
        for tiro in self.tiros:
            tiro.atualizar(dt)
        self.tiros = [tiro for tiro in self.tiros if not tiro.esta_morto()]

    def desenhar(self, tela):
        for tiro in self.tiros:
            tiro.desenhar(tela)

class GerenciadorDeTirosInimigos:
    def __init__(self):
        self.tiros = []
        self.cap_tiros = MAX_TIROS_INIMIGOS

    def criar(self, tiro):
        # limita o número de projéteis inimigos ativos para reduzir poluição visual
        if len(self.tiros) >= getattr(self, 'cap_tiros', 18):
            return
        self.tiros.append(tiro)
        # dispara som de tiro inimigo se configurado
        s = getattr(self, 'sfx_shot', None)
        if s:
            try:
                s.play()
            except Exception:
                pass

    def atualizar(self, dt):
        for t in self.tiros:
            t.atualizar(dt)
        self.tiros = [t for t in self.tiros if not t.esta_morto()]

    def desenhar(self, tela):
        for t in self.tiros:
            t.desenhar(tela)

from src.sprites.boss import Boss

class GerenciadorDeInimigos:
    def __init__(self):
        self.inimigos = []
        self.tempo = 0.0
        self.onda = 0
        self.tempo_total = 0.0
        self.ufo_cd = random.uniform(16.0, 28.0)
        self.shot_mult = 1.0
        self.spawn_delay = 0.0
        # recompensa por UFO abatido
        self.ufo_killed = False
        self.ufo_killed_pos = None
        self.boss_ativo = False
        self.boss_killed = False
        self.boss_killed_pos = None
        self.fase = 1  # atualizado externamente para progressão

    def criar(self, inimigo):
        self.inimigos.append(inimigo)

    def spawnar_boss(self, quantidade=1, fase=1):
        self.boss_ativo = True
        quantidade = max(1, int(quantidade))
        for i in range(quantidade):
            offset = (i - (quantidade - 1) / 2.0) * 180
            boss = Boss(LARGURA/2 - 64 + offset, -150, fase=fase)
            boss.allow_dive = fase >= 3
            boss.dive_cooldown = random.uniform(4.5, 7.5)
            self.criar(boss)

    def atualizar(self, dt):
        # Tempo de respiro após eventos (acoplamento/falha)
        if self.spawn_delay > 0.0:
            self.spawn_delay = max(0.0, self.spawn_delay - dt)
        else:
            self.tempo_total += dt
            self.tempo += dt
        fase_boss = max(0, getattr(self, 'bosses_derrotados', 0))
        
        # Se boss ativo, não spawna inimigos comuns
        if not self.boss_ativo:
            # dificuldade progressiva (escala também com a fase)
            fase_mult = 1.0 + 0.12 * max(0, self.fase - 1)
            intervalo = max(0.45, (TEMPO_ENTRE_INIMIGOS - self.tempo_total * 0.006) / fase_mult)
            speed_mult = min(2.5, (1.0 + self.tempo_total * 0.02) * fase_mult)
            # multiplicador para cadência de tiro dos inimigos (1.0 -> 1.6)
            self.shot_mult = min(1.6, 1.0 + self.tempo_total * 0.01 + fase_boss * 0.05 + 0.08 * (self.fase - 1))
            # spawn simples alternando tipos, mas com intervalo que diminui e velocidades que aumentam
            if self.tempo >= intervalo:
                self.tempo = 0.0
                self.onda += 1
                x = 40 + (self.onda * 53) % (LARGURA - 80)
                if self.onda % 5 == 0:
                    self.criar(InimigoAtirador(x, -26, velocidade=70 * speed_mult))
                elif self.onda % 3 == 0:
                    self.criar(InimigoZigueZague(x, -30, velocidade=80 * speed_mult))
                else:
                    # asteroide com categoria aleatória
                    cat = random.choices(['small','med','big'], weights=[3,2,1])[0]
                    self.criar(Asteroide(x, -48 if cat=='big' else -32, velocidade=60 * speed_mult, categoria=cat))

            # spawn raro de Disco Voador (desafio)
            self.ufo_cd -= dt
            if self.ufo_cd <= 0.0:
                # só 1 por vez
                existe = any(isinstance(i, DiscoVoador) and not i.esta_morto() for i in self.inimigos)
                if not existe:
                    direcao = 1 if random.random() < 0.5 else -1
                    y = random.randint(S(60), S(160))
                    x = -S(40) if direcao == 1 else LARGURA + S(40)
                    # Velocidade escala com a fase (começa mais lento e aumenta)
                    base_speed = 150 + (min(10, self.fase) * 25)
                    speed_mult = 1.0 + (self.tempo_total * 0.001) # Fator tempo bem reduzido
                    self.criar(DiscoVoador(x, y, velocidade=base_speed * speed_mult, direcao=direcao))
                # próximo em 18–30s, mais frequente conforme o tempo
                base_min, base_max = 18.0, 30.0
                fator = max(0.5, 1.0 - self.tempo_total * 0.007)
                self.ufo_cd = random.uniform(base_min * fator, base_max * fator)
        
        # Verifica se o boss morreu para liberar spawns
        if self.boss_ativo:
            bosses = [i for i in self.inimigos if isinstance(i, Boss)]
            mortos_novos = []
            for boss in bosses:
                if boss.esta_morto() and not hasattr(boss, '_morte_notificada'):
                    boss._morte_notificada = True
                    mortos_novos.append(boss)
            tem_boss = any(isinstance(i, Boss) and not i.esta_morto() for i in self.inimigos)
            if (not tem_boss) and (mortos_novos or self.boss_killed):
                ultimo = mortos_novos[-1] if mortos_novos else bosses[-1] if bosses else None
                if ultimo:
                    self.boss_killed = True
                    self.boss_killed_pos = (ultimo.x + ultimo.largura/2, ultimo.y + ultimo.altura/2)
                self.boss_ativo = False
                self.tempo_total += 200 # Aumenta dificuldade após boss

        for inimigo in self.inimigos:
            inimigo.atualizar(dt)
        self.inimigos = [inimigo for inimigo in self.inimigos if not inimigo.esta_morto()]

    def desenhar(self, tela):
        for inimigo in self.inimigos:
            inimigo.desenhar(tela)

    def resetar_spawn(self, atraso=0.0):
        # Reinicia contadores de ondas após eventos como acoplamento ou falha
        self.tempo_total = 0.0
        self.tempo = 0.0
        self.onda = 0
        self.ufo_cd = random.uniform(16.0, 28.0)
        self.spawn_delay = max(0.0, atraso)

    def verificar_colisoes_com_tiros(self, gerenciador_de_tiros, destrocos=None, upgrades=None):
        # Retorna quantos inimigos morreram neste passo
        abates = 0
        for inimigo in self.inimigos:
            if inimigo.esta_morto():
                continue
            for tiro in gerenciador_de_tiros.tiros:
                if tiro.esta_morto():
                    continue
                if inimigo.retangulo.colliderect(tiro.retangulo):
                    if isinstance(inimigo, Asteroide):
                        estava_vivo = inimigo.vivo
                        inimigo.receber_dano(1)
                        if estava_vivo and inimigo.esta_morto():
                            abates += 1
                            if upgrades is not None:
                                upgrades.drop_random(inimigo.x + inimigo.largura/2, inimigo.y + inimigo.altura/2)
                            if destrocos is not None:
                                cx = inimigo.x + inimigo.largura/2
                                cy = inimigo.y + inimigo.altura/2
                                # explosão com origem do player
                                destrocos.explosao_asteroide(cx, cy, origin='player', tam_pai=inimigo.largura)
                                # som de explosão (tenta big, senão small)
                                jogo_ref = getattr(self, 'sfx_explosion_big', None)
                                if jogo_ref:
                                    try: self.sfx_explosion_big.play()
                                    except Exception: pass
                                elif getattr(self, 'sfx_explosion_small', None):
                                    try: self.sfx_explosion_small.play()
                                    except Exception: pass
                    else:
                        # inimigos comuns recebem dano direto
                        estava_vivo = inimigo.vivo
                        inimigo.receber_dano(1)
                        if estava_vivo and inimigo.esta_morto():
                            abates += 1
                            if upgrades is not None:
                                upgrades.drop_random(inimigo.x + inimigo.largura/2, inimigo.y + inimigo.altura/2)
                            if isinstance(inimigo, DiscoVoador):
                                self.ufo_killed = True
                                self.ufo_killed_pos = (inimigo.x + inimigo.largura/2, inimigo.y + inimigo.altura/2)
                    # tiros do player não matam outros inimigos diretamente
                    if not getattr(tiro, 'perfurante', False):
                        tiro.matar()
                    break
        # Remover imediatamente inimigos mortos para refletir no mesmo frame
        self.inimigos = [i for i in self.inimigos if not i.esta_morto()]
        return abates

    def verificar_colisao_com_jogador(self, jogador):
        try:
            hitboxes = jogador.get_segment_rects()
        except Exception:
            hitboxes = [jogador.retangulo]
        for inimigo in self.inimigos:
            for hb in hitboxes:
                if inimigo.retangulo.colliderect(hb):
                    return inimigo
        return None

class GerenciadorDeUpgrades:
    def __init__(self):
        self.upgrades = []
        self.tempo = 0.0
        self.intervalo = 1.2
        self.fase = 1

    def criar(self, upgrade):
        self.upgrades.append(upgrade)

    def atualizar(self, dt):
        self.tempo += dt
        if self.tempo >= self.intervalo:
            self.tempo = 0.0
            # chance de spawn aleatória
            chance_base = 0.28
            chance = max(0.1, chance_base * (0.85 ** max(0, self.fase - 1)))
            if random.random() < chance:
                x = 20 + int(random.random() * (LARGURA - 40))
                # 35% shield, 15% health, 50% v-shot
                r = random.random()
                if r < 0.35:
                    tipo = 'shield'
                elif r < 0.50:
                    tipo = 'health'
                else:
                    tipo = 'v'
                self.criar(Upgrade(x, -18, tipo=tipo))
        for u in self.upgrades:
            u.atualizar(dt)
        self.upgrades = [u for u in self.upgrades if not u.esta_morto()]

    def drop_random(self, x, y):
        # chance fixa por inimigo abatido
        chance = 0.18
        if random.random() > chance:
            return
        r = random.random()
        # Laser removido daqui (exclusivo do UFO)
        if r < 0.40:
            tipo = 'shield'
        elif r < 0.55:
            tipo = 'health'
        else:
            tipo = 'v'
        self.criar(Upgrade(x, y, tipo=tipo, velocidade=90))

    def desenhar(self, tela):
        for u in self.upgrades:
            u.desenhar(tela)

    def verificar_coleta(self, jogador):
        efeitos = []
        try:
            hitboxes = jogador.get_segment_rects()
        except Exception:
            hitboxes = [jogador.retangulo]
        for u in self.upgrades:
            if u.esta_morto(): 
                continue
            for hb in hitboxes:
                if hb.colliderect(u.retangulo):
                    efeitos.append(u.tipo)
                    u.matar()
                    break
        
        self.upgrades = [u for u in self.upgrades if not u.esta_morto()]
        return efeitos

    def verificar_coleta_por_inimigos(self, inimigos):
        # inimigos também podem pegar upgrades
        for u in list(self.upgrades):
            for inimigo in inimigos.inimigos:
                if isinstance(inimigo, Boss):
                    continue
                if inimigo.retangulo.colliderect(u.retangulo):
                    if hasattr(inimigo, 'coletar_upgrade'):
                        inimigo.coletar_upgrade(u.tipo)
                        u.matar()
                        break
        self.upgrades = [u for u in self.upgrades if not u.esta_morto()]

class GerenciadorDeDestrocos:
    def __init__(self):
        self.destrocos = []

    def criar(self, d):
        self.destrocos.append(d)

    def explosao_asteroide(self, cx, cy, origin='env', tam_pai=None):
        n = random.randint(3, 6)
        # Se soubermos o tamanho (diâmetro) do meteoro pai, limite o raio dos
        # fragmentos a no máximo tam_pai/2 para garantir que sejam menores.
        max_raio = (tam_pai / 2.0) if tam_pai is not None else None
        cat_ubs = {'tiny': 8, 'small': 11, 'med': 15, 'big': 20}
        pesos = {'tiny': 3, 'small': 3, 'med': 2, 'big': 1}
        for _ in range(n):
            categorias = ['tiny', 'small', 'med', 'big']
            if max_raio is not None:
                # mantenha somente categorias cujo teto de raio caiba no pai
                categorias = [c for c in categorias if cat_ubs[c] <= max_raio]
                if not categorias:
                    # se o pai for muito pequeno, use tiny e recorte o range
                    categorias = ['tiny']
            # sorteia categoria com pesos filtrados
            w = [pesos[c] for c in categorias]
            categoria = random.choices(categorias, weights=w)[0]
            # intervalo base por categoria
            if categoria == 'tiny':
                rmin, rmax = 5, 8
            elif categoria == 'small':
                rmin, rmax = 8, 11
            elif categoria == 'med':
                rmin, rmax = 11, 15
            else:
                rmin, rmax = 15, 20
            # aplica teto pelo tamanho do pai
            if max_raio is not None:
                rmax = min(rmax, max_raio)
                rmin = min(rmin, rmax)
            raio = random.uniform(rmin, rmax)
            ang = random.random() * math.tau
            # pedaços menores voam mais rápido
            base = {'tiny': 260, 'small': 220, 'med': 180, 'big': 140}[categoria] * SCALE
            speed = random.uniform(base*0.8, base*1.2)
            vx = math.cos(ang) * speed
            vy = math.sin(ang) * speed
            self.criar(Destroco(cx, cy, raio=raio, vx=vx, vy=vy, origin=origin))

    def colidir_com_inimigos(self, ger_inimigos):
        vivos_antes = sum(1 for i in ger_inimigos.inimigos if not i.esta_morto())
        for d in self.destrocos:
            if d.esta_morto():
                continue
            for inimigo in ger_inimigos.inimigos:
                if inimigo.esta_morto():
                    continue
                if inimigo.retangulo.colliderect(d.retangulo):
                    # apenas destroços originados de meteoros destruídos pelo player afetam inimigos
                    if d.origem == 'player' and d.poder >= 2:
                        dano = d.poder
                        estava_vivo = inimigo.vivo
                        inimigo.receber_dano(dano)
                        if estava_vivo and inimigo.esta_morto():
                            # marcar recompensa se for UFO abatido
                            if isinstance(inimigo, DiscoVoador):
                                try:
                                    ger_inimigos.ufo_killed = True
                                    ger_inimigos.ufo_killed_pos = (inimigo.x + inimigo.largura/2, inimigo.y + inimigo.altura/2)
                                except Exception:
                                    pass
        vivos_depois = sum(1 for i in ger_inimigos.inimigos if not i.esta_morto())
        return vivos_antes - vivos_depois

    def colidir_com_tiros(self, tiros):
        # tiros do player destróem destroços tiny; outros tamanhos ignoram e o tiro morre
        for d in self.destrocos:
            if d.esta_morto():
                continue
            for t in tiros.tiros:
                if t.esta_morto():
                    continue
                if d.retangulo.colliderect(t.retangulo):
                    if d.poder == 1:  # tiny
                        d.matar()
                    if not getattr(t, 'perfurante', False):
                        t.matar()

    def atualizar(self, dt):
        for d in self.destrocos:
            d.atualizar(dt)
        self.destrocos = [d for d in self.destrocos if not d.esta_morto()]

    def desenhar(self, tela):
        for d in self.destrocos:
            d.desenhar(tela)
