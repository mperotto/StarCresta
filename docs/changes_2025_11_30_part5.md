# Mudanças - 30/11/2025 (Parte 5)

## Correção Final da Transparência (Magenta Strategy)

- **Problema**: A tentativa anterior resultou em janelas pretas (opacas) ou com artefatos verdes.
- **Solução**:
  - Adotada a estratégia de "Substituição por Magenta".
  - O código agora identifica os pixels verdes (com tolerância de 90) e os substitui por **Magenta Puro (255, 0, 255)** usando `pygame.transform.threshold`.
  - Em seguida, define o Magenta como `colorkey` da superfície.
  - Finalmente, converte para `convert_alpha()`.
  - Isso garante que tanto os pixels verdes originais quanto os artefatos de compressão próximos sejam transformados em transparência perfeita, permitindo ver o cenário 3D ao fundo.

## Arquivos Modificados
- `src/core/planet_stage.py`: Atualizada a lógica de processamento da imagem do cockpit.
