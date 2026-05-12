from django.db import migrations, models


def update_existing_default_config(apps, schema_editor):
    KnowledgeGlobalConfig = apps.get_model("knowledge", "KnowledgeGlobalConfig")
    KnowledgeBase = apps.get_model("knowledge", "KnowledgeBase")

    KnowledgeGlobalConfig.objects.filter(
        pk=1,
        chunk_strategy="recursive_character",
        chunk_size=1000,
        chunk_overlap=200,
    ).update(
        chunk_strategy="heading_aware",
        chunk_size=800,
        chunk_overlap=150,
    )

    KnowledgeBase.objects.filter(chunk_size=1000, chunk_overlap=200).update(
        chunk_size=800,
        chunk_overlap=150,
    )


def restore_previous_default_config(apps, schema_editor):
    KnowledgeGlobalConfig = apps.get_model("knowledge", "KnowledgeGlobalConfig")
    KnowledgeBase = apps.get_model("knowledge", "KnowledgeBase")

    KnowledgeGlobalConfig.objects.filter(
        pk=1,
        chunk_strategy="heading_aware",
        chunk_size=800,
        chunk_overlap=150,
    ).update(
        chunk_strategy="recursive_character",
        chunk_size=1000,
        chunk_overlap=200,
    )

    KnowledgeBase.objects.filter(chunk_size=800, chunk_overlap=150).update(
        chunk_size=1000,
        chunk_overlap=200,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("knowledge", "0022_add_multi_query_and_hyde"),
    ]

    operations = [
        migrations.AlterField(
            model_name="knowledgeglobalconfig",
            name="chunk_size",
            field=models.PositiveIntegerField(default=800, verbose_name="Chunk size"),
        ),
        migrations.AlterField(
            model_name="knowledgeglobalconfig",
            name="chunk_overlap",
            field=models.PositiveIntegerField(default=150, verbose_name="Chunk overlap"),
        ),
        migrations.AlterField(
            model_name="knowledgeglobalconfig",
            name="chunk_strategy",
            field=models.CharField(
                choices=[
                    ("recursive_character", "Fixed length"),
                    ("heading_aware", "Structure aware"),
                    ("markdown_header", "Markdown header"),
                ],
                default="heading_aware",
                help_text="Default chunking strategy for new or reprocessed documents.",
                max_length=50,
                verbose_name="Chunk strategy",
            ),
        ),
        migrations.AlterField(
            model_name="knowledgebase",
            name="chunk_size",
            field=models.PositiveIntegerField(default=800, verbose_name="Chunk size"),
        ),
        migrations.AlterField(
            model_name="knowledgebase",
            name="chunk_overlap",
            field=models.PositiveIntegerField(default=150, verbose_name="Chunk overlap"),
        ),
        migrations.RunPython(
            update_existing_default_config,
            restore_previous_default_config,
        ),
    ]
