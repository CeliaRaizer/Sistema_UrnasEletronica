from django.db import migrations

MUNICIPIOS = ["Ibiam", "Tangará", "Pinheiro Preto", "Ibicaré", "Treze Tílias"]


def criar(apps, schema_editor):
    Municipio = apps.get_model("api", "Municipio")
    for nome in MUNICIPIOS:
        Municipio.objects.get_or_create(nome=nome)


class Migration(migrations.Migration):
    dependencies = [("api", "0001_initial")]
    operations = [migrations.RunPython(criar, migrations.RunPython.noop)]
