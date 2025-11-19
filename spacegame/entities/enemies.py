import pygame, math, random
from spacegame.entities.base import ObjetoDeJogo
from spacegame.settings import S, SCALE, W, H
from spacegame.assets import get_enemy_a_sprite, get_enemy_b_sprite
from spacegame.entities.bullets import Tiro as PlayerTiro  # for type hints only

class Inimigo(ObjetoDeJogo):
    def __init__(self, x, y, largura=28, altura=20, vida=1, cor=(255, 120, 120)):
        super().__init__(x, y, S(largura), S(altura))
        self.vida = vida
        self.vida_max = vida
        self.cor = cor

    def mover(self, dt):
        raise NotImplementedError

    def atualizar(self, dt):
        self.mover(dt)
        if self.y > H:
            self.matar()
        self.sincronizar_retangulo()

    def desenhar(self, tela):
        sprite = getattr(self, 'sprite', None)
        if sprite is not None:
            tela.blit(sprite, self.retangulo.topleft)
        else:
            pygame.draw.rect(tela, self.cor, self.retangulo)

    def receber_dano(self, dano=1):
        self.vida -= dano
        if self.vida <= 0:
            self.matar()

class InimigoDescendo(Inimigo):
    def __init__(self, x, y, velocidade=90):
        super().__init__(x, y, vida=1, cor=(250, 90, 90))
        self.velocidade = velocidade * SCALE
        self.sprite = get_enemy_a_sprite((self.largura, self.altura))

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
        self.sprite = get_enemy_b_sprite((self.largura, self.altura))

    def mover(self, dt):
        self.tempo += dt
        self.y += self.velocidade * dt
        self.x = self.x_inicial + self.amplitude * math.sin(self.tempo * self.frequencia)

class InimigoAtirador(Inimigo):
    def __init__(self, x, y, velocidade=70):
        super().__init__(x, y, largura=28, altura=22, vida=3, cor=(255, 120, 200))
        self.velocidade = velocidade * SCALE
        self.shoot_timer = 0.0
        self.cd_tiro_base = random.uniform(0.6, 1.1)
        self.sprite = get_enemy_b_sprite((self.largura, self.altura))
        self.shield_timer = 0.0
        self.vshot_timer = 0.0

    def mover(self, dt):
        self.y += self.velocidade * dt
        self.shoot_timer += dt
        if self.shield_timer > 0:
            self.shield_timer = max(0.0, self.shield_timer - dt)
        if self.vshot_timer > 0:
            self.vshot_timer = max(0.0, self.vshot_timer - dt)

    def tentar_atirar(self, tiros_inimigos: 'GerenciadorDeTirosInimigos', jogador, dif_mult: float = 1.0, asteroides=None):
        cd = max(0.22, self.cd_tiro_base / max(0.1, dif_mult))
        if self.shoot_timer < cd:
            return
        self.shoot_timer = 0.0
        alvo_x, alvo_y = jogador.x + jogador.largura/2, jogador.y + jogador.altura/2
        alvo_x += random.uniform(-100, 100)
        alvo_y += random.uniform(-60, 60)
        cx = self.x + self.largura/2
        topy = self.y + self.altura
        dx = alvo_x - cx
        dy = max(20.0, alvo_y - topy)
        mag = (dx*dx + dy*dy) ** 0.5
        speed = 240.0 * SCALE * (1.0 + 0.1 * (max(1.0, dif_mult) - 1.0))
        vx, vy = dx/mag*speed, dy/mag*speed
        padrao = [-math.radians(10), 0.0, +math.radians(10)] if self.vshot_timer > 0 else [0.0]
        for ang in padrao:
            svx = vx*math.cos(ang) - vy*math.sin(ang)
            svy = vx*math.sin(ang) + vy*math.cos(ang)
            tiros_inimigos.criar(TiroInimigo(cx-2, topy, vx=svx, vy=svy))

class TiroInimigo(ObjetoDeJogo):
    def __init__(self, x, y, vx=0.0, vy=180):
        super().__init__(x, y, S(4), S(10))
        self.vx = float(vx)
        self.vy = float(vy) * SCALE

    def atualizar(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.y > H + self.altura or self.x < -self.largura or self.x > W:
            self.matar()
        self.sincronizar_retangulo()

    def desenhar(self, tela):
        pygame.draw.rect(tela, (255, 100, 120), self.retangulo)

class GerenciadorDeTirosInimigos:
    def __init__(self):
        self.tiros = []
        self.cap_tiros = 18

    def criar(self, tiro: TiroInimigo):
        if len(self.tiros) >= getattr(self, 'cap_tiros', 18):
            return
        self.tiros.append(tiro)
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

class DiscoVoador(Inimigo):
    def __init__(self, x, y, velocidade=380, direcao=1):
        super().__init__(x, y, largura=34, altura=18, vida=3, cor=(200, 180, 255))
        self.velocidade = velocidade * SCALE
        self.direcao = 1 if direcao >= 0 else -1
        self.shoot_timer = 0.0
        self.cd_tiro_base = 0.42
        self.is_ufo = True
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
        if self.x < -self.largura - 8 or self.x > W + 8:
            self.matar()

    def tentar_atirar(self, tiros_inimigos: 'GerenciadorDeTirosInimigos', jogador, dif_mult: float = 1.0):
        cd = max(0.14, self.cd_tiro_base / max(0.1, dif_mult))
        if self.shoot_timer < cd:
            return
        self.shoot_timer = 0.0
        cx = self.x + self.largura/2
        cy = self.y + self.altura
        alvo_x = jogador.x + jogador.largura/2 + random.uniform(-100, 100)
        alvo_y = jogador.y + jogador.altura/2 + random.uniform(-40, 60)
        dx = max(-400, min(400, alvo_x - cx))
        dy = max(20.0, alvo_y - cy)
        mag = (dx*dx + dy*dy) ** 0.5
        speed = 260.0 * SCALE * (1.0 + 0.1 * (max(1.0, dif_mult) - 1.0))
        vx, vy = dx/mag*speed, dy/mag*speed
        from spacegame.entities.enemies import TiroInimigo  # local import to avoid cycle
        tiros_inimigos.criar(TiroInimigo(cx-2, cy, vx=vx, vy=vy))
