# Mudanças - 30/11/2025 (Parte 4)

## Correção da Transparência (Chroma Key)

- **Problema**: A janela verde persistia, indicando falha na aplicação da transparência.
- **Solução**:
  - Implementada uma amostragem dinâmica da cor de fundo (`chroma_color`) pegando um pixel na posição `(width // 2, height * 0.4)`, que geralmente corresponde à janela central.
  - Criada uma nova superfície `SRCALPHA` onde a imagem original (com `set_colorkey` aplicado) é desenhada (`blit`). Isso força a conversão dos pixels da cor chave para pixels totalmente transparentes (alpha 0), garantindo que o redimensionamento subsequente funcione corretamente sem preservar o verde.

## Arquivos Modificados
- `src/core/planet_stage.py`: Refinada a lógica de carregamento da imagem do cockpit no método `__init__`.
