import os, re, uuid, zipfile
from pathlib import Path
from django.conf import settings
from django.db import connection
from apps.autenticacao.services import limpar_cpf, normalizar_texto, obter_colunas_cadastros

PASTA_DEMONSTRATIVOS = Path(settings.MEDIA_ROOT) / "demonstrativos"

def extrair_nome_e_periodo(nome_arquivo: str) -> tuple[str, str | None]:
    sem_ext = re.sub(r"\.pdf$", "", Path(nome_arquivo).name, flags=re.IGNORECASE).strip()
    m = re.match(r"^(?P<nome>.+?)\s*-\s*(?P<periodo>\d{2}-\d{2}-\d{4}\s*a\s*\d{2}-\d{2}-\d{4})$", sem_ext, flags=re.IGNORECASE)
    if m:
        return m.group("nome").strip(), m.group("periodo").strip()
    if " - " in sem_ext:
        p = sem_ext.rsplit(" - ", 1)
        return p[0].strip(), p[1].strip()
    return sem_ext, None

def _carregar_mapa_promotores() -> dict[str, dict]:
    c = obter_colunas_cadastros()
    sql = f"SELECT {c['id']}, {c['nome']}, {c['cpf']} FROM cadastros WHERE {c['nome']} IS NOT NULL AND {c['cpf']} IS NOT NULL"
    mapa = {}
    with connection.cursor() as cursor:
        cursor.execute(sql)
        for r in cursor.fetchall():
            nome_orig, cpf_l = str(r[1]).strip(), limpar_cpf(str(r[2]))
            if nome_orig and len(cpf_l) == 11:
                mapa[normalizar_texto(nome_orig)] = {"cadastro_id": str(r[0]), "nome_promotor": nome_orig, "cpf_limpo": cpf_l}
    return mapa

def _salvar_individual(info: dict, nome_orig: str, periodo: str | None, conteudo: bytes) -> None:
    PASTA_DEMONSTRATIVOS.mkdir(parents=True, exist_ok=True)
    cpf_l = info["cpf_limpo"]
    with connection.cursor() as cursor:
        cursor.execute("SELECT caminho_arquivo FROM demonstrativos WHERE cpf_limpo = %s", [cpf_l])
        for (cam,) in cursor.fetchall():
            if cam and os.path.exists(cam):
                try:
                    os.remove(cam)
                except OSError:
                    pass
        cursor.execute("DELETE FROM demonstrativos WHERE cpf_limpo = %s", [cpf_l])
        destino = PASTA_DEMONSTRATIVOS / f"{cpf_l}_{uuid.uuid4().hex[:8]}.pdf"
        destino.write_bytes(conteudo)
        cursor.execute(
            "INSERT INTO demonstrativos (cadastro_id, cpf_limpo, nome_promotor, periodo, nome_arquivo, caminho_arquivo, tamanho_bytes) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            [info["cadastro_id"], cpf_l, info["nome_promotor"], periodo, Path(nome_orig).name, str(destino), len(conteudo)],
        )

def processar_importacao_lote(arquivo_zip=None, lista_pdfs=None) -> dict:
    mapa = _carregar_mapa_promotores()
    itens, vinculados, nao_encontrados = [], 0, []
    if arquivo_zip:
        with zipfile.ZipFile(arquivo_zip, "r") as zf:
            for z in zf.infolist():
                nome_in = Path(z.filename).name
                if not z.is_dir() and not nome_in.startswith(".") and "__MACOSX" not in z.filename and nome_in.lower().endswith(".pdf"):
                    itens.append((nome_in, zf.read(z.filename)))
    for arq in (lista_pdfs or []):
        if arq.name.lower().endswith(".pdf"):
            itens.append((arq.name, arq.read()))
    for nome_arq, conteudo in itens:
        nome_ext, periodo = extrair_nome_e_periodo(nome_arq)
        prom = mapa.get(normalizar_texto(nome_ext))
        if not prom:
            nao_encontrados.append({"arquivo": nome_arq, "nome_extraido": nome_ext})
            continue
        _salvar_individual(prom, nome_arq, periodo, conteudo)
        vinculados += 1
    return {"total_processados": len(itens), "total_vinculados": vinculados, "total_nao_encontrados": len(nao_encontrados), "nao_encontrados": nao_encontrados}

def limpar_todos_demonstrativos(periodo: str | None = None) -> int:
    with connection.cursor() as cursor:
        if periodo:
            cursor.execute("SELECT caminho_arquivo FROM demonstrativos WHERE periodo = %s", [periodo.strip()])
        else:
            cursor.execute("SELECT caminho_arquivo FROM demonstrativos")
        caminhos = [r[0] for r in cursor.fetchall()]
        for cam in caminhos:
            if cam and os.path.exists(cam):
                try:
                    os.remove(cam)
                except OSError:
                    pass
        if periodo:
            cursor.execute("DELETE FROM demonstrativos WHERE periodo = %s", [periodo.strip()])
        else:
            cursor.execute("DELETE FROM demonstrativos")
    return len(caminhos)
