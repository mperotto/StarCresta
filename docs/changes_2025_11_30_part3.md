# Mudanças - 30/11/2025 (Parte 3)

## Ajustes no Cockpit e Chroma Key

- **Cockpit em Tela Cheia**:
  - A imagem do cockpit (`cockpit_center_chroma.png`) agora é redimensionada para ocupar toda a tela (`LARGURA`, `ALTURA`) em vez de ser um overlay centralizado. Isso atende ao pedido de "ampliar para fullscreen".

- **Remoção de Máscaras Procedurais**:
  - Removido o método `_blit_viewfinders` e a lógica de máscaras poligonais antigas.
  - O jogo agora confia inteiramente na transparência (chroma key) da imagem do cockpit para mostrar o cenário 3D através das janelas.
  - A cena 3D é desenhada diretamente na tela (`screen.blit(scene, (0, 0))`) e o cockpit é desenhado por cima.

## Arquivos Modificados
- `src/core/planet_stage.py`:
  - Removido `_blit_viewfinders`.
  - Atualizado `draw` para blitar a cena diretamente.
  - Atualizado `draw_cockpit` para escalar a imagem para fullscreen.
