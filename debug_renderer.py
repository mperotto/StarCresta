
import sys
import os

# Adiciona o diretório atual ao path para conseguir importar src
sys.path.insert(0, os.getcwd())

print("Tentando importar Renderer3D...")
try:
    from src.core.renderer3d import Renderer3D
    print("SUCESSO: Renderer3D importado corretamente!")
    
    # Tenta instanciar para ver se inicializa o OpenGL
    # Precisamos de um contexto pygame
    import pygame
    pygame.init()
    screen = pygame.display.set_mode((800, 600), pygame.OPENGL | pygame.DOUBLEBUF | pygame.HIDDEN)
    
    r = Renderer3D(800, 600)
    if r.initialized:
        print("SUCESSO: Renderer3D inicializado e contexto OpenGL criado!")
    else:
        print(f"FALHA: Renderer3D instanciado mas não inicializado. Erro: {r.last_error}")
        
except Exception as e:
    print("\nERRO CRÍTICO AO IMPORTAR/USAR:")
    import traceback
    traceback.print_exc()

print("\nVerificando dependências diretas:")
try:
    import moderngl
    print(f"ModernGL: {moderngl.__version__}")
except ImportError as e:
    print(f"ModernGL FALHOU: {e}")

try:
    import glm
    print(f"GLM: {dir(glm)[:5]}...") # Mostra que leu algo
except ImportError as e:
    print(f"GLM FALHOU: {e}")
