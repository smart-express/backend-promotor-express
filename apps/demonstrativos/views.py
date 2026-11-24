import math, os
from django.db import connection
from django.http import FileResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.autenticacao.security import AdminKeyAuthentication, PromotorJWTAuthentication
from apps.autenticacao.services import buscar_demonstrativo_por_cpf, buscar_promotor_por_cpf, limpar_cpf, serializar_valor
from .serializers import (
    ErroDemonstrativoSerializer,
    ImportarLoteResponseSerializer,
    ImportarLoteSerializer,
    LimparDemonstrativosRequestSerializer,
    LimparDemonstrativosResponseSerializer,
    LoteDemonstrativosListResponseSerializer,
    MeuDemonstrativoResponseSerializer,
)
from .services import limpar_todos_demonstrativos, processar_importacao_lote


class MeuDemonstrativoView(APIView):
    authentication_classes = [PromotorJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Demonstrativos (Promotor)"], summary="Dados do promotor e metadados do demonstrativo", responses={200: MeuDemonstrativoResponseSerializer, 401: ErroDemonstrativoSerializer, 404: ErroDemonstrativoSerializer})
    def get(self, request):
        cpf_l = request.user.get("cpf", "")
        promotor = buscar_promotor_por_cpf(cpf_l)
        if not promotor:
            return Response({"erro": "Cadastro não encontrado."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"promotor": promotor, "demonstrativo": buscar_demonstrativo_por_cpf(cpf_l, f"{request.scheme}://{request.get_host()}")})


class MeuDemonstrativoPdfView(APIView):
    authentication_classes = [PromotorJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Demonstrativos (Promotor)"], summary="Abre ou baixa o PDF do demonstrativo", parameters=[OpenApiParameter(name="download", type=bool, required=False), OpenApiParameter(name="token", type=str, required=False)], responses={(200, "application/pdf"): OpenApiTypes.BINARY, 401: ErroDemonstrativoSerializer, 404: ErroDemonstrativoSerializer})
    def get(self, request):
        cpf_l = request.user.get("cpf", "")
        with connection.cursor() as cursor:
            cursor.execute("SELECT nome_arquivo, caminho_arquivo FROM demonstrativos WHERE cpf_limpo = %s ORDER BY criado_em DESC LIMIT 1", [cpf_l])
            row = cursor.fetchone()
        if not row or not row[1] or not os.path.exists(row[1]):
            return Response({"erro": "Nenhum demonstrativo disponível."}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(open(row[1], "rb"), content_type="application/pdf", as_attachment=str(request.query_params.get("download", "")).lower() == "true", filename=row[0])


class LoteDemonstrativosListView(APIView):
    authentication_classes = [AdminKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Gestão Quinzenal (Admin)"], summary="Lista paginada dos demonstrativos ativos", parameters=[OpenApiParameter(name="page", type=int, default=1), OpenApiParameter(name="page_size", type=int, default=50), OpenApiParameter(name="busca", type=str, required=False)], responses={200: LoteDemonstrativosListResponseSerializer, 401: ErroDemonstrativoSerializer})
    def get(self, request):
        page = max(1, int(request.query_params.get("page", 1) or 1))
        page_size = min(500, max(1, int(request.query_params.get("page_size", 50) or 50)))
        busca = (request.query_params.get("busca") or "").strip()
        where = "WHERE nome_promotor ILIKE %s OR cpf_limpo LIKE %s" if busca else ""
        params = [f"%{busca}%", f"%{busca}%"] if busca else []
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM demonstrativos {where}", params)
            total = cursor.fetchone()[0]
            cursor.execute(f"SELECT id, cadastro_id, cpf_limpo, nome_promotor, periodo, nome_arquivo, tamanho_bytes, criado_em FROM demonstrativos {where} ORDER BY nome_promotor ASC LIMIT %s OFFSET %s", [*params, page_size, (page - 1) * page_size])
            cols = [c[0] for c in cursor.description]
            rows = cursor.fetchall()
        return Response({"total": total, "pagina_atual": page, "total_paginas": max(1, math.ceil(total / page_size)), "resultados": [{c: serializar_valor(v) for c, v in zip(cols, r)} for r in rows]})


class ImportarLoteDemonstrativosView(APIView):
    authentication_classes = [AdminKeyAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(tags=["Gestão Quinzenal (Admin)"], summary="Importa lote de PDFs (.zip ou múltiplos .pdf)", request={"multipart/form-data": ImportarLoteSerializer}, responses={200: ImportarLoteResponseSerializer, 400: ErroDemonstrativoSerializer, 401: ErroDemonstrativoSerializer})
    def post(self, request):
        arq_zip = request.FILES.get("arquivo_zip")
        arqs_pdf = request.FILES.getlist("arquivos_pdf")
        if not arq_zip and not arqs_pdf:
            return Response({"erro": "Envie 'arquivo_zip' ou 'arquivos_pdf'."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            return Response(processar_importacao_lote(arq_zip, arqs_pdf))
        except Exception as exc:
            return Response({"erro": f"{type(exc).__name__}: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LimparDemonstrativosView(APIView):
    authentication_classes = [AdminKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Gestão Quinzenal (Admin)"],
        summary="Exclui PDFs e registros (geral, por período ou por CPFs)",
        parameters=[OpenApiParameter(name="periodo", type=str, required=False)],
        request=LimparDemonstrativosRequestSerializer,
        responses={200: LimparDemonstrativosResponseSerializer, 401: ErroDemonstrativoSerializer},
        examples=[
            OpenApiExample("Por período", value={"periodo": "2026-11-1Q"}, request_only=True),
            OpenApiExample("Por CPFs", value={"cpfs": ["123.456.789-00"]}, request_only=True),
            OpenApiExample("Limpar tudo", value={}, request_only=True),
            OpenApiExample("Retorno", value={"mensagem": "Limpeza concluída.", "total_removidos": 1229}, response_only=True, status_codes=["200"]),
        ],
    )
    def delete(self, request):
        dados = request.data if isinstance(request.data, dict) else {}
        cpfs_limpos = [limpar_cpf(c) for c in (dados.get("cpfs") or []) if len(limpar_cpf(c)) == 11]
        if cpfs_limpos:
            placeholders = ", ".join(["%s"] * len(cpfs_limpos))
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT caminho_arquivo FROM demonstrativos WHERE cpf_limpo IN ({placeholders})", cpfs_limpos)
                caminhos = [r[0] for r in cursor.fetchall() if r[0]]
                cursor.execute(f"DELETE FROM demonstrativos WHERE cpf_limpo IN ({placeholders})", cpfs_limpos)
                removidos = cursor.rowcount
            for caminho in caminhos:
                if os.path.exists(caminho):
                    try:
                        os.remove(caminho)
                    except OSError:
                        pass
            return Response({"mensagem": "Limpeza concluída.", "total_removidos": removidos})
        periodo = (dados.get("periodo") or request.query_params.get("periodo") or "").strip() or None
        return Response({"mensagem": "Limpeza concluída.", "total_removidos": limpar_todos_demonstrativos(periodo)})
