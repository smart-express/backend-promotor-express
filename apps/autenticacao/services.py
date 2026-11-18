from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.contrib.auth.hashers import check_password
from django.db import connection


def serializar_valor(valor):
    if isinstance(valor, (UUID, datetime, date)):
        return str(valor)
    if isinstance(valor, Decimal):
        return float(valor)
    return valor


def _buscar_admin_com_usuario(login_informado: str) -> dict | None:
    termo = login_informado.strip()
    sql = """
        SELECT
            a.id AS admin_uuid,
            a.nome_completo,
            a.cargo,
            a.telefone,
            a.ativo AS admin_ativo,
            a.criado_em,
            a.user_id,
            u.username,
            u.email,
            u.password,
            u.is_active AS user_ativo
        FROM administradores a
        INNER JOIN auth_user u ON a.user_id = u.id
        WHERE LOWER(u.username) = LOWER(%s)
           OR LOWER(u.email) = LOWER(%s)
           OR LOWER(a.nome_completo) = LOWER(%s)
        LIMIT 1
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, [termo, termo, termo])
        row = cursor.fetchone()
        if not row:
            return None
        colunas = [col[0] for col in cursor.description]
        return dict(zip(colunas, row))


def _listar_todos_cadastros_promotor() -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM cadastros ORDER BY nome ASC NULLS LAST")
        colunas = [col[0] for col in cursor.description]
        linhas = cursor.fetchall()

    return [
        {
            "promotor": {
                col: serializar_valor(val) for col, val in zip(colunas, linha)
            }
        }
        for linha in linhas
    ]


def autenticar_admin_e_carregar_cadastros(login_informado: str, senha_informada: str) -> dict | None:
    registro = _buscar_admin_com_usuario(login_informado)
    if not registro:
        return None

    if not registro.get("admin_ativo") or not registro.get("user_ativo"):
        return None

    senha_hash = registro.get("password") or ""
    senha_valida = check_password(senha_informada, senha_hash) or (senha_hash == senha_informada)
    if not senha_valida:
        return None

    administrador = {
        "id": serializar_valor(registro["admin_uuid"]),
        "user_id": registro["user_id"],
        "username": registro["username"],
        "email": registro["email"],
        "nome_completo": registro["nome_completo"],
        "cargo": registro["cargo"],
        "telefone": registro["telefone"],
        "ativo": registro["admin_ativo"],
        "criado_em": serializar_valor(registro["criado_em"]),
    }

    cadastros = _listar_todos_cadastros_promotor()

    return {
        "administrador": administrador,
        "total_cadastros": len(cadastros),
        "cadastros": cadastros,
    }
