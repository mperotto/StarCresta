import pygame
import random
import math
import os
from src.settings import *
from src.assets import get_resource_path

class Particula:
    def __init__(self, x, y, vx, vy, vida=0.4, raio=3, cor=(255, 230, 120)):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.vida_max = vida
        self.vida = 0.0
        self.raio_inicial = max(1, int(round(raio * SCALE)))
        self.cor = cor
        self.viva = True

    def atualizar(self, dt):
        if not self.viva:
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vida += dt
        if self.vida >= self.vida_max:
            self.viva = False

    def desenhar(self, tela):
        if not self.viva:
            return
        t = max(0.0, 1.0 - self.vida / self.vida_max)
        raio = max(1, int(self.raio_inicial * t))
        # variação leve na cor com o tempo
        r, g, b = self.cor
        cor = (min(255, int(r * (0.7 + 0.3 * t))), min(255, int(g * (0.7 + 0.3 * t))), min(255, int(b * (0.7 + 0.3 * t))))
        pygame.draw.circle(tela, cor, (int(self.x), int(self.y)), raio)

class GerenciadorDeParticulas:
    def __init__(self):
        self.particulas = []

    def criar(self, p: Particula):
        self.particulas.append(p)

    def spawn_ao_redor(self, x, y, intensidade=6, raio=22, cores=None, vel_base=30, vel_var=80):
        # gera algumas partículas em volta de (x,y)
        if cores is None:
            cores = [(255, 240, 140), (180, 255, 255)]
        for _ in range(intensidade):
            ang = random.random() * math.tau
            dist = (6*SCALE) + random.random() * (raio * SCALE)
            px = x + math.cos(ang) * dist
            py = y + math.sin(ang) * dist
            # velocidade radial
            speed = (vel_base + random.random() * vel_var) * SCALE
            vx = math.cos(ang) * speed
            vy = math.sin(ang) * speed
            vida = 0.3 + random.random() * 0.4
            r0 = 2 + int(random.random() * 3)
            cor = random.choice(cores)
            self.criar(Particula(px, py, vx, vy, vida=vida, raio=r0, cor=cor))

    def atualizar(self, dt):
        for p in self.particulas:
            p.atualizar(dt)
        self.particulas = [p for p in self.particulas if p.viva]

    def spawn_plasma_drag(self, obj):
        # Gera partículas de plasma (arrasto atmosférico) ao redor do objeto
        # Cores quentes e transparentes
        if random.random() > 0.4: # Não gera todo frame para não saturar
            return
            
        x = obj.x + random.uniform(0, obj.largura)
        y = obj.y + random.uniform(obj.altura * 0.5, obj.altura) # Mais na parte de baixo/trás
        
        # Velocidade para cima (rastro)
        vx = random.uniform(-20, 20) * SCALE
        vy = -random.uniform(50, 100) * SCALE
        
        vida = 0.2 + random.random() * 0.2
        raio = random.uniform(1, 3)
        
        # Laranja/Vermelho bem suave
        cor = (255, random.randint(100, 180), 50)
        
        p = Particula(x, y, vx, vy, vida=vida, raio=raio, cor=cor)
        self.criar(p)

    def desenhar(self, tela):
        for p in self.particulas:
            p.desenhar(tela)

class Estrela:
    def __init__(self, x, y, vel, raio, cor):
        self.x = float(x)
        self.y = float(y)
        self.vel = float(vel) * SCALE
        self.raio = max(1, int(round(raio * SCALE)))
        self.cor = cor

    def atualizar(self, dt):
        self.y += self.vel * dt
        if self.y > ALTURA + self.raio:
            self.y = -self.raio
            self.x = random.uniform(0, LARGURA)

    def desenhar(self, tela):
        pygame.draw.circle(tela, self.cor, (int(self.x), int(self.y)), self.raio)

class Planeta:
    def __init__(self, x, y, vel, escala, imagem, flyby=False, escala_final=None, super_flyby=False):
        self.x = float(x)
        self.y = float(y)
        self.vel = float(vel) * SCALE
        self.flyby = flyby
        self.super_flyby = super_flyby
        self.escala_inicial = escala
        self.escala_final = escala_final if escala_final is not None else escala
        self.imagem_base = imagem
        self.escala_atual = self.escala_inicial
        self.sprite = None
        self.raio = 0
        self.rescale_cd = 0.0
        self._atualizar_sprite()

    def _atualizar_sprite(self):
        escala = self.escala_atual
        # Se for super flyby, permite crescer muito mais
        limit = 4.0 if self.super_flyby else 1.2
        max_w = int(min(LARGURA, ALTURA) * limit)
        w = max(32, min(max_w, int(self.imagem_base.get_width() * escala * SCALE)))
        h = max(32, min(max_w, int(self.imagem_base.get_height() * escala * SCALE)))
        self.sprite = pygame.transform.smoothscale(self.imagem_base, (w, h))
        self.raio = max(w, h) // 2

    def atualizar(self, dt):
        self.y += self.vel * dt
        if self.flyby:
            # cresce conforme desce
            perc = max(0.0, min(1.0, (self.y + self.raio) / (ALTURA + self.raio)))
            alvo = self.escala_inicial + (self.escala_final - self.escala_inicial) * perc
            # suaviza zoom com interpolação exponencial
            base = 1.8
            if self.super_flyby:
                base = 1.1
            lerp = 1 - math.exp(-dt * base)
            self.escala_atual = self.escala_atual + (alvo - self.escala_atual) * lerp
            if self.rescale_cd <= 0.0 and abs(alvo - self.escala_atual) > 0.005:
                self._atualizar_sprite()
                self.rescale_cd = 0.08
            else:
                self.rescale_cd = max(0.0, self.rescale_cd - dt)
        if self.y > ALTURA + self.raio:
            self.y = -self.raio
            self.x = random.uniform(0, LARGURA)
            # reinicia escala e remove flag de super para não repetir
            self.escala_atual = self.escala_inicial
            self.super_flyby = False
            self._atualizar_sprite()

    def desenhar(self, tela):
        rect = self.sprite.get_rect(center=(int(self.x), int(self.y)))
        tela.blit(self.sprite, rect.topleft)

class CampoEstrelas:
    def __init__(self, quantidade=120, planetas=2):
        self.estrelas = []
        self.planetas = []
        self.planeta_imgs = self._carregar_planetas()
        self.max_planetas = max(0, planetas)
        # estrelas menores
        for _ in range(quantidade):
            x = random.uniform(0, LARGURA)
            y = random.uniform(0, ALTURA)
            camada = random.random()
            # parallax leve: camadas distantes andam mais devagar
            if camada < 0.35:
                vel = random.uniform(8, 14)
            elif camada < 0.7:
                vel = random.uniform(15, 28)
            else:
                vel = random.uniform(30, 46)
            # estrelas ainda menores
            raio = 0.25 + camada * 0.8
            brilho = 170 + int(70 * camada)
            cor = (brilho, brilho, 200 + int(40 * camada))
            self.estrelas.append(Estrela(x, y, vel, raio, cor))
        if self.max_planetas > 0:
            # cria 1 planeta próximo (flyby) e 1 distante, no máximo
            self._criar_planeta(force_flyby=True)
            for _ in range(self.max_planetas - 1):
                self._criar_planeta()
            self._enforce_planet_constraints()

    def atualizar(self, dt):
        for e in self.estrelas:
            e.atualizar(dt)
        for p in self.planetas:
            p.atualizar(dt)
        self._enforce_planet_constraints()

    def desenhar(self, tela):
        for e in self.estrelas:
            e.desenhar(tela)
        flybys = [p for p in self.planetas if getattr(p, 'flyby', False)]
        comuns = [p for p in self.planetas if not getattr(p, 'flyby', False)]
        for p in comuns:
            p.desenhar(tela)
        for p in flybys:
            p.desenhar(tela)

    def _carregar_planetas(self):
        imgs = []
        base_path = get_resource_path(os.path.join('assets', 'kenney', 'PNG', 'Planets'))
        if not os.path.isdir(base_path):
            return imgs
        for nome in os.listdir(base_path):
            if not nome.lower().endswith('.png'):
                continue
            if not nome.lower().startswith('planet'):
                continue
            caminho = os.path.join(base_path, nome)
            try:
                img = pygame.image.load(caminho).convert_alpha()
                imgs.append(img)
            except Exception:
                pass
        return imgs

    def iniciar_super_flyby(self):
        # Promove um planeta em flyby já visível para super flyby com zoom gradual
        candidato = None
        best = -1
        for p in self.planetas:
            if getattr(p, 'flyby', False) and (p.y - p.raio < ALTURA and p.y + p.raio > 0):
                if p.raio > best:
                    best = p.raio
                    candidato = p
        if candidato is not None:
            candidato.super_flyby = True
            alvo = LARGURA * 2.2
            candidato.escala_final = max(0.05, alvo / max(32, candidato.imagem_base.get_width()))
            # centraliza lentamente
            candidato.x = LARGURA / 2
            # reduz velocidade para zoom mais demorado
            candidato.vel = max(10.0, candidato.vel * 0.7)
        else:
            # fallback: cria um flyby normal (não super) para ser promovido futuramente
            self._criar_planeta(force_flyby=True)

    def cancelar_super_flyby(self):
        # Remove status de super flyby dos planetas para impedir reentrada imediata após falha
        for p in self.planetas:
            if getattr(p, 'super_flyby', False):
                p.super_flyby = False

    def tem_super_flyby(self):
        # Verifica se há algum planeta em modo super flyby ativo na tela
        for p in self.planetas:
            if getattr(p, 'super_flyby', False):
                # Considera ativo se estiver visível (y < ALTURA e y + raio > 0)
                # Garante que o planeta já entrou na tela
                if p.y - p.raio < ALTURA and p.y + p.raio > 0:
                    return True
        return False

    def tem_flyby_ativo(self):
        for p in self.planetas:
            if getattr(p, 'flyby', False) or getattr(p, 'super_flyby', False):
                if p.y - p.raio < ALTURA and p.y + p.raio > 0:
                    return True
        return False

    def _enforce_planet_constraints(self):
        # mantém no máximo 1 planeta próximo (flyby/super) e 1 distante
        flybys = [p for p in self.planetas if getattr(p, 'flyby', False) or getattr(p, 'super_flyby', False)]
        comuns = [p for p in self.planetas if not (getattr(p, 'flyby', False) or getattr(p, 'super_flyby', False))]
        # mantém o flyby mais próximo (maior raio)
        if len(flybys) > 1:
            flybys.sort(key=lambda p: p.raio, reverse=True)
            keep = set(flybys[:1])
            self.planetas = [p for p in self.planetas if (p in keep) or (p in comuns)]
        # mantém apenas 1 distante (menor escala)
        if len(comuns) > 1:
            comuns.sort(key=lambda p: p.escala_atual)
            keep_common = set(comuns[:1])
            self.planetas = [p for p in self.planetas if (p in keep_common) or (p in flybys)]

    def _criar_planeta(self, force_flyby=False, super_size=False):
        if not self.planeta_imgs:
            return
        img = random.choice(self.planeta_imgs)
        x = random.uniform(0, LARGURA)
        y = -random.uniform(100, 400) # Começa fora da tela acima
        
        # alguns bem grandes (flyby) e únicos; demais variam por plano
        ja_tem_grande = any(getattr(p, 'flyby', False) or getattr(p, 'super_flyby', False) for p in self.planetas)
        roll = random.random()
        
        flyby = False
        super_flyby = False
        escala_final = None
        escala_inicial = 0.1

        if (force_flyby or super_size or roll < 0.2) and (super_size or not ja_tem_grande):
            # flyby: planeta gigante ocupando boa parte da tela
            flyby = True
            if super_size:
                super_flyby = True
                # Super flyby: ocupa 2.5x a largura (zoom extremo)
                alvo = LARGURA * 2.5
                # Aumentado para durar menos tempo (aprox 30-40s)
                vel = random.uniform(12, 18)
                # Garante que o super flyby seja centralizado
                x = LARGURA / 2
            else:
                alvo = random.uniform(LARGURA * 1.0, LARGURA * 1.45)
                vel = random.uniform(14, 22)
            
            escala_final = max(0.05, alvo / max(32, img.get_width()))
            escala_inicial = escala_final * 0.35
        elif roll < 0.45:
            # plano médio
            alvo = random.uniform(120, 220)
            vel = random.uniform(10, 18)
            flyby = False
        else:
            # distante
            alvo = random.uniform(50, 110)
            vel = random.uniform(6, 12)
            flyby = False
            
        # converte alvo de largura para escala relativa da textura original
        if not flyby:
            escala = max(0.05, alvo / max(32, img.get_width()))
            self.planetas.append(Planeta(x, y, vel, escala, img))
        else:
            self.planetas.append(Planeta(x, y, vel, escala_inicial, img, flyby=True, escala_final=escala_final, super_flyby=super_flyby))
