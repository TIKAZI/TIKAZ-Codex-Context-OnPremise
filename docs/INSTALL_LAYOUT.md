# Isolated installation layout

Runtime environments and models live on `G:`. Mutable input, cache, and output live on `F:`. Nothing large or private is committed.

```text
G:\CodexTools\token-forge\
  envs\documents
  envs\mineru
  envs\paddleocr
  envs\media
  envs\retrieval
  envs\llmlingua
  node\

G:\CodexTools\models\token-forge\
F:\TIKAZ-Token-Forge-Data\cache\
F:\TIKAZ-Token-Forge-Data\outputs\
F:\TIKAZ-Token-Forge-Data\sources\
```

The controller invokes adapters through configured executables. It never imports all heavy frameworks into one process. GPU-heavy work is serialized by default.

## Four cache layers

1. Acquisition cache: immutable source bytes and metadata keyed by source hash.
2. Conversion cache: canonical Markdown, tables, images, timestamps, and adapter version.
3. Index cache: chunks, lexical index, embeddings, and reranker version.
4. Query-pack cache: task, budget, safety class, selected evidence, and omissions.

Changing a query reuses acquisition, conversion, and index work. Changing an adapter invalidates only the dependent cache layers.
