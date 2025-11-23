from src.core.game import Jogo

import traceback

if __name__ == "__main__":
    try:
        Jogo().executar()
    except Exception:
        with open("error_log.txt", "w") as f:
            traceback.print_exc(file=f)
        raise
