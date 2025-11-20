# StarCresta Overhaul

Um jogo de tiro espacial vertical (shmup) desenvolvido em Python com Pygame.

## Funcionalidades

- **Combate Espacial**: Enfrente ondas de inimigos, asteroides e OVNIs.
- **Boss Battle**: Uma batalha épica contra um chefe com múltiplos padrões de ataque e modo "Enrage".
- **Power-ups**:
  - **V-Shot**: Aumenta o nível da arma e espalha os tiros.
  - **Shield**: Protege contra danos por tempo acumulativo.
  - **Health**: Recupera vida ou dá bônus de pontuação.
- **Sistema de Pontuação**: High score persistente.
- **Efeitos Visuais**: Partículas, explosões, rastro de motor e feedback visual de dano.

## Como Executar

1.  **Pré-requisitos**: Python 3.10+ instalado.
2.  **Instalar Dependências**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Rodar o Jogo**:
    ```bash
    python main.py
    ```

## Controles

- **Setas**: Mover a nave.
- **Espaço**: Atirar.
- **Z**: Super Tiro (quando carregado).
- **B**: Spawnar Boss (Debug).

## Estrutura do Projeto

- `main.py`: Ponto de entrada.
- `src/`: Código fonte organizado em módulos (core, sprites, ui).
- `assets/`: Imagens e sprites.
- `sound/`: Efeitos sonoros e música.

## Créditos

- Desenvolvido como projeto de exemplo de POO e Pygame.
- Assets sonoros e gráficos de fontes variadas (OpenGameArt, Kenney).
