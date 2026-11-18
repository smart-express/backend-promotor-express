import math
from django.db import connection
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.autenticacao.services import serializar_valor


class CadastrosPaginadosView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Cadastros"],
        summary="Lista paginada da tabela cadastros (todas as colunas)",
        parameters=[
            OpenApiParameter(name="page", type=int, default=1, description="Número da página"),
            OpenApiParameter(name="page_size", type=int, default=50, description="Itens por página (máx. 500)"),
            OpenApiParameter(name="busca", type=str, required=False, description="Filtro opcional por nome"),
        ],
    )
    def get(self, request):
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except ValueError:
            page = 1

        try:
            page_size = min(500, max(1, int(request.query_params.get("page_size", 50))))
        except ValueError:
            page_size = 50

        busca = (request.query_params.get("busca") or "").strip()
        offset = (page - 1) * page_size

        where_sql = ""
        params = []
        if busca:
            where_sql = "WHERE nome ILIKE %s"
            params.append(f"%{busca}%")

        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM cadastros {where_sql}", params)
            total = cursor.fetchone()[0]

            cursor.execute(
                f"SELECT * FROM cadastros {where_sql} ORDER BY nome ASC NULLS LAST LIMIT %s OFFSET %s",
                [*params, page_size, offset],
            )
            colunas = [col[0] for col in cursor.description]
            linhas = cursor.fetchall()

        total_paginas = max(1, math.ceil(total / page_size))
        resultados = [
            {"promotor": {col: serializar_valor(val) for col, val in zip(colunas, linha)}}
            for linha in linhas
        ]

        base_url = request.build_absolute_uri(request.path)
        query_extra = f"&busca={busca}" if busca else ""
        proxima = f"{base_url}?page={page + 1}&page_size={page_size}{query_extra}" if page < total_paginas else None
        anterior = f"{base_url}?page={page - 1}&page_size={page_size}{query_extra}" if page > 1 else None

        return Response(
            {
                "total": total,
                "pagina_atual": page,
                "total_paginas": total_paginas,
                "proxima": proxima,
                "anterior": anterior,
                "resultados": resultados,
            }
        )
