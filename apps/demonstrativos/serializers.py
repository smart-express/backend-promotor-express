from rest_framework import serializers

class ImportarLoteSerializer(serializers.Serializer):
    arquivo_zip = serializers.FileField(required=False, help_text="Arquivo .zip com os PDFs.")
    arquivos_pdf = serializers.ListField(child=serializers.FileField(), required=False, help_text="Envio direto de múltiplos .pdf.")
