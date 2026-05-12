# Knowledge RAG Enhancement Priority Plan

## 1. 背景

当前项目的知识库已经具备完整的 RAG 能力，包括：

- 文档解析与入库
- Embedding 向量化
- Qdrant 存储
- BM25 + Dense 混合检索
- RRF 融合
- 可选 Reranker 精排
- Query Rewrite / Multi-Query / HyDE 多路径检索
- MMR 多样性去重
- 邻近 chunk 上下文扩展
- Parent-Child 双层切分检索
- 元数据过滤
- 多种切分策略（固定长度、结构优先、Markdown 标题）

## 2. 优先级总览

```text
P0: 检索级元数据过滤          ✅ 已完成
P1: Parent-Child 检索         ✅ 已完成
P2: 切分策略增强              ✅ 已完成
P3: 查询增强策略配置化        ✅ 已完成
```

## 3. 当前实现状态

### 3.1 P0 元数据过滤 ✅

已落地能力：

- `Document` 支持字段：`tags`、`metadata`、`module`、`version`、`business_domain`、`document_stage`
- `QueryLog` 记录本次查询使用的 `metadata_filter`
- 文档入库 Qdrant 时，chunk payload 继承文档元数据
- 查询 API 支持过滤条件：`document_ids`、`document_type`、`tags`、`module`、`version`、`business_domain`、`document_stage`、`metadata_filter`
- Dense 检索和 Hybrid 检索都支持 Qdrant `query_filter`
- 前端支持：上传文档时录入元数据、查询面板传入过滤条件、文档详情展示元数据、批量重处理

### 3.2 P1 Parent-Child 检索 ✅

已落地能力：

- `DocumentChunk` 新增：`parent_chunk`（自引用 ForeignKey）、`chunk_level`（`parent` 或 `child`）
- `KnowledgeGlobalConfig` 新增：`parent_child_enabled`、`parent_chunk_size`、`parent_chunk_overlap`、`child_chunk_size`、`child_chunk_overlap`
- `KnowledgeBase` 支持 per-KB 级别 chunk 参数覆盖
- 两层切分：Parent 存 PostgreSQL 不向量化，Child 向量化后存 Qdrant（payload 含 `parent_chunk_id`）
- 检索命中 Child 后替换为 Parent 内容
- 同 Parent 多 Child 命中时去重合并分数
- 向后兼容：旧文档无 `parent_chunk_id` 时自动走原有邻居扩展逻辑
- 前端支持：全局配置弹窗支持 Parent-Child 模式开关和参数配置，知识库级别可覆盖

### 3.3 P2 切分策略增强 ✅

第一阶段：

- `KnowledgeGlobalConfig` 新增 `chunk_strategy`，支持三种策略：
  - `recursive_character`：固定 `chunk_size/chunk_overlap` 的字符级切分
  - `heading_aware`：优先按标题、段落、换行和中英文句号等分隔符切分
  - `markdown_header`：对 Markdown 文档按标题层级先切，再递归细分
- 后端索引时按 `chunk_strategy` 选择切分逻辑
- 前端全局配置弹窗支持切分策略选择

第二阶段：

- `DocumentChunk` 新增 `heading_path`（JSONField），存储结构化标题路径如 `["H1 标题", "H2 标题", "H3 标题"]`
- `markdown_header` 策略：从 h1/h2/h3/h4 metadata 构建 heading_path
- `heading_aware` 策略：从 chunk 内容中正则提取 Markdown 标题构建 heading_path
- Parent-Child 模式下 parent 和 child 都保存 heading_path（child 继承 parent）
- 前端文档详情页 chunk 列表展示 heading_path 和 chunk_level 标签
- 切分策略变更时前端显示重处理提示

### 3.4 P3 查询增强策略配置化 ✅

检索参数配置化：

- `KnowledgeGlobalConfig` 新增字段：
  - `enable_query_rewrite`（默认开启）：是否启用单次查询改写
  - `enable_mmr`（默认开启）：是否启用 MMR 多样性去重
  - `mmr_lambda`（默认 0.7）：MMR lambda 参数，0=纯多样性，1=纯相关性
  - `reranker_weight`（默认 0.6）：Reranker 分数在复合评分中的权重
  - `rrf_weight`（默认 0.3）：RRF 融合分数在复合评分中的权重
- `_composite_score` 改为实例方法，从配置读取权重
- MMR 和 Query Rewrite 开关从配置读取
- 前端全局配置弹窗支持所有参数调整（开关 + 滑块）

多路查询（Multi-Query）：

- `KnowledgeGlobalConfig` 新增字段：
  - `enable_multi_query`（默认关闭）：是否启用多路查询
  - `multi_query_count`（默认 3）：生成的查询变体数量（2-5）
- LLM 将用户问题改写为 N 个不同角度的查询，分别检索后合并去重
- 与单次 Query Rewrite 互斥：开启 Multi-Query 时自动跳过单次改写

HyDE（Hypothetical Document Embeddings）：

- `KnowledgeGlobalConfig` 新增 `enable_hyde`（默认关闭）
- LLM 根据问题生成一段假想答案，用答案的 embedding 做检索
- 假想答案是陈述式文本，与知识库文档在向量空间中更接近
- 与 Multi-Query / Query Rewrite 可叠加使用

完整检索流程：

```text
原始查询
  │
  ├─ 路径 1: 原始查询 → similarity_search
  │
  ├─ 路径 2 (HyDE): LLM 生成假想答案 → similarity_search
  │
  ├─ 路径 3 (Multi-Query): LLM 生成 N 个变体 → 每个变体 similarity_search
  │   └─ 或路径 3 (Query Rewrite): LLM 改写 1 次 → similarity_search
  │
  ▼ 合并所有路径结果 → 去重 → 按 score 排序 → top_k
  │
  ▼ parent_child_expand / expand_context
  │
  ▼ 最终结果
```

## 4. 实施历史

```text
阶段 A：P0 元数据过滤 ✅
1. Document 增加 metadata/tags
2. 上传与查询 UI 支持元数据
3. Qdrant payload 写入元数据
4. Dense/Hybrid 检索支持 metadata_filter
5. QueryLog 记录过滤条件

阶段 B：P2 切分策略 ✅
6. 全局配置增加 chunk_strategy
7. 后端接通 recursive_character / heading_aware / markdown_header
8. 前端全局配置弹窗支持切分策略
9. heading_path 持久化和前端展示
10. 切分策略变更重处理提示

阶段 C：P1 Parent-Child ✅
11. Parent-Child 数据结构
12. Parent-Child 入库逻辑
13. Parent-Child 检索返回逻辑
14. 同 parent 多 child 命中的去重逻辑

阶段 D：P3 查询增强 ✅
15. 检索参数配置化（Query Rewrite / MMR / Reranker / RRF 开关和参数）
16. Multi-Query 多路查询
17. HyDE 假想答案检索
```

## 5. 验收口径

### P0 验收 ✅

- 查询能按模块、版本、标签、业务域、阶段过滤
- Dense/Hybrid 检索结果一致遵守过滤条件
- QueryLog 可追踪本次过滤条件

### P1 验收 ✅

- 入库生成 parent/child 双层 chunk
- Qdrant payload 含 `parent_chunk_id`
- 命中 child 时返回 parent 作为最终上下文
- 同 parent 下多 child 命中时能去重

### P2 验收 ✅

- 全局配置里可切换 `chunk_strategy`
- 新上传或重处理文档时按选定策略切分
- Markdown 文档可按标题层级切分
- 文档详情页 chunk 列表展示 heading_path 和 chunk_level
- 切分策略变更时显示重处理提示

### P3 验收 ✅

- 全局配置弹窗可调整 Query Rewrite / MMR 开关和参数
- 全局配置弹窗可调整 Reranker / RRF 权重
- 全局配置弹窗可开启 Multi-Query 并设置变体数量
- 全局配置弹窗可开启 HyDE
- 开启 Multi-Query 后查询，日志可见多个变体被检索
- 开启 HyDE 后查询，日志可见假想答案生成和检索
- Multi-Query 和 Query Rewrite 互斥生效

## 6. 当前注意事项

- 切分策略默认值为 `recursive_character`，需要在全局配置里手动切换
- 切分策略切换后，历史文档必须重处理，否则 Qdrant 中仍是旧切法
- Multi-Query 和 HyDE 会增加 LLM 调用开销和响应延迟，按需开启
- `KnowledgeBase` 级别暂无独立的 `chunk_strategy` 覆盖能力，以全局配置为主

## 7. 结论

四个优先级全部完成：

- **P0：已完成** — 元数据过滤全链路
- **P1：已完成** — Parent-Child 双层切分检索
- **P2：已完成** — 多种切分策略 + heading_path 结构路径展示
- **P3：已完成** — 检索参数配置化 + Multi-Query + HyDE
