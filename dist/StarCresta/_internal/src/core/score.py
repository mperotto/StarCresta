import json
import os

class ScoreManager:
    def __init__(self, arquivo='highscore.json'):
        self.arquivo = arquivo
        self.high_score = self.carregar()

    def carregar(self):
        if not os.path.exists(self.arquivo):
            return 0
        try:
            with open(self.arquivo, 'r') as f:
                data = json.load(f)
                return data.get('high_score', 0)
        except Exception:
            return 0

    def salvar(self, score):
        if score > self.high_score:
            self.high_score = score
            try:
                with open(self.arquivo, 'w') as f:
                    json.dump({'high_score': self.high_score}, f)
            except Exception:
                pass
        return self.high_score

    def get_high_score(self):
        return self.high_score
