import sys
import pygame


def processar_eventos(jogo):
    """Processa eventos e delega transicoes de estado."""
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_F12:
            try:
                jogo.toggle_fps_display()
            except Exception:
                pass

        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_F9:
            try:
                jogo.salvar_screenshot()
            except Exception:
                pass

        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_t:
            try:
                jogo.debug_tex_enabled = not getattr(jogo, "debug_tex_enabled", True)
                r = getattr(jogo.planet_stage, "renderer3d", None)
                if r:
                    r.set_texture_enabled(jogo.debug_tex_enabled)
            except Exception:
                pass

        if evento.type == pygame.KEYDOWN and evento.key == pygame.K_m:
            try:
                jogo.debug_tex_mode = 0 if getattr(jogo, "debug_tex_mode", 1) == 1 else 1
                r = getattr(jogo.planet_stage, "renderer3d", None)
                if r and hasattr(r, "program"):
                    r.program['tex_mode'].value = jogo.debug_tex_mode
            except Exception:
                pass

        # Controles do visualizador de imagem (mouse/teclas dedicadas)
        if getattr(jogo, "image_viewer_active", False):
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_r:
                try:
                    jogo.reset_image_view()
                except Exception:
                    pass
                continue

            if evento.type == pygame.MOUSEWHEEL:
                try:
                    fator = 1.1 if evento.y > 0 else 1 / 1.1
                    jogo.image_zoom = max(0.05, min(20.0, jogo.image_zoom * fator))
                except Exception:
                    pass
                continue

            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                try:
                    jogo.image_dragging = True
                    jogo.image_last_mouse = getattr(evento, "pos", pygame.mouse.get_pos())
                except Exception:
                    pass
                continue

            if evento.type == pygame.MOUSEBUTTONUP and evento.button == 1:
                try:
                    jogo.image_dragging = False
                    jogo.image_last_mouse = None
                except Exception:
                    pass
                continue

            if evento.type == pygame.MOUSEMOTION and getattr(jogo, "image_dragging", False):
                try:
                    mx, my = getattr(evento, "pos", pygame.mouse.get_pos())
                    lx, ly = jogo.image_last_mouse or (mx, my)
                    dx = mx - lx
                    dy = my - ly
                    jogo.image_offset_x += dx
                    jogo.image_offset_y += dy
                    jogo.image_last_mouse = (mx, my)
                except Exception:
                    pass
                continue

        if jogo.estado == "menu":
            acao = jogo.menu.lidar_evento(evento)
            if acao == "jogar":
                jogo.reiniciar()
                jogo.estado = "jogando"
                jogo.limpar_buffer_entrada(220)
            elif acao == "sair":
                pygame.quit()
                sys.exit()

        elif jogo.estado == "jogando":
            if evento.type in (pygame.KEYDOWN, pygame.KEYUP):
                if getattr(jogo, "entrada_bloqueada", None) and jogo.entrada_bloqueada():
                    continue

            # Pausa com confirmacao (ESC/Q abre pausa)
            if evento.type == pygame.KEYDOWN and evento.key in (pygame.K_ESCAPE, pygame.K_q):
                jogo.estado = "pausado"
                jogo.carregando_super = False
                jogo.tempo_carregando = 0.0
                jogo.sinalizou_super_pronto = False
                try:
                    pygame.mixer.music.pause()
                except Exception:
                    pass
                try:
                    if jogo.ufo_channel is not None:
                        jogo.ufo_channel.pause()
                except Exception:
                    pass
                return

            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_SPACE:
                # laser continuo ignora input manual
                if jogo.laser_wave_expire is not None:
                    return
                if jogo.jogador.pode_atirar():
                    jogo.disparar_normal()

            # atalho: entrar direto no mini-game 3D
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_p:
                if not jogo.in_planet_stage:
                    jogo.player_shield_layers = max(1, getattr(jogo, "player_shield_layers", 0))
                    jogo.player_shield_hp = 3
                    jogo.in_planet_stage = True
                    jogo.planet_stage.start(None, no_shield=False)
                    jogo.inimigos.inimigos.clear()
                    jogo.tiros_inimigos.tiros.clear()
                    jogo.tiros.tiros.clear()
                    jogo.destrocos.destrocos.clear()
                    return

            if evento.type == pygame.KEYUP and evento.key == pygame.K_SPACE:
                if jogo.laser_wave_expire is not None:
                    return
                # Se soltou a barra de espaco e estava carregado, dispara o super
                if jogo.tempo_carregando >= 1.0:
                    jogo.disparar_super()

                # Reseta carga
                jogo.carregando_super = False
                jogo.tempo_carregando = 0.0
                jogo.sinalizou_super_pronto = False

        elif jogo.estado == "pausado":
            if evento.type == pygame.KEYDOWN:
                # confirmacao explicita: S para sair; N/ESC/Enter/Espaco/P/R/C para continuar
                if evento.key in (pygame.K_s,):
                    pygame.quit()
                    sys.exit()
                if evento.key in (
                    pygame.K_n,
                    pygame.K_ESCAPE,
                    pygame.K_RETURN,
                    pygame.K_SPACE,
                    pygame.K_p,
                    pygame.K_r,
                    pygame.K_c,
                ):
                    jogo.estado = "jogando"
                    try:
                        pygame.mixer.music.unpause()
                    except Exception:
                        pass
                    try:
                        if jogo.ufo_channel is not None:
                            jogo.ufo_channel.unpause()
                    except Exception:
                        pass

        elif jogo.estado == "game_over":
            if jogo.entering_initials:
                if getattr(jogo, "entrada_bloqueada", None) and jogo.entrada_bloqueada():
                    continue
                if evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_BACKSPACE:
                        jogo.initials_input = jogo.initials_input[:-1]
                    elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        jogo._registrar_iniciais()
                    else:
                        ch = evento.unicode.upper() if hasattr(evento, "unicode") else ""
                        # aceita apenas letras/numeros
                        if ch.isalpha() or ch.isdigit():
                            if len(jogo.initials_input) < 3:
                                jogo.initials_input += ch
                return

            if evento.type == pygame.KEYDOWN:
                if evento.key in (pygame.K_r, pygame.K_SPACE, pygame.K_RETURN):
                    jogo.reiniciar()
                    jogo.limpar_buffer_entrada(220)
                elif evento.key == pygame.K_m:
                    jogo.estado = "menu"
                    jogo._tocar_musica(jogo.music_path)
                    jogo.limpar_buffer_entrada(220)
                elif evento.key in (pygame.K_ESCAPE, pygame.K_q):
                    pygame.quit()
                    sys.exit()
