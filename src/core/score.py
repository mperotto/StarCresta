import json
import os
from typing import List, Dict

class ScoreManager:
    def __init__(self, arquivo='highscore.json'):
        self.arquivo = arquivo
        self.top_scores: List[Dict] = []
        self.carregar()

    def carregar(self):
        if not os.path.exists(self.arquivo):
            self.top_scores = []
            return
        try:
            with open(self.arquivo, 'r') as f:
                data = json.load(f)
            if isinstance(data, dict) and 'scores' in data:
                self.top_scores = data.get('scores', [])
            elif isinstance(data, dict) and 'high_score' in data:
                hs = data.get('high_score', 0)
                self.top_scores = [{'name': '---', 'score': hs}] if hs > 0 else []
            elif isinstance(data, list):
                self.top_scores = data
            else:
                self.top_scores = []
        except Exception:
            self.top_scores = []
        self._ordenar()

    def _ordenar(self):
        self.top_scores = sorted(self.top_scores, key=lambda e: e.get('score', 0), reverse=True)[:10]

    def get_high_score(self):
        return self.top_scores[0]['score'] if self.top_scores else 0

    def get_high_holder(self):
        if not self.top_scores:
            return ("---", 0)
        top = self.top_scores[0]
        return (top.get('name', '---'), top.get('score', 0))

    def get_top10(self):
        return self.top_scores

    def qualifica(self, score: int):
        if len(self.top_scores) < 10:
            return True
        return score > self.top_scores[-1].get('score', 0)

    def registrar(self, nome: str, score: int):
        nome = (nome or '').upper()[:3].ljust(3, '_')
        self.top_scores.append({'name': nome, 'score': score})
        self._ordenar()
        try:
            with open(self.arquivo, 'w') as f:
                json.dump({'scores': self.top_scores}, f)
        except Exception:
            pass
        return self.top_scores
