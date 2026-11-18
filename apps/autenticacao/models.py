import uuid
from django.db import models


class Administrador(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    nome_completo = models.CharField(max_length=255)
    cargo = models.CharField(max_length=100, blank=True, null=True)
    telefone = models.CharField(max_length=30, blank=True, null=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField()
    user_id = models.IntegerField()

    class Meta:
        managed = False
        db_table = "administradores"
