from rest_framework import serializers


class LoginAdminRequestSerializer(serializers.Serializer):
    login = serializers.CharField(
        help_text="Username, e-mail ou nome completo do administrador."
    )
    senha = serializers.CharField(
        write_only=True,
        help_text="Senha do usuário vinculado em auth_user.",
    )


class PromotorItemSerializer(serializers.Serializer):
    promotor = serializers.DictField(
        help_text="Objeto completo com todas as colunas do registro na tabela cadastros."
    )


class LoginAdminResponseSerializer(serializers.Serializer):
    administrador = serializers.DictField()
    total_cadastros = serializers.IntegerField()
    cadastros = PromotorItemSerializer(many=True)
