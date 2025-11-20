import pygame
from src.settings import *

class Menu:
    def __init__(self, jogo):
        self.jogo = jogo
        self.fonte_titulo = pygame.font.SysFont(None, 80)
        self.fonte_opcao = pygame.font.SysFont(None, 40)
        self.opcoes = ['Jogar', 'Sair']
        self.selecionado = 0

    def desenhar(self, tela):
        # Fundo escurecido
        overlay = pygame.Surface((LARGURA, ALTURA))
        overlay.set_alpha(200)
        overlay.fill((5, 8, 15))
        tela.blit(overlay, (0, 0))

        # Título
        titulo = self.fonte_titulo.render("STAR CRESTA", True, (100, 200, 255))
        rect_titulo = titulo.get_rect(center=(LARGURA//2, ALTURA//3))
        tela.blit(titulo, rect_titulo)

        # Opções
        for i, opcao in enumerate(self.opcoes):
            cor = (255, 255, 255) if i == self.selecionado else (150, 150, 150)
            texto = self.fonte_opcao.render(opcao, True, cor)
            rect = texto.get_rect(center=(LARGURA//2, ALTURA//2 + i * 60))
            tela.blit(texto, rect)
            
            # Seta de seleção
            if i == self.selecionado:
                pygame.draw.polygon(tela, (255, 255, 255), [
                    (rect.left - 20, rect.centery - 10),
                    (rect.left - 20, rect.centery + 10),
                    (rect.left - 5, rect.centery)
                ])

    def lidar_evento(self, evento):
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_UP:
                self.selecionado = (self.selecionado - 1) % len(self.opcoes)
            elif evento.key == pygame.K_DOWN:
                self.selecionado = (self.selecionado + 1) % len(self.opcoes)
            elif evento.key == pygame.K_RETURN or evento.key == pygame.K_SPACE:
                if self.selecionado == 0:
                    return 'jogar'
                elif self.selecionado == 1:
                    return 'sair'
        return None

class GameOverScreen:
    def __init__(self, jogo):
        self.jogo = jogo
        self.fonte_grande = pygame.font.SysFont(None, 64)
        self.fonte_media = pygame.font.SysFont(None, 36)

    def desenhar(self, tela, pontuacao, high_score):
        overlay = pygame.Surface((LARGURA, ALTURA))
        overlay.set_alpha(180)
        overlay.fill((10, 0, 0))
        tela.blit(overlay, (0, 0))

        t1 = self.fonte_grande.render("GAME OVER", True, (255, 80, 80))
        t2 = self.fonte_media.render(f"Pontuação: {pontuacao}", True, (255, 255, 255))
        t3 = self.fonte_media.render(f"High Score: {high_score}", True, (255, 215, 0))
        t4 = self.fonte_media.render("R - Reiniciar  |  M - Menu  |  ESC - Sair", True, (200, 200, 200))

        tela.blit(t1, t1.get_rect(center=(LARGURA//2, ALTURA//3)))
        tela.blit(t2, t2.get_rect(center=(LARGURA//2, ALTURA//2)))
        tela.blit(t3, t3.get_rect(center=(LARGURA//2, ALTURA//2 + 40)))
        tela.blit(t4, t4.get_rect(center=(LARGURA//2, ALTURA//2 + 100)))
