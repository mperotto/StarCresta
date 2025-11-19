# Basic settings and scaling helpers

W, H = 1920, 1080
FPS = 60

BASE_W, BASE_H = 480, 720
SCALE = H / BASE_H

def S(v: float) -> int:
    return int(round(v * SCALE))

# Gameplay base speeds (scaled below)
VELOCIDADE_JOGADOR_BASE = 280
VELOCIDADE_TIRO_BASE = -500
TEMPO_ENTRE_INIMIGOS = 1.0

# Scaled speeds
VELOCIDADE_JOGADOR = VELOCIDADE_JOGADOR_BASE * SCALE
VELOCIDADE_TIRO = VELOCIDADE_TIRO_BASE * SCALE

# Input keys (can be extended later)
KEY_PAUSE = ("ESC", "Q")
KEY_RESUME = ("ENTER", "SPACE", "R", "P", "C", "ESC", "N")

# Paths (centralize here if needed later)
ASSETS_DIR = "assets"
SOUND_DIR = "sound"
