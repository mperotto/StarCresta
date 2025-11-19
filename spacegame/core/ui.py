import pygame

def get_font(size=22):
    try:
        return pygame.font.SysFont(None, size)
    except Exception:
        return pygame.font.Font(None, size)

def draw_text_centered(surface, text, font, color, cx, cy):
    s = font.render(text, True, color)
    surface.blit(s, (cx - s.get_width()//2, cy - s.get_height()//2))

