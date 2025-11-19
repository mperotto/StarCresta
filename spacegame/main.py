import sys
import pygame
from spacegame.settings import W, H, FPS

# Phase 1 bootstrap: run legacy game inside a simple scene loop
def run():
    pygame.init()
    screen = pygame.display.set_mode((W, H), pygame.FULLSCREEN)
    clock = pygame.time.Clock()

    try:
        from spacegame.scenes.game import GameScene
        scene = GameScene()
        scene.enter()
    except Exception as e:
        print("Failed to init scene:", e)
        pygame.quit()
        sys.exit(1)

    while True:
        dt = clock.tick(FPS) / 1000.0
        # Não drenamos a fila de eventos aqui; a cena/legado consome via pygame.event.get()
        scene.update(dt)
        scene.draw(screen)
        pygame.display.flip()

if __name__ == "__main__":
    run()
