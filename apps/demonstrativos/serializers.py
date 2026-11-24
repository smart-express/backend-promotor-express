from rest_framework import serializers


class ErroDemonstrativoSerializer(serializers.Serializer):
    erro = serializers.CharField()


class DemonstrativoItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    cadastro_id = serializers.CharField(allow_null=True)
    cpf_limpo = serializers.CharField()
    nome_promotor = serializers.CharField()
    periodo = serializers.CharField(allow_null=True)
    nome_arquivo = serializers.CharField()
    tamanho_bytes = serializers.IntegerField(allow_null=True)
    criado_em = serializers.CharField()


class MeuDemonstrativoResponseSerializer(serializers.Serializer):
    promotor = serializers.DictField(child=serializers.JSONField())
    demonstrativo = DemonstrativoItemSerializer(allow_null=True)


class LoteDemonstrativosListResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    pagina_atual = serializers.IntegerField()
    total_paginas = serializers.IntegerField()
    resultados = DemonstrativoItemSerializer(many=True)


class ImportarLoteSerializer(serializers.Serializer):
    arquivo_zip = serializers.FileField(required=False)
    arquivos_pdf = serializers.ListField(child=serializers.FileField(), required=False)


class NaoEncontradoItemSerializer(serializers.Serializer):
    arquivo = serializers.CharField()
    nome_extraido = serializers.CharField(allow_null=True)


class ImportarLoteResponseSerializer(serializers.Serializer):
    total_processados = serializers.IntegerField()
    total_vinculados = serializers.IntegerField()
    total_nao_encontrados = serializers.IntegerField(required=False)
    nao_encontrados = NaoEncontradoItemSerializer(many=True)


class LimparDemonstrativosRequestSerializer(serializers.Serializer):
    periodo = serializers.CharField(required=False, allow_blank=True, help_text="Período específico (ex: '2026-11-1Q').")
    cpfs = serializers.ListField(child=serializers.CharField(), required=False, help_text="Lista de CPFs específicos.")


class LimparDemonstrativosResponseSerializer(serializers.Serializer):
    mensagem = serializers.CharField()
    total_removidos = serializers.IntegerField()
