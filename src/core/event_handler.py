import sys
import pygame


def processar_eventos(jogo):
    """Processa eventos e delega transições de estado."""
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if jogo.estado == "menu":
            acao = jogo.menu.lidar_evento(evento)
            if acao == "jogar":
                jogo.reiniciar()
                jogo.estado = "jogando"
            elif acao == "sair":
                pygame.quit()
                sys.exit()

        elif jogo.estado == "jogando":
            # Pausa com confirmação (ESC/Q abre pausa)
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
                # laser contínuo ignora input manual
                if jogo.laser_wave_expire is not None:
                    return
                if jogo.jogador.pode_atirar():
                    if jogo.tempo_carregando >= 1.0:
                        jogo.disparar_super()
                    else:
                        jogo.disparar_normal()
                    # reinicia ciclo de carga imediatamente
                    jogo.carregando_super = False
                    jogo.tempo_carregando = 0.0
                    jogo.sinalizou_super_pronto = False

        elif jogo.estado == "pausado":
            if evento.type == pygame.KEYDOWN:
                # confirmação explícita: S para sair; N/ESC/Enter/Espaço/P/R/C para continuar
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
                if evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_BACKSPACE:
                        jogo.initials_input = jogo.initials_input[:-1]
                    elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        jogo._registrar_iniciais()
                    else:
                        ch = evento.unicode.upper() if hasattr(evento, "unicode") else ""
                        # aceita apenas letras/números para evitar espaços acidentais durante tiros
                        if ch.isalpha() or ch.isdigit():
                            if len(jogo.initials_input) < 3:
                                jogo.initials_input += ch
                            if len(jogo.initials_input) >= 3:
                                jogo._registrar_iniciais()
                return
            else:
                if evento.type == pygame.KEYDOWN:
                    if evento.key in (pygame.K_r, pygame.K_SPACE, pygame.K_RETURN):
                        jogo.reiniciar()
                    elif evento.key == pygame.K_m:
                        jogo.estado = "menu"
                        jogo._tocar_musica(jogo.music_path)
                    elif evento.key in (pygame.K_ESCAPE, pygame.K_q):
                        pygame.quit()
                        sys.exit()
