import os, pygame
from spacegame.assets import load_sound
from spacegame.settings import SOUND_DIR, W

class AudioSystem:
    def __init__(self, bus):
        self.bus = bus
        self.channel = None
        self.sfx_ufo = self._load_ufo()
        self.ufo_active = False
        self.paused = False
        # subscribe
        bus.on('ufo_spawned', self._ufo_spawned)
        bus.on('ufo_gone', self._ufo_gone)
        bus.on('pause', self._pause)
        bus.on('resume', self._resume)

    def _load_ufo(self):
        cands = ['ufo_siren.wav', 'ufo.wav', 'siren.wav', 'ambulancia.wav', 'ufo_loop.wav']
        for nm in cands:
            p = os.path.join(SOUND_DIR, nm)
            if os.path.exists(p):
                try:
                    return load_sound(p, vol=0.18)
                except Exception:
                    continue
        return None

    # events
    def _ufo_spawned(self, **_):
        self.ufo_active = True
        self._start_if_possible()

    def _ufo_gone(self, **_):
        self.ufo_active = False
        self._stop()

    def _pause(self, **_):
        self.paused = True
        self._pause_channel()

    def _resume(self, **_):
        self.paused = False
        self._start_if_possible()

    # control helpers
    def _start_if_possible(self):
        if self.paused or not self.ufo_active or not self.sfx_ufo:
            return
        try:
            if self.channel is None:
                ch = pygame.mixer.find_channel()
                if ch is None:
                    return
                ch.play(self.sfx_ufo, loops=-1)
                self.channel = ch
            else:
                # ensure playing
                if not self.channel.get_busy():
                    self.channel.play(self.sfx_ufo, loops=-1)
        except Exception:
            pass

    def _stop(self):
        try:
            if self.channel is not None:
                self.channel.stop()
        except Exception:
            pass
        self.channel = None

    def _pause_channel(self):
        try:
            if self.channel is not None:
                self.channel.pause()
        except Exception:
            pass

    def update(self, scene):
        # adjust pan/volume based on nearest UFO position
        if not self.channel or not self.ufo_active:
            return
        try:
            ufos = [e for e in scene.enemies if getattr(e, 'is_ufo', False) and not e.esta_morto()]
            if not ufos:
                return
            u = min(ufos, key=lambda obj: abs((obj.x + obj.largura/2) - (W/2)))
            ux = u.x + u.largura/2
            cx = W / 2.0
            norm = max(-1.0, min(1.0, (ux - cx) / cx))
            vol_scale = 0.35 + 0.65 * (1.0 - abs(norm)) ** 0.8
            aproximando = (getattr(u, 'direcao', 1) > 0 and ux < cx) or (getattr(u, 'direcao', 1) < 0 and ux > cx)
            vol_scale *= 1.06 if aproximando else 0.94
            vol_scale = max(0.1, min(1.0, vol_scale))
            left = vol_scale * (1.0 - norm) * 0.5
            right = vol_scale * (1.0 + norm) * 0.5
            self.channel.set_volume(left, right)
        except Exception:
            pass

