import random
from spacegame.settings import W, TEMPO_ENTRE_INIMIGOS, S
from spacegame.entities.enemies import InimigoDescendo, InimigoZigueZague, DiscoVoador, InimigoAtirador

class Spawner:
    def __init__(self):
        self.tempo = 0.0
        self.onda = 0
        self.tempo_total = 0.0
        self.ufo_cd = random.uniform(16.0, 28.0)

    def update(self, dt: float, enemies: list):
        self.tempo_total += dt
        self.tempo += dt
        intervalo = max(0.55, TEMPO_ENTRE_INIMIGOS - self.tempo_total * 0.006)
        speed_mult = min(2.0, 1.0 + self.tempo_total * 0.02)
        if self.tempo >= intervalo:
            self.tempo = 0.0
            self.onda += 1
            x = 40 + (self.onda * 53) % (W - 80)
            if self.onda % 5 == 0:
                enemies.append(InimigoAtirador(x, -26, velocidade=70 * speed_mult))
            elif self.onda % 3 == 0:
                enemies.append(InimigoZigueZague(x, -30, velocidade=80 * speed_mult))
            else:
                enemies.append(InimigoDescendo(x, -26, velocidade=90 * speed_mult))
        # UFO raro
        self.ufo_cd -= dt
        if self.ufo_cd <= 0.0:
            existe = any(getattr(i, 'is_ufo', False) and not i.esta_morto() for i in enemies)
            if not existe:
                direcao = 1 if random.random() < 0.5 else -1
                y = random.randint(S(60), S(160))
                x = -S(40) if direcao == 1 else W + S(40)
                enemies.append(DiscoVoador(x, y, velocidade=380 * speed_mult, direcao=direcao))
            base_min, base_max = 18.0, 30.0
            fator = max(0.5, 1.0 - self.tempo_total * 0.007)
            import random as _r
            self.ufo_cd = _r.uniform(base_min * fator, base_max * fator)
