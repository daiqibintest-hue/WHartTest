from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("knowledge", "0023_update_chunk_defaults"),
    ]

    operations = [
        migrations.AlterField(
            model_name="knowledgeglobalconfig",
            name="reranker_service",
            field=models.CharField(
                choices=[
                    ("none", "不启用"),
                    ("xinference", "Xinference"),
                    ("dashscope", "DashScope (阿里百炼)"),
                    ("custom", "自定义 API"),
                ],
                default="none",
                help_text="Optional reranker used after recall.",
                max_length=50,
                verbose_name="Reranker service",
            ),
        ),
        migrations.AlterField(
            model_name="knowledgeglobalconfig",
            name="chunk_strategy",
            field=models.CharField(
                choices=[
                    ("recursive_character", "固定长度"),
                    ("heading_aware", "结构优先"),
                    ("markdown_header", "Markdown 标题"),
                ],
                default="heading_aware",
                help_text="Default chunking strategy for new or reprocessed documents.",
                max_length=50,
                verbose_name="Chunk strategy",
            ),
        ),
    ]
