"""Valida um arquivo de trechos de risco contra o contrato (docs/09-contrato-trechos-e-telemetria.md).

Uso:
    python scripts/validar_trechos.py data/contrato/trechos_exemplo.json

Não precisa de nenhuma biblioteca externa.
"""
import json
import re
import sys
from datetime import datetime

VERSOES_SUPORTADAS = {1}
RISCOS = {"baixo", "medio", "alto"}
MAX_TRECHOS = 200
# Retângulo folgado em volta da Região Metropolitana do Recife
LAT_MIN, LAT_MAX = -8.30, -7.80
LON_MIN, LON_MAX = -35.10, -34.80
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def faixa_do_score(score: float) -> str:
    if score >= 0.70:
        return "alto"
    if score >= 0.40:
        return "medio"
    return "baixo"


def validar(dados: dict) -> tuple[list[str], list[str]]:
    erros: list[str] = []
    avisos: list[str] = []

    if dados.get("versao") not in VERSOES_SUPORTADAS:
        erros.append(f"versao deve ser uma de {sorted(VERSOES_SUPORTADAS)}")

    gerado = dados.get("gerado_em")
    try:
        dt = datetime.fromisoformat(str(gerado))
        if dt.tzinfo is None:
            erros.append("gerado_em precisa ter fuso horário (ex.: -03:00)")
    except ValueError:
        erros.append("gerado_em não está no formato ISO 8601")

    if not isinstance(dados.get("fonte"), str) or not dados["fonte"]:
        erros.append("fonte é obrigatória")

    trechos = dados.get("trechos")
    if not isinstance(trechos, list):
        return erros + ["trechos deve ser uma lista"], avisos
    if len(trechos) > MAX_TRECHOS:
        erros.append(f"{len(trechos)} trechos: o máximo é {MAX_TRECHOS}")

    ids = set()
    for i, t in enumerate(trechos):
        p = f"trechos[{i}] ({t.get('id', '?')})"
        tid = t.get("id")
        if not isinstance(tid, str) or not ID_RE.match(tid):
            erros.append(f"{p}: id deve ter só minúsculas, números e hífen")
        elif tid in ids:
            erros.append(f"{p}: id repetido")
        ids.add(tid)

        nome = t.get("nome")
        if not isinstance(nome, str) or not 0 < len(nome) <= 60:
            erros.append(f"{p}: nome obrigatório, até 60 caracteres")

        lat, lon = t.get("lat"), t.get("lon")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            erros.append(f"{p}: lat e lon devem ser números")
        elif not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
            erros.append(f"{p}: coordenada fora da região do Recife (lat/lon trocados?)")

        raio = t.get("raio_m")
        if not isinstance(raio, int) or not 20 <= raio <= 500:
            erros.append(f"{p}: raio_m deve ser inteiro entre 20 e 500")

        risco = t.get("risco")
        if risco not in RISCOS:
            erros.append(f"{p}: risco deve ser baixo, medio ou alto")

        score = t.get("score")
        if not isinstance(score, (int, float)) or not 0 <= score <= 1:
            erros.append(f"{p}: score deve estar entre 0 e 1")
        elif risco in RISCOS and faixa_do_score(score) != risco:
            avisos.append(f"{p}: score {score} indica '{faixa_do_score(score)}', mas risco é '{risco}'")

        horas = t.get("horas")
        if not isinstance(horas, list) or not all(isinstance(h, int) and 0 <= h <= 23 for h in horas):
            erros.append(f"{p}: horas deve ser lista de inteiros de 0 a 23 (vazia = dia todo)")
        elif len(set(horas)) != len(horas):
            avisos.append(f"{p}: horas repetidas")

        vel = t.get("vel_segura")
        if not isinstance(vel, int) or not 10 <= vel <= 80:
            erros.append(f"{p}: vel_segura deve ser inteiro entre 10 e 80 km/h")

        extras = set(t) - {"id", "nome", "lat", "lon", "raio_m", "risco", "score", "horas", "vel_segura"}
        if extras:
            avisos.append(f"{p}: campos fora do contrato serão ignorados: {sorted(extras)}")

    return erros, avisos


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    caminho = sys.argv[1]
    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERRO ao ler {caminho}: {e}")
        return 1

    erros, avisos = validar(dados)
    for a in avisos:
        print(f"aviso: {a}")
    for e in erros:
        print(f"ERRO: {e}")
    if erros:
        print(f"\n{caminho}: inválido ({len(erros)} erro(s))")
        return 1
    tamanho = len(json.dumps(dados, separators=(",", ":")).encode())
    print(f"{caminho}: válido, {len(dados['trechos'])} trecho(s), {tamanho} bytes compactado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
