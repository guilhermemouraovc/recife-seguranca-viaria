"""Grafo de consulta da ontologia do domínio (ver docs/03-ontologia.md).

Entidades e relações abaixo são uma transcrição estruturada do doc — mantidas
manualmente em código (não parseadas do markdown) porque são ~9 nós / ~10
arestas, estáveis, e um parser de prosa livre seria menos confiável que
copiar à mão. Se `03-ontologia.md` mudar, atualize NODES/EDGES aqui junto.

Uso por um agente:
    from scripts.ontologia_grafo import query, path, GLOBAL_CAVEATS
    query("sinistro")          # nó + arestas de entrada/saída + ressalvas globais
    path("samu", "equipamento") # caminho (se existir) entre duas entidades

CLI:
    python scripts/ontologia_grafo.py sinistro
    python scripts/ontologia_grafo.py --path samu equipamento
    python scripts/ontologia_grafo.py --export grafo.json
"""

import argparse
import json
from collections import defaultdict, deque

NODES = {
    "sinistro": "Sinistro/chamado de trânsito (CTTU) — protocolo, data, hora, endereço, natureza, tipo.",
    "vitima": "Vítima — agregada por sinistro (contadores), não é linha própria no CSV da CTTU.",
    "veiculo": "Veículo envolvido — inferido por colunas de contagem por tipo, sem registro individual.",
    "local": "Via/bairro/endereço/cruzamento — texto livre no dataset de sinistros, sem lat/long.",
    "equipamento": "Equipamento de fiscalização (radar, lombada, fotossensor) — tem lat/long, velocidade regulamentada, VMD.",
    "registro_velocidade": "Contagem de veículos por faixa de velocidade, por equipamento e janela de tempo.",
    "infracao": "Infração/multa — data/hora, tipo, base legal, local em texto (não geolocalizada diretamente).",
    "semaforo": "Semáforo — infraestrutura de via com lat/long, sem relação codificada com sinistros.",
    "samu": "Atendimento SAMU — chamado de saúde da RMR, com sexo/idade/bairro, tipo/subtipo.",
    "psvr_indicador": "Indicador/meta do PSVR — fonte qualitativa (PDF), não tabular.",
}

# (origem, destino, relação, ressalva)
EDGES = [
    ("sinistro", "local", "ocorre_em", "endereço em texto livre — sem lat/long."),
    ("sinistro", "veiculo", "envolve", "via colunas de contagem por tipo, não registros individuais."),
    ("sinistro", "vitima", "pode_ter", "contagem agregada, não fatos individuais por vítima."),
    ("local", "equipamento", "pode_ter", "relação espacial via lat/long — exige geocodificar o endereço do sinistro."),
    ("local", "semaforo", "pode_ter", "relação só espacial (proximidade), sem chave codificada."),
    ("equipamento", "registro_velocidade", "gera", "uma linha por faixa de velocidade/tempo."),
    ("equipamento", "infracao", "pode_gerar", "só quando a infração é automática (excesso de velocidade)."),
    ("infracao", "equipamento", "pode_referenciar", "campo agenteequipamento — nem toda infração vem de equipamento fixo."),
    ("samu", "sinistro", "pode_corresponder", "correspondência PROBABILÍSTICA por data+hora+bairro — nunca chave exata, tratar como hipótese a validar."),
    ("psvr_indicador", "sinistro", "descreve_agregado", "fonte qualitativa (PDF) — não reconcilia automaticamente com CSVs (ver docs/06)."),
]

GLOBAL_CAVEATS = [
    "Não há chave única compartilhada entre nenhum par de datasets.",
    "Não há geolocalização no dataset de sinistros — qualquer join espacial exige geocodificação prévia e validação manual de amostra.",
    "Números de relatórios institucionais (PSVR, Relatórios Anuais) não reconciliam automaticamente com os datasets abertos — processos estatísticos diferentes.",
]

_adj = defaultdict(list)
_rev = defaultdict(list)
for src, dst, rel, note in EDGES:
    _adj[src].append((dst, rel, note))
    _rev[dst].append((src, rel, note))


def query(entity):
    if entity not in NODES:
        raise KeyError(f"entidade desconhecida: {entity!r}. Nós disponíveis: {sorted(NODES)}")
    return {
        "entidade": entity,
        "descricao": NODES[entity],
        "saidas": [{"para": d, "relacao": r, "ressalva": n} for d, r, n in _adj[entity]],
        "entradas": [{"de": s, "relacao": r, "ressalva": n} for s, r, n in _rev[entity]],
        "ressalvas_globais": GLOBAL_CAVEATS,
    }


def path(origem, destino):
    """BFS não-direcionado — só indica se existe cadeia de relações no grafo, não um join válido."""
    if origem not in NODES or destino not in NODES:
        raise KeyError("origem/destino precisam ser nós conhecidos")
    if origem == destino:
        return [origem]
    undirected = defaultdict(set)
    for src, dst, _, _ in EDGES:
        undirected[src].add(dst)
        undirected[dst].add(src)
    visited = {origem}
    queue = deque([[origem]])
    while queue:
        p = queue.popleft()
        for nxt in undirected[p[-1]]:
            if nxt == destino:
                return p + [nxt]
            if nxt not in visited:
                visited.add(nxt)
                queue.append(p + [nxt])
    return None


def export_json(path_out):
    data = {
        "nodes": [{"id": n, "descricao": d} for n, d in NODES.items()],
        "edges": [{"de": s, "para": d, "relacao": r, "ressalva": n} for s, d, r, n in EDGES],
        "ressalvas_globais": GLOBAL_CAVEATS,
    }
    with open(path_out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path_out


def _demo():
    assert "sinistro" in NODES
    q = query("sinistro")
    assert any(e["para"] == "local" for e in q["saidas"])
    assert q["ressalvas_globais"] == GLOBAL_CAVEATS
    p = path("samu", "equipamento")
    assert p is not None and p[0] == "samu" and p[-1] == "equipamento"
    assert path("sinistro", "sinistro") == ["sinistro"]
    try:
        query("entidade_inexistente")
        raise AssertionError("deveria ter levantado KeyError")
    except KeyError:
        pass
    print("ok:", p)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("entity", nargs="?", help="nome da entidade a consultar")
    parser.add_argument("--path", nargs=2, metavar=("ORIGEM", "DESTINO"))
    parser.add_argument("--export", metavar="ARQUIVO_JSON")
    parser.add_argument("--demo", action="store_true", help="roda o self-check")
    args = parser.parse_args()

    if args.demo:
        _demo()
    elif args.export:
        print("exportado em", export_json(args.export))
    elif args.path:
        result = path(*args.path)
        print(json.dumps(result, ensure_ascii=False, indent=2) if result else "sem caminho no grafo")
    elif args.entity:
        print(json.dumps(query(args.entity), ensure_ascii=False, indent=2))
    else:
        parser.print_help()
