import re, unicodedata
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from uuid import UUID
from django.db import connection

SENHA_PADRAO_PROMOTOR = "express1234"

def limpar_cpf(cpf: str) -> str:
    digitos = re.sub(r"\D", "", cpf or "")
    return digitos.zfill(11) if digitos else ""

def normalizar_texto(texto: str) -> str:
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn")
    return " ".join(sem_acento.upper().split())

def serializar_valor(valor):
    if isinstance(valor, (UUID, datetime, date)):
        return str(valor)
    if isinstance(valor, Decimal):
        return float(valor)
    return valor

@lru_cache(maxsize=1)
def obter_colunas_cadastros() -> dict:
    with connection.cursor() as cursor:
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='cadastros' ORDER BY ordinal_position")
        cols = [r[0] for r in cursor.fetchall()]
    return {
        "id": "id" if "id" in cols else cols[0],
        "nome": "nome" if "nome" in cols else next((c for c in cols if "nome" in c.lower()), "nome"),
        "cpf": "cpf" if "cpf" in cols else next((c for c in cols if "cpf" in c.lower()), "cpf"),
    }

def promotor_esta_ativo(promotor: dict) -> bool:
    if not promotor:
        return False
    mapa = {k.lower(): k for k in promotor.keys()}
    col_in = next((mapa[c] for c in ("inativo", "desligado") if c in mapa), None)
    if col_in:
        v_in = promotor.get(col_in)
        if isinstance(v_in, bool):
            return not v_in
        if isinstance(v_in, (int, float)):
            return v_in == 0
        if isinstance(v_in, str) and normalizar_texto(v_in) in {"TRUE", "T", "1", "S", "SIM", "Y", "YES"}:
            return False
    candidatos = ("ativo", "status", "situacao", "situacao_cadastral", "status_promotor", "estado")
    col = next((mapa[c] for c in candidatos if c in mapa), None) or next((o for l, o in mapa.items() if any(p in l for p in ("ativo", "status", "situacao"))), None)
    if not col:
        return True
    val = promotor.get(col)
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val != 0
    if isinstance(val, str):
        v = normalizar_texto(val)
        if not v or v in {"FALSE", "F", "0", "N", "NAO"} or any(v.startswith(p) for p in ("INATIV", "DESATIV", "DESLIG", "BLOQ", "DEMIT", "CANCEL", "SUSP", "AFAST")):
            return False
    return True

def buscar_promotor_por_cpf(cpf_limpo: str) -> dict | None:
    col_cpf = obter_colunas_cadastros()["cpf"]
    sql = f"SELECT * FROM cadastros WHERE LPAD(regexp_replace(COALESCE(CAST({col_cpf} AS TEXT), ''), '[^0-9]', '', 'g'), 11, '0') = %s LIMIT 1"
    with connection.cursor() as cursor:
        cursor.execute(sql, [cpf_limpo])
        row = cursor.fetchone()
        if not row:
            return None
        return {col[0]: serializar_valor(val) for col, val in zip(cursor.description, row)}

def buscar_demonstrativo_por_cpf(cpf_limpo: str, base_url: str) -> dict | None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, nome_arquivo, periodo, tamanho_bytes, criado_em FROM demonstrativos WHERE cpf_limpo = %s ORDER BY criado_em DESC LIMIT 1", [cpf_limpo])
        row = cursor.fetchone()
        if not row:
            return None
    url_pdf = f"{base_url.rstrip('/')}/api/demonstrativos/meu/pdf/"
    return {
        "id": str(row[0]),
        "nome_arquivo": row[1],
        "periodo": row[2],
        "tamanho_bytes": row[3],
        "criado_em": serializar_valor(row[4]),
        "url_visualizar": url_pdf,
        "url_download": f"{url_pdf}?download=true",
    }
