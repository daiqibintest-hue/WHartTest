from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("knowledge", "0021_add_retrieval_config_and_heading_path"),
    ]

    operations = [
        migrations.AddField(
            model_name="knowledgeglobalconfig",
            name="enable_multi_query",
            field=models.BooleanField(
                default=False,
                help_text="Use LLM to generate multiple query variants for broader recall.",
                verbose_name="启用多路查询",
            ),
        ),
        migrations.AddField(
            model_name="knowledgeglobalconfig",
            name="multi_query_count",
            field=models.PositiveIntegerField(
                default=3,
                help_text="Number of query variants to generate (2-5).",
                verbose_name="多路查询变体数",
            ),
        ),
        migrations.AddField(
            model_name="knowledgeglobalconfig",
            name="enable_hyde",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Use LLM to generate a hypothetical answer, then search with "
                    "its embedding instead of the original query."
                ),
                verbose_name="启用 HyDE",
            ),
        ),
    ]
