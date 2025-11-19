import pygame

class ObjetoDeJogo:
    def __init__(self, x, y, largura, altura):
        self.x, self.y = float(x), float(y)
        self.largura, self.altura = int(largura), int(altura)
        self.retangulo = pygame.Rect(int(x), int(y), int(largura), int(altura))
        self.vivo = True

    def atualizar(self, dt: float):
        raise NotImplementedError

    def desenhar(self, tela):
        raise NotImplementedError

    def matar(self):
        self.vivo = False

    def esta_morto(self):
        return not self.vivo

    def sincronizar_retangulo(self):
        self.retangulo.topleft = (int(self.x), int(self.y))

