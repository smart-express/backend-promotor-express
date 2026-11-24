from rest_framework import serializers


class ErroResponseSerializer(serializers.Serializer):
    erro = serializers.CharField(help_text="Descrição detalhada do erro.")


class DemonstrativoResumoSerializer(serializers.Serializer):
    id = serializers.CharField()
    nome_arquivo = serializers.CharField()
    periodo = serializers.CharField(allow_null=True)
    tamanho_bytes = serializers.IntegerField(allow_null=True)
    criado_em = serializers.CharField()
    url_visualizar = serializers.URLField()
    url_download = serializers.URLField()


class LoginPromotorRequestSerializer(serializers.Serializer):
    cpf = serializers.CharField(help_text="CPF do promotor (com ou sem pontos e traço).")
    senha = serializers.CharField(help_text="Senha de acesso do promotor.")


class LoginPromotorResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    token_type = serializers.CharField(default="Bearer")
    promotor = serializers.DictField(child=serializers.JSONField())
    demonstrativo = DemonstrativoResumoSerializer(allow_null=True)


class ImportarCadastrosRequestSerializer(serializers.Serializer):
    registros = serializers.ListField(
        child=serializers.DictField(child=serializers.JSONField()),
        help_text="Lista de objetos representando as linhas da planilha de cadastros.",
    )


class ImportarCadastrosResponseSerializer(serializers.Serializer):
    total_atualizados = serializers.IntegerField()
    total_inseridos = serializers.IntegerField()
    ignorados_sem_cpf = serializers.IntegerField()
    colunas_mapeadas = serializers.ListField(child=serializers.CharField())


class ListaCadastrosResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    total_ativos = serializers.IntegerField()
    total_inativos = serializers.IntegerField()
    pagina_atual = serializers.IntegerField()
    total_paginas = serializers.IntegerField()
    resultados = serializers.ListField(child=serializers.DictField(child=serializers.JSONField()))


class ExcluirCadastrosRequestSerializer(serializers.Serializer):
    cpfs = serializers.ListField(child=serializers.CharField(), required=False, help_text="Lista de CPFs para exclusão.")
    apenas_inativos = serializers.BooleanField(required=False, default=False, help_text="Se true, remove todos os inativos.")


class ExcluirCadastrosResponseSerializer(serializers.Serializer):
    mensagem = serializers.CharField()
    total_removidos = serializers.IntegerField()
