import pygame
import random
import math
from src.settings import *

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
    def __init__(self, x, y, vel, raio, cor, halo):
        self.x = float(x)
        self.y = float(y)
        self.vel = float(vel) * SCALE
        self.raio = max(6, int(round(raio * SCALE)))
        self.cor = cor
        self.halo = halo

    def atualizar(self, dt):
        self.y += self.vel * dt
        if self.y > ALTURA + self.raio:
            self.y = -self.raio
            self.x = random.uniform(0, LARGURA)

    def desenhar(self, tela):
        cx, cy = int(self.x), int(self.y)
        # halo suave
        pygame.draw.circle(tela, self.halo, (cx, cy), int(self.raio * 1.25))
        # corpo
        pygame.draw.circle(tela, self.cor, (cx, cy), self.raio)
        # reflexo simples
        pygame.draw.circle(tela, (255, 255, 255), (cx - self.raio//3, cy - self.raio//3), max(2, self.raio//4))

class CampoEstrelas:
    def __init__(self, quantidade=120, planetas=3):
        self.estrelas = []
        self.planetas = []
        for _ in range(quantidade):
            x = random.uniform(0, LARGURA)
            y = random.uniform(0, ALTURA)
            camada = random.random()
            vel = 20 + camada * 80
            raio = 1 + int(camada * 2)
            cor = (200 + int(55 * camada), 200 + int(55 * camada), 200 + int(55 * camada))
            self.estrelas.append(Estrela(x, y, vel, raio, cor))
        for _ in range(planetas):
            x = random.uniform(0, LARGURA)
            y = random.uniform(0, ALTURA)
            raio = random.uniform(18, 38)
            vel = random.uniform(35, 60)
            base = random.randint(80, 160)
            cor = (base + 50, base + 30, base + 10)
            halo = (base, base, base + 40)
            self.planetas.append(Planeta(x, y, vel, raio, cor, halo))

    def atualizar(self, dt):
        for e in self.estrelas:
            e.atualizar(dt)
        for p in self.planetas:
            p.atualizar(dt)

    def desenhar(self, tela):
        for e in self.estrelas:
            e.desenhar(tela)
        for p in self.planetas:
            p.desenhar(tela)
