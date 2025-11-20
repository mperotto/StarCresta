import pygame
from abc import ABC, abstractmethod

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
