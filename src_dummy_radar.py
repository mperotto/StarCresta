
    def _draw_radar_hud(self, surf):
        """Desenha instrumentos de navegação no cockpit."""
        if not self.active or self.state == 'inactive':
            return

        # Posição do Radar (Centro Inferior)
        cx = LARGURA // 2
        cy = ALTURA - 80 * SCALE
        w = 300 * SCALE
        h = 100 * SCALE
        
        # Fundo do Radar
        rect = pygame.Rect(cx - w//2, cy - h//2, w, h)
        pygame.draw.rect(surf, (0, 20, 10, 180), rect)
        pygame.draw.rect(surf, (50, 200, 100), rect, 2)
        
        # Grid de Solo (Pseudo-3D no radar)
        # Horizon Line no radar
        radar_horizon = cy 
        if self.banking != 0:
            radar_horizon += math.sin(self.banking) * 20 * SCALE

        # Linhas Verticais (movem com x)
        offset_x = (self.cam_x % 100) / 100.0
        for i in range(-5, 6):
            lx = cx + (i - offset_x) * (w / 8)
            # Perspectiva simples
            # Topo (horizonte) -> Base
            p1 = (lx, radar_horizon)
            # Afasta as linhas na base para efeito 3D
            dist_from_center = (lx - cx) * 2.0
            p2 = (cx + dist_from_center, rect.bottom)
            
            # Clip no rect
            if p2[0] > rect.left and p2[0] < rect.right:
                 pygame.draw.line(surf, (0, 100, 50), p1, p2, 1)

        # Linhas Horizontais (movem com z/velocidade)
        # self.traveled_distance
        offset_z = (self.traveled_distance % 200) / 200.0
        for i in range(4):
            # i=0 (fundo/horizonte) -> i=3 (perto)
            prog = (i + offset_z) / 4.0
            # Exponencial para perspectiva
            y_radar = radar_horizon + (rect.bottom - radar_horizon) * (prog ** 2)
            if y_radar < rect.bottom and y_radar > rect.top:
                pygame.draw.line(surf, (0, 150, 80), (rect.left, int(y_radar)), (rect.right, int(y_radar)), 1)

        # Altímetro (Barra lateral)
        # Altura normalizada (0 a 100)
        alt_norm = max(0, min(1.0, (self.cam_y + 20) / 150.0))
        bar_h = rect.height * 0.8
        bar_x = rect.right + 10 * SCALE
        bar_y = rect.centery - bar_h/2
        
        # Moldura Alt
        pygame.draw.rect(surf, (50, 200, 100), (bar_x, bar_y, 10 * SCALE, bar_h), 1)
        # Preenchimento
        fill_h = bar_h * alt_norm
        pygame.draw.rect(surf, (50, 255, 100), (bar_x, bar_y + bar_h - fill_h, 10 * SCALE, fill_h))
        
        # Texto ALT
        font = pygame.font.SysFont("Arial", int(16 * SCALE), bold=True)
        txt = font.render(f"ALT: {int(self.cam_y + 20)}", True, (150, 255, 180))
        surf.blit(txt, (bar_x + 15 * SCALE, bar_y))
        
        # Texto VEL
        v_kmh = int(self.scroll_speed / 10)
        txt_v = font.render(f"SPD: {v_kmh} MACH", True, (150, 255, 180))
        surf.blit(txt_v, (rect.left - 120 * SCALE, bar_y))

        # Texto STATUS
        status = "AUTOPILOT" if self.state == 'leveling' else "MANUAL"
        col = (255, 200, 50) if status == "MANUAL" else (100, 200, 255)
        txt_st = font.render(status, True, col)
        
        # Piscar se status manual acabou de ativar
        if status == "MANUAL" and (pygame.time.get_ticks() // 500) % 2 == 0:
             surf.blit(txt_st, (cx - txt_st.get_width()//2, rect.top - 20 * SCALE))
        elif status == "AUTOPILOT":
             surf.blit(txt_st, (cx - txt_st.get_width()//2, rect.top - 20 * SCALE))
