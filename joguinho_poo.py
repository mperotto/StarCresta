import pygame
import sys
import math
import random
import os
 # ZIP removido: imports não são mais necessários
from abc import ABC, abstractmethod

# -----------------------------
# Configurações
# -----------------------------
LARGURA, ALTURA = 1920, 1080
FPS = 60
VELOCIDADE_JOGADOR = 280
VELOCIDADE_TIRO = -500
TEMPO_ENTRE_INIMIGOS = 1.0
BASE_LARGURA, BASE_ALTURA = 480, 720
SCALE = ALTURA / BASE_ALTURA

def S(v):
    return int(round(v * SCALE))

# escala velocidades base para manter sensação de jogo
VELOCIDADE_JOGADOR = VELOCIDADE_JOGADOR * SCALE
VELOCIDADE_TIRO = VELOCIDADE_TIRO * SCALE

# -----------------------------
# Infraestrutura base
# -----------------------------
def _carregar_sprite(caminho, largura, altura):
    try:
        if os.path.exists(caminho):
            img = pygame.image.load(caminho).convert_alpha()
            return pygame.transform.smoothscale(img, (largura, altura))
    except Exception:
        pass
    return None

def criar_sprite_nave(largura, altura):
    surf = pygame.Surface((largura, altura), pygame.SRCALPHA)
    cx = largura // 2
    # corpo principal (nave estilizada)
    corpo = [(cx, 0), (largura-4, altura-6), (cx, altura-2), (4, altura-6)]
    pygame.draw.polygon(surf, (180, 220, 255), corpo)
    pygame.draw.polygon(surf, (80, 140, 220), corpo, 2)
    # cabine
    pygame.draw.ellipse(surf, (255, 255, 255), (cx-6, 6, 12, 10))
    pygame.draw.ellipse(surf, (100, 200, 255), (cx-5, 7, 10, 8))
    # asas
    asa_esq = [(4, altura-8), (cx-8, altura-12), (cx-10, altura-6)]
    asa_dir = [(largura-4, altura-8), (cx+8, altura-12), (cx+10, altura-6)]
    pygame.draw.polygon(surf, (160, 200, 255), asa_esq)
    pygame.draw.polygon(surf, (160, 200, 255), asa_dir)
    # bico destacando
    pygame.draw.circle(surf, (255, 255, 255), (cx, 2), 2)
    return surf
def carregar_sprite_nave(largura, altura):
    # tenta assets/player.png
    sprite = _carregar_sprite(os.path.join('assets', 'player.png'), largura, altura)
    if sprite:
        return sprite
    return criar_sprite_nave(largura, altura)

def carregar_sprite_inimigo_a(largura, altura):
    sprite = _carregar_sprite(os.path.join('assets', 'enemy_a.png'), largura, altura)
    if sprite:
        return sprite
    return None

def carregar_sprite_inimigo_b(largura, altura):
    sprite = _carregar_sprite(os.path.join('assets', 'enemy_b.png'), largura, altura)
    if sprite:
        return sprite
    return None

def carregar_sprites_asteroide_opcoes(largura, altura):
    # tenta vários meteoros do pack Kenney
    opcoes = [
        'PNG/Meteors/meteorBrown_big1.png',
        'PNG/Meteors/meteorBrown_big2.png',
        'PNG/Meteors/meteorBrown_big3.png',
        'PNG/Meteors/meteorGrey_big1.png',
        'PNG/Meteors/meteorGrey_big2.png',
        'PNG/Meteors/meteorGrey_big3.png',
    ]
    sprites = []
    for nm in opcoes:
        s = _carregar_sprite(os.path.join('assets', 'kenney', nm), largura, altura)
        if s:
            sprites.append(s)
    # fallback: tentará um arquivo único em assets/asteroid.png
    if not sprites:
        s = _carregar_sprite(os.path.join('assets', 'asteroid.png'), largura, altura)
        if s:
            sprites.append(s)
    return sprites

def carregar_sprite_powerup(largura, altura):
    # tenta algumas opções típicas do pack Kenney Power-ups
    candidatos = [
        'PNG/Power-ups/powerupBlue_bolt.png',
        'PNG/Power-ups/powerupYellow_bolt.png',
        'PNG/Power-ups/powerupGreen_bolt.png',
        'PNG/Power-ups/powerupBlue_star.png',
    ]
    # inclui também opções de shield
    candidatos.extend([
        'PNG/Power-ups/powerupBlue_shield.png',
        'PNG/Power-ups/powerupRed_shield.png',
    ])
    for nm in candidatos:
        s = _carregar_sprite(os.path.join('assets', 'kenney', nm), largura, altura)
        if s:
            return s
    return _carregar_sprite(os.path.join('assets', 'powerup.png'), largura, altura)
class ObjetoDeJogo(ABC):
    def __init__(self, x, y, largura, altura):
        self.x, self.y = float(x), float(y)
        self.largura, self.altura = largura, altura
        self.retangulo = pygame.Rect(int(x), int(y), largura, altura)
        self.vivo = True

    @abstractmethod
    def atualizar(self, dt): ...
    @abstractmethod
    def desenhar(self, tela): ...

    def matar(self): self.vivo = False
    def esta_morto(self): return not self.vivo
    def sincronizar_retangulo(self):
        self.retangulo.topleft = (int(self.x), int(self.y))

# -----------------------------
# Jogador e projéteis
# -----------------------------
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

class Jogador(ObjetoDeJogo):
    def __init__(self, x, y):
        super().__init__(x, y, S(36), S(24))
        self.tempo_recarga = 0.0
        self.sprite = carregar_sprite_nave(self.largura, self.altura)
        self.spawn_anim = 0.0

    def atualizar(self, dt):
        if self.spawn_anim > 0.0:
            alvo_y = ALTURA - 80
            self.y = max(alvo_y, self.y - 140 * dt)
            self.spawn_anim = max(0.0, self.spawn_anim - dt)
        else:
            teclas = pygame.key.get_pressed()
            dx = (teclas[pygame.K_RIGHT] - teclas[pygame.K_LEFT]) * VELOCIDADE_JOGADOR * dt
            dy = (teclas[pygame.K_DOWN] - teclas[pygame.K_UP]) * VELOCIDADE_JOGADOR * dt
            self.x = max(0, min(LARGURA - self.largura, self.x + dx))
            self.y = max(0, min(ALTURA - self.altura, self.y + dy))
        self.tempo_recarga = max(0, self.tempo_recarga - dt)
        self.sincronizar_retangulo()

    def desenhar(self, tela):
        tela.blit(self.sprite, self.retangulo.topleft)

    def pode_atirar(self): return self.tempo_recarga <= 0
    def atirar(self):
        self.tempo_recarga = 0.1
        # centraliza o tiro no topo do jogador
        return Tiro(self.x + self.largura/2 - 3, self.y - 12)
    def atirar_super(self):
        # recarga maior para super tiro
        self.tempo_recarga = 0.8
        return SuperTiro(self.x + self.largura/2 - 12, self.y - 18)

# -----------------------------
# Inimigos (base + especializações)
# -----------------------------
class Inimigo(ObjetoDeJogo, ABC):
    def __init__(self, x, y, largura=28, altura=20, vida=1, cor=(255, 120, 120)):
        super().__init__(x, y, S(largura), S(altura))
        self.vida = vida
        self.vida_max = vida
        self.cor = cor

    @abstractmethod
    def mover(self, dt): ...

    def atualizar(self, dt):
        self.mover(dt)
        if self.y > ALTURA:  # saiu da tela
            self.matar()
        self.sincronizar_retangulo()

    def desenhar(self, tela):
        sprite = getattr(self, 'sprite', None)
        if sprite is not None:
            tela.blit(sprite, self.retangulo.topleft)
        else:
            pygame.draw.rect(tela, self.cor, self.retangulo)
        # barra de vida para inimigos com mais de 1 de vida
        if self.vida_max > 1 and self.vida < self.vida_max and self.vivo:
            w = self.largura
            h = 4
            x = int(self.x)
            y = int(self.y) - 6
            # fundo
            pygame.draw.rect(tela, (100, 40, 40), pygame.Rect(x, y, w, h))
            # preenchimento
            pct = max(0.0, min(1.0, self.vida / self.vida_max))
            pygame.draw.rect(tela, (60, 220, 90), pygame.Rect(x, y, int(w * pct), h))
        # escudo visual se ativo
        if hasattr(self, 'shield_timer') and self.shield_timer > 0 and self.vivo:
            cx = int(self.x + self.largura/2)
            cy = int(self.y + self.altura/2)
            r = max(self.largura, self.altura)//2 + 2
            pygame.draw.circle(tela, (120, 200, 255), (cx, cy), int(r), 2)

    def receber_dano(self, dano=1):
        self.vida -= dano
        if self.vida <= 0:
            self.matar()

    # upgrades padrão: inimigo pode ter shield e vshot
    def coletar_upgrade(self, tipo):
        if tipo == 'shield':
            setattr(self, 'shield_timer', 10.0)
        elif tipo == 'v':
            setattr(self, 'vshot_timer', 10.0)

class InimigoDescendo(Inimigo):
    def __init__(self, x, y, velocidade=90):
        super().__init__(x, y, vida=1, cor=(250, 90, 90))
        self.velocidade = velocidade * SCALE
        self.sprite = carregar_sprite_inimigo_a(self.largura, self.altura)

    def mover(self, dt):
        self.y += self.velocidade * dt

class InimigoZigueZague(Inimigo):
    def __init__(self, x, y, velocidade=80, amplitude=60, frequencia=3.0):
        super().__init__(x, y, vida=2, cor=(255, 170, 90))
        self.velocidade = velocidade * SCALE
        self.amplitude = amplitude * SCALE
        self.frequencia = frequencia
        self.tempo = 0.0
        self.x_inicial = x
        self.sprite = carregar_sprite_inimigo_b(self.largura, self.altura)

    def mover(self, dt):
        self.tempo += dt
        self.y += self.velocidade * dt
        self.x = self.x_inicial + self.amplitude * math.sin(self.tempo * self.frequencia)

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

class GerenciadorDeTirosInimigos:
    def __init__(self):
        self.tiros = []
        self.cap_tiros = 18

    def criar(self, tiro: TiroInimigo):
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

class InimigoAtirador(Inimigo):
    def __init__(self, x, y, velocidade=70):
        super().__init__(x, y, largura=28, altura=22, vida=3, cor=(255, 120, 200))
        self.velocidade = velocidade * SCALE
        self.tempo = 0.0
        # cadência base aleatória por inimigo; será ajustada por dificuldade
        self.cd_tiro_base = random.uniform(0.6, 1.1)
        self.shoot_timer = 0.0
        self.sprite = carregar_sprite_inimigo_b(self.largura, self.altura)
        self.shield_timer = 0.0
        self.vshot_timer = 0.0

    def mover(self, dt):
        self.y += self.velocidade * dt
        self.shoot_timer += dt
        if self.shield_timer > 0:
            self.shield_timer = max(0.0, self.shield_timer - dt)
        if self.vshot_timer > 0:
            self.vshot_timer = max(0.0, self.vshot_timer - dt)

    def tentar_atirar(self, tiros_inimigos: 'GerenciadorDeTirosInimigos', jogador: Jogador, asteroides: list, dif_mult: float = 1.0):
        # quanto maior dif_mult, mais rápida (menor intervalo). Mantém um piso para não virar metralhadora.
        effective_cd = max(0.22, self.cd_tiro_base / max(0.1, dif_mult))
        if self.shoot_timer < effective_cd:
            return
        self.shoot_timer = 0.0
        # alvo: 70% jogador, 30% asteroide próximo (com ruído para reduzir precisão)
        alvo_x, alvo_y = jogador.x + jogador.largura/2, jogador.y + jogador.altura/2
        if asteroides and random.random() < 0.3:
            a = min(asteroides, key=lambda a: (a.y - self.y)**2 + (a.x - self.x)**2)
            alvo_x, alvo_y = a.x + a.largura/2, a.y + a.altura/2
        # ruído na mira para evitar acertos inevitáveis
        alvo_x += random.uniform(-100, 100)
        alvo_y += random.uniform(-60, 60)
        # calcula vetores a partir do topo do inimigo
        cx = self.x + self.largura/2
        topy = self.y + self.altura
        dx = alvo_x - cx
        dy = max(20.0, alvo_y - topy)
        mag = (dx*dx + dy*dy) ** 0.5
        # velocidade base do projétil, levemente escalada pela dificuldade (até ~+30%)
        speed = 240.0 * SCALE * (1.0 + 0.1 * (max(1.0, dif_mult) - 1.0))
        vx, vy = dx/mag*speed, dy/mag*speed
        padrao = [-math.radians(10), 0.0, +math.radians(10)] if self.vshot_timer > 0 else [0.0]
        for ang in padrao:
            svx = vx*math.cos(ang) - vy*math.sin(ang)
            svy = vx*math.sin(ang) + vy*math.cos(ang)
            tiros_inimigos.criar(TiroInimigo(cx-2, topy, vx=svx, vy=svy))

    def receber_dano(self, dano=1):
        if self.shield_timer > 0:
            return
        super().receber_dano(dano)

class DiscoVoador(Inimigo):
    def __init__(self, x, y, velocidade=380, direcao=1):
        # OVNI rápido que cruza a tela na horizontal e atira
        super().__init__(x, y, largura=34, altura=18, vida=3, cor=(200, 180, 255))
        self.velocidade = velocidade * SCALE
        self.direcao = 1 if direcao >= 0 else -1
        self.shoot_timer = 0.0
        self.cd_tiro_base = 0.42
        # sprite simples em forma de disco (ellipse)
        try:
            surf = pygame.Surface((self.largura, self.altura), pygame.SRCALPHA)
            pygame.draw.ellipse(surf, (200, 190, 255), (0, 2, self.largura, self.altura-4))
            pygame.draw.ellipse(surf, (120, 110, 200), (0, 2, self.largura, self.altura-4), 2)
            pygame.draw.ellipse(surf, (255, 255, 255), (self.largura//2-6, 0, 12, 8))
            self.sprite = surf
        except Exception:
            self.sprite = None

    def mover(self, dt):
        self.x += self.direcao * self.velocidade * dt
        self.shoot_timer += dt
        if self.x < -self.largura - 8 or self.x > LARGURA + 8:
            self.matar()

    def tentar_atirar(self, tiros_inimigos: 'GerenciadorDeTirosInimigos', jogador: Jogador, asteroides: list, dif_mult: float = 1.0):
        # dispara rajadas rápidas para baixo em direção aproximada ao jogador
        cd = max(0.14, self.cd_tiro_base / max(0.1, dif_mult))
        if self.shoot_timer < cd:
            return
        self.shoot_timer = 0.0
        cx = self.x + self.largura/2
        cy = self.y + self.altura
        # mira com leve imprecisão
        alvo_x = jogador.x + jogador.largura/2 + random.uniform(-100, 100)
        alvo_y = jogador.y + jogador.altura/2 + random.uniform(-40, 60)
        dx = max(-400, min(400, alvo_x - cx))
        dy = max(20.0, alvo_y - cy)
        mag = (dx*dx + dy*dy) ** 0.5
        # leve aumento com dificuldade (até ~+30%)
        speed = 260.0 * SCALE * (1.0 + 0.1 * (max(1.0, dif_mult) - 1.0))
        vx, vy = dx/mag*speed, dy/mag*speed
        # dispara apenas 1 projétil (menos pressão)
        off = 0.0
        svx = vx*math.cos(off) - vy*math.sin(off)
        svy = vx*math.sin(off) + vy*math.cos(off)
        tiros_inimigos.criar(TiroInimigo(cx-2, cy, vx=svx, vy=svy))

class Asteroide(Inimigo):
    def __init__(self, x, y, velocidade=60, categoria=None):
        # categorias: 'tiny','small','med','big'
        if categoria is None:
            categoria = random.choices(['small', 'med', 'big'], weights=[3, 2, 1])[0]
        self.categoria = categoria
        tamanho_por_cat = {'tiny': 16, 'small': 24, 'med': 32, 'big': 48}
        tam = tamanho_por_cat[self.categoria]
        super().__init__(x, y, largura=tam, altura=tam, vida=1, cor=(180, 160, 140))
        self.velocidade = (velocidade * SCALE) * (0.9 if categoria=='big' else 1.0)
        self.angulo = random.uniform(0, 360)
        self.rot_vel = random.uniform(-90, 90)
        sprites = carregar_sprites_asteroide_opcoes(self.largura, self.altura)
        self.base_sprite = random.choice(sprites) if sprites else None

    def mover(self, dt):
        self.y += self.velocidade * dt
        self.angulo = (self.angulo + self.rot_vel * dt) % 360

    def receber_dano(self, dano=1):
        # ao ser atingido, reduz categoria (big->med->small->tiny), só morre no tiny
        ordem = ['tiny', 'small', 'med', 'big']
        idx = ordem.index(self.categoria)
        if idx > 0:
            # encolhe uma categoria
            self.categoria = ordem[idx-1]
            novo_tam = {'tiny': 16, 'small': 24, 'med': 32, 'big': 48}[self.categoria]
            cx, cy = self.x + self.largura/2, self.y + self.altura/2
            self.largura = self.altura = novo_tam
            self.retangulo.size = (novo_tam, novo_tam)
            self.x, self.y = cx - novo_tam/2, cy - novo_tam/2
            # atualiza sprite escalado
            sprites = carregar_sprites_asteroide_opcoes(self.largura, self.altura)
            self.base_sprite = random.choice(sprites) if sprites else None
            self.sincronizar_retangulo()
        else:
            self.matar()

    def desenhar(self, tela):
        if self.base_sprite is not None:
            img = pygame.transform.rotozoom(self.base_sprite, self.angulo, 1.0)
            rect = img.get_rect(center=(int(self.x + self.largura/2), int(self.y + self.altura/2)))
            tela.blit(img, rect.topleft)
        else:
            pygame.draw.circle(tela, (160, 160, 160), (int(self.x + self.largura/2), int(self.y + self.altura/2)), self.largura//2)
# -----------------------------
# Gerenciadores
# -----------------------------
class Upgrade(ObjetoDeJogo):
    def __init__(self, x, y, velocidade=90, tipo='v'):
        super().__init__(x, y, S(18), S(18))
        self.velocidade = velocidade * SCALE
        self.cor = (140, 200, 255)
        self.tipo = tipo  # 'v' (tiro em V) ou 'shield'
        # escolhe sprite por tipo
        # carregar sprite (genérico + shield incluído na função)
        self.sprite = carregar_sprite_powerup(self.largura, self.altura)

    def atualizar(self, dt):
        self.y += self.velocidade * dt
        if self.y > ALTURA:
            self.matar()
        self.sincronizar_retangulo()

    def desenhar(self, tela):
        if self.sprite is not None:
            tela.blit(self.sprite, self.retangulo.topleft)
        else:
            pygame.draw.rect(tela, self.cor, self.retangulo, border_radius=4)

class GerenciadorDeUpgrades:
    def __init__(self):
        self.upgrades = []
        self.tempo = 0.0
        self.intervalo = 1.2

    def criar(self, upgrade: Upgrade):
        self.upgrades.append(upgrade)

    def atualizar(self, dt):
        self.tempo += dt
        if self.tempo >= self.intervalo:
            self.tempo = 0.0
            # chance de spawn aleatória
            if random.random() < 0.28:
                x = 20 + int(random.random() * (LARGURA - 40))
                tipo = 'shield' if random.random() < 0.35 else 'v'
                self.criar(Upgrade(x, -18, tipo=tipo))
        for u in self.upgrades:
            u.atualizar(dt)
        self.upgrades = [u for u in self.upgrades if not u.esta_morto()]

    def desenhar(self, tela):
        for u in self.upgrades:
            u.desenhar(tela)

    def verificar_coleta(self, jogador: Jogador):
        coletados = 0
        for u in self.upgrades:
            if jogador.retangulo.colliderect(u.retangulo):
                if u.tipo == 'shield':
                    jogador.coletou_shield = True
                else:
                    coletados += 1
                u.matar()
        if coletados:
            self.upgrades = [u for u in self.upgrades if not u.esta_morto()]
        return coletados

    def verificar_coleta_por_inimigos(self, inimigos: 'GerenciadorDeInimigos'):
        # inimigos também podem pegar upgrades
        for u in list(self.upgrades):
            for inimigo in inimigos.inimigos:
                if inimigo.retangulo.colliderect(u.retangulo):
                    if hasattr(inimigo, 'coletar_upgrade'):
                        inimigo.coletar_upgrade(u.tipo)
                        u.matar()
                        break
        self.upgrades = [u for u in self.upgrades if not u.esta_morto()]

class Destroco(ObjetoDeJogo):
    def __init__(self, x, y, raio=6, vx=0.0, vy=0.0, origin='env'):
        r = int(round(raio * SCALE))
        r = max(1, r)
        super().__init__(x, y, int(r*2), int(r*2))
        self.raio = int(r)
        self.vx = float(vx)
        self.vy = float(vy)
        self.angulo = random.uniform(0, 360)
        self.rot_vel = random.uniform(-180, 180)
        self.cor = (150 + random.randint(-20, 20), 140 + random.randint(-20, 20), 130 + random.randint(-20, 20))
        # poder do fragmento: maior raio => mais dano
        self.poder = 1 if self.raio < 10 else (2 if self.raio < 15 else 3)
        # sprite opcional (meteoro), escalado ao diâmetro
        sprites = carregar_sprites_asteroide_opcoes(self.largura, self.altura)
        self.base_sprite = random.choice(sprites) if sprites else None
        # origem: 'player' faz dano em inimigos, 'env' não
        self.origem = origin

    def atualizar(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angulo = (self.angulo + self.rot_vel * dt) % 360
        # leve desaceleração, mas nunca parar totalmente; viés para baixo
        self.vx *= (1 - 0.25 * dt)
        self.vy = self.vy * (1 - 0.25 * dt) + (35 * SCALE) * dt
        # velocidade mínima para sair da tela
        if abs(self.vx) < 8*SCALE: self.vx = (8*SCALE) if self.vx >= 0 else -(8*SCALE)
        if abs(self.vy) < 20*SCALE: self.vy = 20*SCALE
        # só somem fora da tela
        if (self.y > ALTURA + self.raio) or (self.y < -self.raio) or (self.x < -self.raio) or (self.x > LARGURA + self.raio):
            self.matar()
        self.sincronizar_retangulo()

    def desenhar(self, tela):
        if self.base_sprite is not None:
            img = pygame.transform.rotozoom(self.base_sprite, self.angulo, 1.0)
            rect = img.get_rect(center=(int(self.x), int(self.y)))
            tela.blit(img, rect.topleft)
        else:
            pygame.draw.circle(tela, self.cor, (int(self.x), int(self.y)), self.raio)

class GerenciadorDeDestrocos:
    def __init__(self):
        self.destrocos = []

    def criar(self, d: Destroco):
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
        # tocar som de explosão (big preferível)
        try:
            jogo = pygame.display.get_surface()  # dummy to ensure pygame initialized
        except Exception:
            jogo = None

    def colidir_com_inimigos(self, ger_inimigos: 'GerenciadorDeInimigos'):
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

    def colidir_com_tiros(self, tiros: 'GerenciadorDeTiros'):
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
class Particula:
    def __init__(self, x, y, vx, vy, vida=0.4, raio=3, cor=(255, 230, 120)):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.vida_max = vida
        self.vida = 0.0
        self.raio_inicial = max(1, int(round(raio * SCALE)))
        self.cor = cor
        self.viva = True

    def atualizar(self, dt):
        if not self.viva:
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vida += dt
        if self.vida >= self.vida_max:
            self.viva = False

    def desenhar(self, tela):
        if not self.viva:
            return
        t = max(0.0, 1.0 - self.vida / self.vida_max)
        raio = max(1, int(self.raio_inicial * t))
        # variação leve na cor com o tempo
        r, g, b = self.cor
        cor = (min(255, int(r * (0.7 + 0.3 * t))), min(255, int(g * (0.7 + 0.3 * t))), min(255, int(b * (0.7 + 0.3 * t))))
        pygame.draw.circle(tela, cor, (int(self.x), int(self.y)), raio)

class GerenciadorDeParticulas:
    def __init__(self):
        self.particulas = []

    def criar(self, p: Particula):
        self.particulas.append(p)

    def spawn_ao_redor(self, x, y, intensidade=6, raio=22, cores=None, vel_base=30, vel_var=80):
        # gera algumas partículas em volta de (x,y)
        if cores is None:
            cores = [(255, 240, 140), (180, 255, 255)]
        for _ in range(intensidade):
            ang = random.random() * math.tau
            dist = (6*SCALE) + random.random() * (raio * SCALE)
            px = x + math.cos(ang) * dist
            py = y + math.sin(ang) * dist
            # velocidade radial
            speed = (vel_base + random.random() * vel_var) * SCALE
            vx = math.cos(ang) * speed
            vy = math.sin(ang) * speed
            vida = 0.3 + random.random() * 0.4
            r0 = 2 + int(random.random() * 3)
            cor = random.choice(cores)
            self.criar(Particula(px, py, vx, vy, vida=vida, raio=r0, cor=cor))

    def atualizar(self, dt):
        for p in self.particulas:
            p.atualizar(dt)
        self.particulas = [p for p in self.particulas if p.viva]

    def desenhar(self, tela):
        for p in self.particulas:
            p.desenhar(tela)

class Estrela:
    def __init__(self, x, y, vel, raio, cor):
        self.x = float(x)
        self.y = float(y)
        self.vel = float(vel) * SCALE
        self.raio = max(1, int(round(raio * SCALE)))
        self.cor = cor

    def atualizar(self, dt):
        self.y += self.vel * dt
        if self.y > ALTURA + self.raio:
            self.y = -self.raio
            self.x = random.uniform(0, LARGURA)

    def desenhar(self, tela):
        pygame.draw.circle(tela, self.cor, (int(self.x), int(self.y)), self.raio)

class CampoEstrelas:
    def __init__(self, quantidade=120):
        self.estrelas = []
        for _ in range(quantidade):
            x = random.uniform(0, LARGURA)
            y = random.uniform(0, ALTURA)
            camada = random.random()
            vel = 20 + camada * 80
            raio = 1 + int(camada * 2)
            cor = (200 + int(55 * camada), 200 + int(55 * camada), 200 + int(55 * camada))
            self.estrelas.append(Estrela(x, y, vel, raio, cor))

    def atualizar(self, dt):
        for e in self.estrelas:
            e.atualizar(dt)

    def desenhar(self, tela):
        for e in self.estrelas:
            e.desenhar(tela)
class GerenciadorDeTiros:
    def __init__(self):
        self.tiros = []

    def criar(self, tiro: Tiro):
        self.tiros.append(tiro)

    def atualizar(self, dt):
        for tiro in self.tiros:
            tiro.atualizar(dt)
        self.tiros = [tiro for tiro in self.tiros if not tiro.esta_morto()]

    def desenhar(self, tela):
        for tiro in self.tiros:
            tiro.desenhar(tela)

class GerenciadorDeInimigos:
    def __init__(self):
        self.inimigos = []
        self.tempo = 0.0
        self.onda = 0
        self.tempo_total = 0.0
        self.ufo_cd = random.uniform(16.0, 28.0)
        self.shot_mult = 1.0
        # recompensa por UFO abatido
        self.ufo_killed = False
        self.ufo_killed_pos = None

    def criar(self, inimigo: Inimigo):
        self.inimigos.append(inimigo)

    def atualizar(self, dt):
        self.tempo_total += dt
        self.tempo += dt
        # dificuldade progressiva
        intervalo = max(0.55, TEMPO_ENTRE_INIMIGOS - self.tempo_total * 0.006)
        speed_mult = min(2.0, 1.0 + self.tempo_total * 0.02)
        # multiplicador para cadência de tiro dos inimigos (1.0 -> 1.3)
        self.shot_mult = min(1.3, 1.0 + self.tempo_total * 0.01)
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
                self.criar(DiscoVoador(x, y, velocidade=380 * speed_mult, direcao=direcao))
            # próximo em 18–30s, mais frequente conforme o tempo
            base_min, base_max = 18.0, 30.0
            fator = max(0.5, 1.0 - self.tempo_total * 0.007)
            self.ufo_cd = random.uniform(base_min * fator, base_max * fator)
        for inimigo in self.inimigos:
            inimigo.atualizar(dt)
        self.inimigos = [inimigo for inimigo in self.inimigos if not inimigo.esta_morto()]

    def desenhar(self, tela):
        for inimigo in self.inimigos:
            inimigo.desenhar(tela)

    def verificar_colisoes_com_tiros(self, gerenciador_de_tiros: GerenciadorDeTiros, destrocos: 'GerenciadorDeDestrocos' = None):
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
        for inimigo in self.inimigos:
            if inimigo.retangulo.colliderect(jogador.retangulo):
                return inimigo
        return None

# -----------------------------
# Jogo
# -----------------------------
class Jogo:
    def __init__(self):
        # tentar reduzir latência de áudio
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
        except Exception:
            pass
        pygame.init()
        pygame.display.set_caption("POO organizada: inimigos simples")
        self.tela = pygame.display.set_mode((LARGURA, ALTURA), pygame.FULLSCREEN)
        self.relogio = pygame.time.Clock()
        self.fonte = pygame.font.SysFont(None, 22)
        self.fonte_grande = pygame.font.SysFont(None, 48)

        # sprites são carregados de assets/; não depende mais de ZIP

        self.jogador = Jogador(LARGURA/2 - 18, ALTURA - 80)
        self.tiros = GerenciadorDeTiros()
        self.inimigos = GerenciadorDeInimigos()
        self.particulas = GerenciadorDeParticulas()
        # menos estrelas no fundo (metade do anterior)
        estrelas_qtd = int(70 * (LARGURA/BASE_LARGURA) * (ALTURA/BASE_ALTURA) / 1.0)
        self.fundo = CampoEstrelas(quantidade=estrelas_qtd)
        self.tiros_inimigos = GerenciadorDeTirosInimigos()
        # liga som de tiro inimigo (se disponível)
        if hasattr(self, 'sfx_enemy_shot') and self.sfx_enemy_shot:
            setattr(self.tiros_inimigos, 'sfx_shot', self.sfx_enemy_shot)
        self.pontuacao = 0
        self.estado = 'jogando'  # 'jogando' | 'pausado' | 'game_over'
        self.carregando_super = False
        self.tempo_carregando = 0.0
        self.sinalizou_super_pronto = False
        self.upgrade_super_timer = 0.0  # buff temporário (s)
        self.player_shield_timer = 0.0
        self.vidas = 3
        self.invul_timer = 0.0
        # áudio
        self._carregar_audio()
        self._tocar_musica()
        self.upgrades = GerenciadorDeUpgrades()
        # carregar sons/música
        self._carregar_audio()
        self._tocar_musica()
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
        def _snd(nome, vol=0.35):
            caminho = os.path.join('sound', nome)
            if os.path.exists(caminho):
                try:
                    s = pygame.mixer.Sound(caminho)
                    s.set_volume(vol)
                    return s
                except Exception:
                    return None
            return None
        self.sfx_shot = _snd('laser1.wav', 0.28) or _snd('shot.wav', 0.28)
        self.sfx_super = _snd('laser_heavy.wav', 0.34) or _snd('super.wav', 0.34)
        self.sfx_explosion_small = _snd('explosion_small.wav', 0.45)
        self.sfx_explosion_big = _snd('explosion_big.wav', 0.52)
        self.sfx_powerup = _snd('powerup.wav', 0.3)
        self.sfx_damage = _snd('damage.wav', 0.35)
        self.sfx_enemy_shot = _snd('laser2.wav', 0.24) or _snd('laser_2.wav', 0.24) or _snd('enemy_shot.wav', 0.24)
        # Sirene/ambiente do UFO (opcional). Toca em loop enquanto houver UFO na tela.
        self.sfx_ufo = (
            _snd('ufo_siren.wav', 0.18)
            or _snd('ufo.wav', 0.18)
            or _snd('siren.wav', 0.18)
            or _snd('ambulancia.wav', 0.18)
            or _snd('ufo_loop.wav', 0.18)
        )
        self.music_path = None
        for cand in ['bg_loop.ogg', 'bg_loop.mp3', 'bg_loop.wav']:
            p = os.path.join('sound', cand)
            if os.path.exists(p):
                self.music_path = p
                break

    def _tocar_musica(self):
        if getattr(self, 'music_path', None):
            try:
                pygame.mixer.music.load(self.music_path)
                pygame.mixer.music.set_volume(0.25)
                pygame.mixer.music.play(-1)
            except Exception:
                pass

    def lidar_com_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if self.estado == 'jogando':
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
                    elif evento.key in (pygame.K_ESCAPE, pygame.K_q):
                        pygame.quit(); sys.exit()

    def atualizar(self, dt):
        # atualiza fundo e partículas mesmo em game over
        if not hasattr(self, 'particulas'):
            self.particulas = GerenciadorDeParticulas()
        if not hasattr(self, 'fundo'):
            self.fundo = CampoEstrelas(quantidade=70)
        self.fundo.atualizar(dt)
        self.particulas.atualizar(dt)
        if not hasattr(self, 'destrocos'):
            self.destrocos = GerenciadorDeDestrocos()
        self.destrocos.atualizar(dt)
        # atualizar textos flutuantes
        if not hasattr(self, 'fx_texts'):
            self.fx_texts = []
        novos = []
        for fx in self.fx_texts:
            fx['t'] += dt
            if fx['t'] <= fx.get('dur', 1.6):
                novos.append(fx)
        self.fx_texts = novos
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

        # upgrades: coleta e aplica (buff 10s, reseta se já ativo)
        coletados = self.upgrades.verificar_coleta(self.jogador)
        if coletados:
            self.upgrade_super_timer = 10.0
            if hasattr(self, 'sfx_powerup') and self.sfx_powerup:
                try:
                    self.sfx_powerup.play()
                except Exception:
                    pass
            # texto flutuante "+1 VIDA"
            try:
                surf = self.fonte.render("+1 VIDA", True, (180, 255, 200))
                self.fx_texts.append({'surf': surf, 'x': cx, 'y': cy - 16, 't': 0.0, 'dur': 1.6})
            except Exception:
                pass
        if self.upgrade_super_timer > 0:
            self.upgrade_super_timer = max(0.0, self.upgrade_super_timer - dt)
        # aplica shield do jogador se coletado
        if getattr(self.jogador, 'coletou_shield', False):
            self.player_shield_timer = 10.0
            self.jogador.coletou_shield = False
        if self.player_shield_timer > 0:
            self.player_shield_timer = max(0.0, self.player_shield_timer - dt)

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

    def reiniciar(self):
        self.jogador = Jogador(LARGURA/2 - 18, ALTURA - 80)
        self.tiros = GerenciadorDeTiros()
        self.inimigos = GerenciadorDeInimigos()
        self.upgrades = GerenciadorDeUpgrades()
        self.pontuacao = 0
        self.estado = 'jogando'
        self.particulas = GerenciadorDeParticulas()
        estrelas_qtd = int(140 * (LARGURA/BASE_LARGURA) * (ALTURA/BASE_ALTURA) / 1.0)
        self.fundo = CampoEstrelas(quantidade=estrelas_qtd)
        self.destrocos = GerenciadorDeDestrocos()
        self.carregando_super = False
        self.tempo_carregando = 0.0
        self.sinalizou_super_pronto = False
        self.upgrade_super_timer = 0.0
        self.vidas = 3
        self.invul_timer = 0.0

    def desenhar(self):
        # Quando usado como "legacy" dentro de uma Scene nova, podemos delegar o fundo.
        if not getattr(self, 'external_background', False):
            self.tela.fill((5, 8, 15))
            self.fundo.desenhar(self.tela)
        self.upgrades.desenhar(self.tela)
        # destroços antes dos sprites principais
        if not hasattr(self, 'destrocos'):
            self.destrocos = GerenciadorDeDestrocos()
        self.destrocos.desenhar(self.tela)
        # nave: pode ser desenhada externamente pela nova Scene
        if not getattr(self, 'external_player', False):
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
        # partículas por cima do jogador
        if not hasattr(self, 'particulas'):
            self.particulas = GerenciadorDeParticulas()
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
        if hasattr(self, 'fx_texts'):
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
        if not getattr(self, 'external_ui', False):
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
                pygame.draw.circle(self.tela, (120, 200, 255), (cx, cy), int(r), 2)
            if self.estado == 'game_over':
                # overlay semi-transparente simples
                overlay = pygame.Surface((LARGURA, ALTURA))
                overlay.set_alpha(140)
                overlay.fill((10, 10, 16))
                self.tela.blit(overlay, (0, 0))
                texto1 = self.fonte_grande.render("GAME OVER", True, (255, 230, 230))
                texto2 = self.fonte.render("Pressione R/Enter/Espaço para reiniciar", True, (220, 230, 255))
                texto3 = self.fonte.render("ESC para sair", True, (200, 210, 230))
                self.tela.blit(texto1, (LARGURA//2 - texto1.get_width()//2, ALTURA//2 - 40))
                self.tela.blit(texto2, (LARGURA//2 - texto2.get_width()//2, ALTURA//2 + 10))
                self.tela.blit(texto3, (LARGURA//2 - texto3.get_width()//2, ALTURA//2 + 36))
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

if __name__ == "__main__":
    Jogo().executar()
