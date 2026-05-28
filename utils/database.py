"""
utils/database.py
Gerencia todos os dados do bot em arquivos JSON.
Cada guild (servidor) tem seus próprios dados isolados.
"""
import json
import os
from pathlib import Path

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# ── Estrutura padrão de dados de um servidor ──────────────────────────────────
DEFAULT_GUILD_DATA = {
    "config": {
        "moeda_nome": "Moedas",
        "moeda_emoji": "🪙",
        "taxa_mediador": 10,          # % que o mediador recebe
        "taxa_org": 10,               # % que a org retém
        "prefixo": "!",
        "cargo_mediador": None,       # ID do cargo mediador
        "cargo_admin": None,          # ID do cargo admin
        "canal_logs": None,           # ID do canal de logs
        "canal_fila_mediador": None,  # ID do canal fila-mediador
        "canal_ranking": None,
        "canal_blacklist": None,
        "pix_org": "",                # Chave PIX da org
    },
    "filas": {},        # fila_id -> dados da fila configurada
    "jogadores": {},    # user_id -> perfil do jogador
    "mediadores": {},   # user_id -> dados do mediador
    "partidas": {},     # partida_id -> dados da partida ativa
    "historico": [],    # lista de partidas finalizadas
    "loja": {},         # item_id -> item da loja
    "blacklist": [],    # lista de user_ids banidos
    "ranking": {
        "diario": {},
        "semanal": {},
        "mensal": {},
        "geral": {},
    }
}

DEFAULT_JOGADOR = {
    "vitorias": 0,
    "derrotas": 0,
    "moedas": 0,
    "historico": [],
    "inventario": [],
    "pix": "",
    "nick_jogo": "",
    "receita_total": 0.0,   # só para mediadores
    "partidas_mediadas": 0, # só para mediadores
}


def _guild_file(guild_id: int) -> Path:
    return DATA_DIR / f"{guild_id}.json"


def load(guild_id: int) -> dict:
    """Carrega os dados de um servidor."""
    path = _guild_file(guild_id)
    if not path.exists():
        save(guild_id, DEFAULT_GUILD_DATA.copy())
        return DEFAULT_GUILD_DATA.copy()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Garante que chaves novas existam (atualização sem apagar dados)
    for key, value in DEFAULT_GUILD_DATA.items():
        if key not in data:
            data[key] = value
    return data


def save(guild_id: int, data: dict):
    """Salva os dados de um servidor."""
    path = _guild_file(guild_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_jogador(guild_id: int, user_id: int) -> dict:
    """Retorna o perfil de um jogador, criando se não existir."""
    data = load(guild_id)
    uid = str(user_id)
    if uid not in data["jogadores"]:
        data["jogadores"][uid] = DEFAULT_JOGADOR.copy()
        save(guild_id, data)
    return data["jogadores"][uid]


def save_jogador(guild_id: int, user_id: int, jogador: dict):
    """Salva o perfil de um jogador."""
    data = load(guild_id)
    data["jogadores"][str(user_id)] = jogador
    save(guild_id, data)


def get_config(guild_id: int) -> dict:
    """Retorna as configurações do servidor."""
    return load(guild_id)["config"]


def save_config(guild_id: int, config: dict):
    """Salva as configurações do servidor."""
    data = load(guild_id)
    data["config"] = config
    save(guild_id, data)
