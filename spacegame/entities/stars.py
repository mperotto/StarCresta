import pygame, random
from spacegame.settings import LARGURA as W if False else None
from spacegame.settings import W, H, SCALE

class Estrela:
    def __init__(self, x, y, vel, raio, cor):
        self.x = float(x)
        self.y = float(y)
        self.vel = float(vel) * SCALE
        self.raio = max(1, int(round(raio * SCALE)))
        self.cor = cor

    def atualizar(self, dt):
        self.y += self.vel * dt
        if self.y > H + self.raio:
            self.y = -self.raio
            self.x = random.uniform(0, W)

    def desenhar(self, tela):
        pygame.draw.circle(tela, self.cor, (int(self.x), int(self.y)), self.raio)

class CampoEstrelas:
    def __init__(self, quantidade=120):
        self.estrelas = []
        for _ in range(quantidade):
            x = random.uniform(0, W)
            y = random.uniform(0, H)
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

