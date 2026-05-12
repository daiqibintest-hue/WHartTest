from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("knowledge", "0020_add_parent_child_chunking"),
    ]

    operations = [
        # --- KnowledgeGlobalConfig: retrieval parameter config ---
        migrations.AddField(
            model_name="knowledgeglobalconfig",
            name="enable_query_rewrite",
            field=models.BooleanField(
                default=True,
                help_text="Use LLM to rewrite the query for better retrieval.",
                verbose_name="启用查询改写",
            ),
        ),
        migrations.AddField(
            model_name="knowledgeglobalconfig",
            name="enable_mmr",
            field=models.BooleanField(
                default=True,
                help_text="Apply Maximal Marginal Relevance diversification to reduce redundancy.",
                verbose_name="启用 MMR",
            ),
        ),
        migrations.AddField(
            model_name="knowledgeglobalconfig",
            name="mmr_lambda",
            field=models.FloatField(
                default=0.7,
                help_text="MMR diversity parameter: 0 = pure diversity, 1 = pure relevance.",
                verbose_name="MMR Lambda",
            ),
        ),
        migrations.AddField(
            model_name="knowledgeglobalconfig",
            name="reranker_weight",
            field=models.FloatField(
                default=0.6,
                help_text="Weight of the reranker score in the composite scoring formula.",
                verbose_name="Reranker 权重",
            ),
        ),
        migrations.AddField(
            model_name="knowledgeglobalconfig",
            name="rrf_weight",
            field=models.FloatField(
                default=0.3,
                help_text="Weight of the RRF fusion score in the composite scoring formula.",
                verbose_name="RRF 权重",
            ),
        ),
        # --- DocumentChunk: heading path ---
        migrations.AddField(
            model_name="documentchunk",
            name="heading_path",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Structural heading path, e.g. ['H1 title', 'H2 title'].",
                verbose_name="标题路径",
            ),
        ),
    ]
