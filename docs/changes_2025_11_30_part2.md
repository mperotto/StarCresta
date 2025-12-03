# Mudanças - 30/11/2025 (Parte 2)

## Debug e Visual do Cockpit

- **Atalho de Debug 'P'**:
  - Modificado `src/core/event_handler.py` para que, ao pressionar 'P', o jogador receba automaticamente um escudo (10s) antes de entrar no estágio do planeta. Isso evita a morte imediata por falta de escudo na reentrada.

- **Cockpit com Chroma Key**:
  - Atualizado `src/core/planet_stage.py` para carregar preferencialmente a imagem `assets/cockpit_center_chroma.png`.
  - Implementada lógica de chroma key (verde `0, 255, 0` como transparente) e conversão para canal alpha, garantindo que o redimensionamento (`smoothscale`) não crie halos verdes indesejados.

## Arquivos Modificados
- `src/core/event_handler.py`: Adicionado `jogo.player_shield_timer = 10.0` no handler da tecla 'P'.
- `src/core/planet_stage.py`: Adicionada lógica de carregamento com `set_colorkey` e `convert_alpha` para a nova imagem do cockpit.
