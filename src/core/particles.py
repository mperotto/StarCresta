import pygame
import random
import math
import os
from src.settings import *
from src.assets import get_resource_path

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

class Planeta:
    def __init__(self, x, y, vel, escala, imagem, flyby=False, escala_final=None):
        self.x = float(x)
        self.y = float(y)
        self.vel = float(vel) * SCALE
        self.flyby = flyby
        self.escala_inicial = escala
        self.escala_final = escala_final if escala_final is not None else escala
        self.imagem_base = imagem
        self.escala_atual = self.escala_inicial
        self.sprite = None
        self.raio = 0
        self.rescale_cd = 0.0
        self._atualizar_sprite()

    def _atualizar_sprite(self):
        escala = self.escala_atual
        max_w = int(min(LARGURA, ALTURA) * 1.2)
        w = max(32, min(max_w, int(self.imagem_base.get_width() * escala * SCALE)))
        h = max(32, min(max_w, int(self.imagem_base.get_height() * escala * SCALE)))
        self.sprite = pygame.transform.smoothscale(self.imagem_base, (w, h))
        self.raio = max(w, h) // 2

    def atualizar(self, dt):
        self.y += self.vel * dt
        if self.flyby:
            # cresce conforme desce
            perc = max(0.0, min(1.0, (self.y + self.raio) / (ALTURA + self.raio)))
            alvo = self.escala_inicial + (self.escala_final - self.escala_inicial) * perc
            # suaviza zoom com interpolação exponencial
            lerp = 1 - math.exp(-dt * 1.8)
            self.escala_atual = self.escala_atual + (alvo - self.escala_atual) * lerp
            if self.rescale_cd <= 0.0 and abs(alvo - self.escala_atual) > 0.005:
                self._atualizar_sprite()
                self.rescale_cd = 0.08
            else:
                self.rescale_cd = max(0.0, self.rescale_cd - dt)
        if self.y > ALTURA + self.raio:
            self.y = -self.raio
            self.x = random.uniform(0, LARGURA)
            # reinicia escala
            self.escala_atual = self.escala_inicial
            self._atualizar_sprite()

    def desenhar(self, tela):
        rect = self.sprite.get_rect(center=(int(self.x), int(self.y)))
        tela.blit(self.sprite, rect.topleft)

class CampoEstrelas:
    def __init__(self, quantidade=120, planetas=2):
        self.estrelas = []
        self.planetas = []
        self.planeta_imgs = self._carregar_planetas()
        self.max_planetas = max(0, planetas)
        # estrelas menores
        for _ in range(quantidade):
            x = random.uniform(0, LARGURA)
            y = random.uniform(0, ALTURA)
            camada = random.random()
            # parallax leve: camadas distantes andam mais devagar
            if camada < 0.35:
                vel = random.uniform(8, 14)
            elif camada < 0.7:
                vel = random.uniform(15, 28)
            else:
                vel = random.uniform(30, 46)
            # estrelas ainda menores
            raio = 0.25 + camada * 0.8
            brilho = 170 + int(70 * camada)
            cor = (brilho, brilho, 200 + int(40 * camada))
            self.estrelas.append(Estrela(x, y, vel, raio, cor))
        if self.max_planetas > 0:
            # garante um flyby e poucos planetas simultâneos
            self._criar_planeta(force_flyby=True)
            for _ in range(self.max_planetas - 1):
                self._criar_planeta()

    def atualizar(self, dt):
        for e in self.estrelas:
            e.atualizar(dt)
        for p in self.planetas:
            p.atualizar(dt)

    def desenhar(self, tela):
        for e in self.estrelas:
            e.desenhar(tela)
        flybys = [p for p in self.planetas if getattr(p, 'flyby', False)]
        comuns = [p for p in self.planetas if not getattr(p, 'flyby', False)]
        for p in comuns:
            p.desenhar(tela)
        for p in flybys:
            p.desenhar(tela)

    def _carregar_planetas(self):
        imgs = []
        base_path = get_resource_path(os.path.join('assets', 'kenney', 'PNG', 'Planets'))
        if not os.path.isdir(base_path):
            return imgs
        for nome in os.listdir(base_path):
            if not nome.lower().endswith('.png'):
                continue
            if not nome.lower().startswith('planet'):
                continue
            caminho = os.path.join(base_path, nome)
            try:
                img = pygame.image.load(caminho).convert_alpha()
                imgs.append(img)
            except Exception:
                pass
        return imgs

    def _criar_planeta(self, force_flyby=False):
        if not self.planeta_imgs:
            return
        img = random.choice(self.planeta_imgs)
        x = random.uniform(0, LARGURA)
        y = random.uniform(0, ALTURA)
        # alguns bem grandes (flyby) e únicos; demais variam por plano
        ja_tem_grande = any(p.raio > LARGURA * 0.25 for p in self.planetas)
        roll = random.random()
        if (force_flyby or roll < 0.2) and not ja_tem_grande:
            # flyby: planeta gigante ocupando boa parte da tela
            # flyby ocupa praticamente a tela inteira
            alvo = random.uniform(LARGURA * 1.0, LARGURA * 1.45)
            vel = random.uniform(14, 26)
            flyby = True
            escala_final = max(0.05, alvo / max(32, img.get_width()))
            escala_inicial = escala_final * 0.35
        elif roll < 0.45:
            # plano médio
            alvo = random.uniform(120, 220)
            vel = random.uniform(12, 22)
            flyby = False
        else:
            # distante
            alvo = random.uniform(50, 110)
            vel = random.uniform(7, 16)
            flyby = False
        # converte alvo de largura para escala relativa da textura original
        escala = max(0.05, alvo / max(32, img.get_width()))
        if flyby:
            self.planetas.append(Planeta(x, y, vel, escala_inicial, img, flyby=True, escala_final=escala_final))
        else:
            self.planetas.append(Planeta(x, y, vel, escala, img))
