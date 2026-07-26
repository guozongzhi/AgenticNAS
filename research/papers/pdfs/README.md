# 本地论文 PDF 缓存

本目录保存从 arXiv 下载的阅读副本。`*.pdf` 和未完成的 `*.part` 文件已被 Git 忽略；远端仓库仅保留本清单、论文索引和原创笔记。

| Local file | arXiv | Pages | SHA-256 |
|---|---:|---:|---|
| [1909.01051-manas.pdf](1909.01051-manas.pdf) | [1909.01051](https://arxiv.org/abs/1909.01051) | 24 | `55fb04f8af406f045b663c3d899da00bcb4e224ebc937e78fc4a087c0d044068` |
| [2302.14838-evoprompting.pdf](2302.14838-evoprompting.pdf) | [2302.14838](https://arxiv.org/abs/2302.14838) | 31 | `8febb503edfda11041e01ad7c7e5b1454dda5740ac9d37251a449601d3afe2da` |
| [2306.01102-llmatic.pdf](2306.01102-llmatic.pdf) | [2306.01102](https://arxiv.org/abs/2306.01102) | 9 | `3ad56f3077fddbded7b5c57e752d5a67727aa5532c8d30fc515d193c322a2bc9` |
| [2310.03302-mlagentbench.pdf](2310.03302-mlagentbench.pdf) | [2310.03302](https://arxiv.org/abs/2310.03302) | 39 | `09837c2813668ee6dcb00abdf22b6293a9ad6ef4c135774bc504e233db017702` |
| [2312.00949-llm-instruction-tuning-hpo.pdf](2312.00949-llm-instruction-tuning-hpo.pdf) | [2312.00949](https://arxiv.org/abs/2312.00949) | 9 | `6da1f4e998c2ea1ab1960e6e05d2066a05263f5afb00d2642916a7b89a5cb669` |
| [2312.04528-llm-hpo.pdf](2312.04528-llm-hpo.pdf) | [2312.04528](https://arxiv.org/abs/2312.04528) | 28 | `d6193c6909e01773145d9e9a062a5a6dea7fd106fb902696df4852fd8eb4af49` |
| [2402.01881-agenthpo.pdf](2402.01881-agenthpo.pdf) | [2402.01881](https://arxiv.org/abs/2402.01881) | 24 | `c2d8097dd384e96728ab32368358d950295f236e2b3eed54adce01317cf5f971` |
| [2402.03921-llambo.pdf](2402.03921-llambo.pdf) | [2402.03921](https://arxiv.org/abs/2402.03921) | 33 | `7b6040f88088039c40e632c4ac0649da61c9d255eb7091fa898790ecae3e4cae` |
| [2412.19206-nader.pdf](2412.19206-nader.pdf) | [2412.19206](https://arxiv.org/abs/2412.19206) | 18 | `465282d63160e25eeb47f1a8253b3b8f5d61d1929dcd5d5acdc34e39a9297d12` |
| [2603.15939-data-local-llm-nas.pdf](2603.15939-data-local-llm-nas.pdf) | [2603.15939](https://arxiv.org/abs/2603.15939) | 16 | `2d5ee55c5bb65a3e2ffb7994f5bbebb99579ca934e03592e32aa06c6ca648f61` |
| [2605.11518-autollmresearch.pdf](2605.11518-autollmresearch.pdf) | [2605.11518](https://arxiv.org/abs/2605.11518) | 41 | `e5ccece82a6d45934b575d3008cc39cdd5b26ae40c6fdc0ce8eba11b73dccc17` |
| [2606.10294-uh-nas.pdf](2606.10294-uh-nas.pdf) | [2606.10294](https://arxiv.org/abs/2606.10294) | 16 | `a668a991e9528afad1f05d9ebdb7ca80536a1c3886a2b13b5ffeb640e3d731cf` |

重新校验单个文件：

```bash
pdfinfo research/papers/pdfs/2302.14838-evoprompting.pdf
shasum -a 256 research/papers/pdfs/2302.14838-evoprompting.pdf
```
