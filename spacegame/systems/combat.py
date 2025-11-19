import pygame

def _rects_collide(a, b):
    return a.retangulo.colliderect(b.retangulo)

def resolve(scene) -> None:
    # Player shots vs enemies
    abates = 0
    for e in scene.enemies:
        if e.esta_morto():
            continue
        for t in scene._shots:
            if t.esta_morto():
                continue
            if _rects_collide(e, t):
                e.matar()
                abates += 1
                if not getattr(t, 'perfurante', False):
                    t.matar()
                break
    if abates:
        try:
            scene._legacy.pontuacao += abates
        except Exception:
            pass
    scene.enemies = [e for e in scene.enemies if not e.esta_morto()]

    # Player vs enemies
    try:
        invul = scene._legacy.invul_timer
    except Exception:
        invul = 0.0
    if invul > 0:
        try:
            scene._legacy.invul_timer = max(0.0, invul - scene._dt)
        except Exception:
            pass
    else:
        for e in scene.enemies:
            if _rects_collide(e, scene._player):
                e.matar()
                # damage player
                try:
                    scene._legacy.vidas -= 1
                    cx = scene._player.x + scene._player.largura/2
                    cy = scene._player.y + scene._player.altura/2
                    # partículas simples
                    try:
                        scene.particles.spawn_ao_redor(cx, cy, intensidade=18, raio=28)
                    except Exception:
                        pass
                    if scene._legacy.vidas <= 0:
                        # game over FX
                        scene._legacy.game_over_fx_active = True
                        scene._legacy.game_over_fx_t = 0.0
                        scene._legacy.game_over_fx_pos = (cx, cy)
                        scene._legacy.game_over_fx_emit = 0.0
                        scene._legacy.jogador.matar()
                        scene._legacy.estado = 'game_over'
                    else:
                        scene._legacy.invul_timer = 1.8
                        scene._legacy.jogador.y = scene._legacy.jogador.y + 0  # keep current; legacy anim cuida
                except Exception:
                    pass
                break
    # Enemy shots vs player
    try:
        shots = scene.enemy_shots.tiros
    except Exception:
        shots = []
    if getattr(scene._legacy, 'invul_timer', 0.0) == 0.0:
        for t in shots:
            if t.esta_morto():
                continue
            if _rects_collide(t, scene._player):
                try:
                    if getattr(scene._legacy, 'player_shield_timer', 0.0) > 0:
                        t.matar(); continue
                except Exception:
                    pass
                # apply damage
                try:
                    scene._legacy.vidas -= 1
                    cx = scene._player.x + scene._player.largura/2
                    cy = scene._player.y + scene._player.altura/2
                    scene.particles.spawn_ao_redor(cx, cy, intensidade=20, raio=28)
                    if scene._legacy.vidas <= 0:
                        scene._legacy.game_over_fx_active = True
                        scene._legacy.game_over_fx_t = 0.0
                        scene._legacy.game_over_fx_pos = (cx, cy)
                        scene._legacy.game_over_fx_emit = 0.0
                        scene._legacy.jogador.matar()
                        scene._legacy.estado = 'game_over'
                    else:
                        scene._legacy.invul_timer = 1.8
                except Exception:
                    pass
                t.matar()
    # Reward: extra life for UFO
    # Award if any killed enemy had is_ufo flag.
    try:
        # best-effort: if any dead this frame UFO, grant life and feedback
        killed_ufos = [e for e in scene.enemies if getattr(e, 'is_ufo', False) and e.esta_morto()]
    except Exception:
        killed_ufos = []
    if killed_ufos:
        try:
            scene._legacy.vidas += 1
            # feedback
            e = killed_ufos[0]
            cx, cy = e.x + e.largura/2, e.y + e.altura/2
            scene.particles.spawn_ao_redor(cx, cy, intensidade=18, raio=28, cores=[(140,255,200),(180,255,220),(220,255,255)], vel_base=70, vel_var=120)
            # floating text in legacy HUD if available
            if hasattr(scene._legacy, 'fx_texts') and hasattr(scene._legacy, 'fonte'):
                surf = scene._legacy.fonte.render("+1 VIDA", True, (180,255,200))
                scene._legacy.fx_texts.append({'surf': surf, 'x': cx, 'y': cy - 16, 't': 0.0, 'dur': 1.6})
        except Exception:
            pass
