import math
from django.db import connection, transaction
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .security import AdminKeyAuthentication, gerar_token_promotor
from .serializers import (
    ErroResponseSerializer,
    ExcluirCadastrosRequestSerializer,
    ExcluirCadastrosResponseSerializer,
    ImportarCadastrosRequestSerializer,
    ImportarCadastrosResponseSerializer,
    ListaCadastrosResponseSerializer,
    LoginPromotorRequestSerializer,
    LoginPromotorResponseSerializer,
)
from .services import (
    SENHA_PADRAO_PROMOTOR,
    buscar_demonstrativo_por_cpf,
    buscar_promotor_por_cpf,
    limpar_cpf,
    normalizar_texto,
    obter_colunas_cadastros,
    promotor_esta_ativo,
    serializar_valor,
)


class LoginPromotorView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Autenticação"],
        summary="Login do Promotor por CPF",
        request=LoginPromotorRequestSerializer,
        responses={200: LoginPromotorResponseSerializer, 401: ErroResponseSerializer},
        examples=[
            OpenApiExample("Exemplo Login", value={"cpf": "123.456.789-00", "senha": "express1234"}, request_only=True),
            OpenApiExample("Cadastro Inativo", value={"erro": "Acesso negado. Seu cadastro está inativo."}, response_only=True, status_codes=["401"]),
        ],
    )
    def post(self, request):
        ser = LoginPromotorRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cpf_limpo = limpar_cpf(ser.validated_data["cpf"])
        if len(cpf_limpo) != 11 or ser.validated_data["senha"] != SENHA_PADRAO_PROMOTOR:
            return Response({"erro": "CPF ou senha inválidos."}, status=status.HTTP_401_UNAUTHORIZED)
        promotor = buscar_promotor_por_cpf(cpf_limpo)
        if not promotor:
            return Response({"erro": "Promotor não encontrado na base de cadastros."}, status=status.HTTP_401_UNAUTHORIZED)
        if not promotor_esta_ativo(promotor):
            return Response({"erro": "Acesso negado. Seu cadastro está inativo."}, status=status.HTTP_401_UNAUTHORIZED)
        cols = obter_colunas_cadastros()
        token = gerar_token_promotor(str(promotor.get(cols["id"], "")), cpf_limpo, str(promotor.get(cols["nome"], "")))
        base_url = f"{request.scheme}://{request.get_host()}"
        return Response({
            "access_token": token,
            "token_type": "Bearer",
            "promotor": promotor,
            "demonstrativo": buscar_demonstrativo_por_cpf(cpf_limpo, base_url),
        })


class ListarCadastrosView(APIView):
    authentication_classes = [AdminKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Cadastros (Admin)"],
        summary="Consulta paginada de cadastros (informações e status)",
        parameters=[
            OpenApiParameter(name="page", type=int, default=1),
            OpenApiParameter(name="page_size", type=int, default=50),
            OpenApiParameter(name="busca", type=str, required=False, description="Filtro por nome ou CPF."),
            OpenApiParameter(name="status", type=str, required=False, enum=["todos", "ativos", "inativos"]),
        ],
        responses={200: ListaCadastrosResponseSerializer, 401: ErroResponseSerializer},
    )
    def get(self, request):
        page = max(1, int(request.query_params.get("page", 1) or 1))
        page_size = min(500, max(1, int(request.query_params.get("page_size", 50) or 50)))
        busca = normalizar_texto(request.query_params.get("busca") or "")
        filtro_status = (request.query_params.get("status") or "todos").strip().lower()
        cols_info = obter_colunas_cadastros()
        col_nome, col_cpf = cols_info["nome"], cols_info["cpf"]

        with connection.cursor() as cursor:
            cursor.execute(f'SELECT * FROM cadastros ORDER BY "{col_nome}" ASC')
            cols = [c[0] for c in cursor.description]
            todos = [{c: serializar_valor(v) for c, v in zip(cols, r)} for r in cursor.fetchall()]

        total_ativos = total_inativos = 0
        filtrados = []
        for reg in todos:
            ativo = promotor_esta_ativo(reg)
            total_ativos += int(ativo)
            total_inativos += int(not ativo)
            if (filtro_status == "ativos" and not ativo) or (filtro_status == "inativos" and ativo):
                continue
            if busca:
                nome_val = normalizar_texto(str(reg.get(col_nome) or ""))
                cpf_val = limpar_cpf(str(reg.get(col_cpf) or ""))
                busca_dig = limpar_cpf(busca)
                if busca not in nome_val and (not busca_dig or busca_dig not in cpf_val):
                    continue
            reg["_ativo"] = ativo
            filtrados.append(reg)

        total = len(filtrados)
        inicio = (page - 1) * page_size
        return Response({
            "total": total,
            "total_ativos": total_ativos,
            "total_inativos": total_inativos,
            "pagina_atual": page,
            "total_paginas": max(1, math.ceil(total / page_size)),
            "resultados": filtrados[inicio : inicio + page_size],
        })


class ImportarCadastrosView(APIView):
    authentication_classes = [AdminKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Cadastros (Admin)"],
        summary="Sincroniza cadastros em lote (atualiza existentes e insere novos por CPF)",
        request=ImportarCadastrosRequestSerializer,
        responses={200: ImportarCadastrosResponseSerializer, 400: ErroResponseSerializer, 401: ErroResponseSerializer},
        examples=[
            OpenApiExample(
                "Exemplo Request Body",
                value={"registros": [{"CPF": "12345678900", "NOME": "MARIA SILVA", "STATUS": "ATIVO"}]},
                request_only=True,
            ),
            OpenApiExample(
                "Exemplo Retorno",
                value={"total_atualizados": 1, "total_inseridos": 0, "ignorados_sem_cpf": 0, "colunas_mapeadas": ["cpf", "nome", "status"]},
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request):
        try:
            registros = request.data.get("registros")
            if not isinstance(registros, list) or not registros:
                return Response({"erro": "Envie uma lista válida em 'registros'."}, status=status.HTTP_400_BAD_REQUEST)

            with connection.cursor() as cursor:
                cursor.execute("SELECT column_name, column_default FROM information_schema.columns WHERE table_schema='public' AND table_name='cadastros' ORDER BY ordinal_position")
                info_cols = cursor.fetchall()

            colunas_banco = [r[0] for r in info_cols]
            colunas_com_default = {r[0] for r in info_cols if r[1] is not None}
            cols_info = obter_colunas_cadastros()
            col_id, col_cpf = cols_info["id"], cols_info["cpf"]

            with connection.cursor() as cursor:
                cursor.execute(f'SELECT DISTINCT LPAD(regexp_replace(COALESCE(CAST("{col_cpf}" AS TEXT), \'\'), \'[^0-9]\', \'\', \'g\'), 11, \'0\') FROM cadastros WHERE regexp_replace(COALESCE(CAST("{col_cpf}" AS TEXT), \'\'), \'[^0-9]\', \'\', \'g\') <> \'\'')
                cpfs_existentes = {r[0] for r in cursor.fetchall() if r[0]}

            mapa_colunas = {normalizar_texto(c).replace("_", "").replace(" ", ""): c for c in colunas_banco}
            registros_por_cpf, colunas_usadas, ignorados_sem_cpf = {}, set(), 0

            for item in registros:
                if not isinstance(item, dict):
                    continue
                linha = {}
                for k, v in item.items():
                    col_real = mapa_colunas.get(normalizar_texto(str(k)).replace("_", "").replace(" ", ""))
                    if not col_real or (col_real == col_id and col_real in colunas_com_default):
                        continue
                    linha[col_real] = None if (v is None or (isinstance(v, str) and v.strip() == "")) else str(v).strip()
                    colunas_usadas.add(col_real)
                if not linha:
                    continue
                cpf_limpo = limpar_cpf(linha.get(col_cpf) or "")
                if len(cpf_limpo) != 11:
                    ignorados_sem_cpf += 1
                    continue
                registros_por_cpf[cpf_limpo] = linha

            if not colunas_usadas:
                return Response({"erro": "Nenhuma coluna da planilha correspondeu à tabela 'cadastros'."}, status=status.HTTP_400_BAD_REQUEST)

            cols_ordenadas = [c for c in colunas_banco if c in colunas_usadas]
            cols_update = [c for c in cols_ordenadas if c != col_id]
            linhas_inserir, linhas_atualizar = [], []

            for cpf_limpo, linha in registros_por_cpf.items():
                if cpf_limpo in cpfs_existentes:
                    if cols_update:
                        linhas_atualizar.append([linha.get(c, None) for c in cols_update] + [cpf_limpo])
                else:
                    linhas_inserir.append([linha.get(c, None) for c in cols_ordenadas])
                    cpfs_existentes.add(cpf_limpo)

            with transaction.atomic():
                with connection.cursor() as cursor:
                    if linhas_atualizar:
                        set_sql = ", ".join([f'"{c}" = %s' for c in cols_update])
                        cursor.executemany(f'UPDATE cadastros SET {set_sql} WHERE LPAD(regexp_replace(COALESCE(CAST("{col_cpf}" AS TEXT), \'\'), \'[^0-9]\', \'\', \'g\'), 11, \'0\') = %s', linhas_atualizar)
                    if linhas_inserir:
                        placeholders = ", ".join(["%s"] * len(cols_ordenadas))
                        cols_sql = ", ".join([f'"{c}"' for c in cols_ordenadas])
                        cursor.executemany(f"INSERT INTO cadastros ({cols_sql}) VALUES ({placeholders})", linhas_inserir)
                        cursor.execute(f'UPDATE demonstrativos d SET cadastro_id = c."{col_id}"::text FROM cadastros c WHERE d.cadastro_id IS NULL AND LPAD(regexp_replace(COALESCE(CAST(c."{col_cpf}" AS TEXT), \'\'), \'[^0-9]\', \'\', \'g\'), 11, \'0\') = d.cpf_limpo')

            obter_colunas_cadastros.cache_clear()
            return Response({"total_atualizados": len(linhas_atualizar), "total_inseridos": len(linhas_inserir), "ignorados_sem_cpf": ignorados_sem_cpf, "colunas_mapeadas": cols_ordenadas})
        except Exception as exc:
            return Response({"erro": f"{type(exc).__name__}: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExcluirCadastrosView(APIView):
    authentication_classes = [AdminKeyAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Cadastros (Admin)"],
        summary="Exclui cadastros por lista de CPFs ou remove todos os inativos",
        request=ExcluirCadastrosRequestSerializer,
        responses={200: ExcluirCadastrosResponseSerializer, 400: ErroResponseSerializer, 401: ErroResponseSerializer},
        examples=[
            OpenApiExample("Excluir por CPFs", value={"cpfs": ["123.456.789-00"]}, request_only=True),
            OpenApiExample("Excluir todos inativos", value={"apenas_inativos": True}, request_only=True),
            OpenApiExample("Retorno Exclusão", value={"mensagem": "Exclusão de cadastros concluída.", "total_removidos": 1}, response_only=True, status_codes=["200"]),
        ],
    )
    def delete(self, request):
        dados = request.data if isinstance(request.data, dict) else {}
        cpfs_limpos = [limpar_cpf(c) for c in (dados.get("cpfs") or []) if len(limpar_cpf(c)) == 11]
        apenas_inativos = bool(dados.get("apenas_inativos", False))
        cols_info = obter_colunas_cadastros()
        col_id, col_cpf = cols_info["id"], cols_info["cpf"]

        if not cpfs_limpos and not apenas_inativos:
            return Response({"erro": "Informe 'cpfs' ou 'apenas_inativos': true no corpo da requisição."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            with connection.cursor() as cursor:
                if cpfs_limpos:
                    placeholders = ", ".join(["%s"] * len(cpfs_limpos))
                    cursor.execute(f'DELETE FROM cadastros WHERE LPAD(regexp_replace(COALESCE(CAST("{col_cpf}" AS TEXT), \'\'), \'[^0-9]\', \'\', \'g\'), 11, \'0\') IN ({placeholders})', cpfs_limpos)
                    removidos = cursor.rowcount
                else:
                    cursor.execute("SELECT * FROM cadastros")
                    cols = [c[0] for c in cursor.description]
                    ids_inativos = [r[cols.index(col_id)] for r in cursor.fetchall() if not promotor_esta_ativo({c: serializar_valor(v) for c, v in zip(cols, r)})]
                    if ids_inativos:
                        placeholders = ", ".join(["%s"] * len(ids_inativos))
                        cursor.execute(f'DELETE FROM cadastros WHERE "{col_id}" IN ({placeholders})', ids_inativos)
                        removidos = cursor.rowcount
                    else:
                        removidos = 0

        obter_colunas_cadastros.cache_clear()
        return Response({"mensagem": "Exclusão de cadastros concluída.", "total_removidos": removidos})
