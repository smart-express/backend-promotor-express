from rest_framework import serializers

class LoginPromotorRequestSerializer(serializers.Serializer):
    cpf = serializers.CharField(help_text="CPF com ou sem pontos e traços.")
    senha = serializers.CharField(write_only=True, help_text="Senha padrão (express1234).")
