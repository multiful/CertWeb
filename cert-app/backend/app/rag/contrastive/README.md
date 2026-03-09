---
tags:
- sentence-transformers
- sentence-similarity
- feature-extraction
- dense
- generated_from_trainer
- dataset_size:1556
- loss:TripletLoss
base_model: jhgan/ko-sroberta-multitask
widget:
- source_sentence: 개발 쪽 준비하고 있어
  sentences:
  - '[자격증명: 전기기사] 자격증명: 전기기사 | 유형: 국가기술자격 | 분야: 전기 | NCS분류: 전기.전자 | 시행기관: 한국산업인력공단
    | 등급: 기사 | 관련전공: ICT로봇공학전공, 휴먼지능로봇공학과, 휴먼・로봇융합전공, 지능형로봇융합전공, 지능로봇학과'
  - '[자격증명: SQL개발자(SQLD)] 자격증명: SQL개발자(SQLD) | 유형: 국가민간자격 | 분야: 정보기술 | NCS분류: 정보통신
    | 시행기관: 한국데이터산업진흥원 | 등급: 1 | 관련전공: IT미디어공학과, IT·디자인융합학부, ICT융합콘텐츠전공, 인공지능융합전공,
    인공지능소프트웨어전공'
  - '[자격증명: SQL개발자(SQLD)] 자격증명: SQL개발자(SQLD) | 유형: 국가민간자격 | 분야: 정보기술 | NCS분류: 정보통신
    | 시행기관: 한국데이터산업진흥원 | 등급: 1 | 관련전공: IT미디어공학과, IT·디자인융합학부, ICT융합콘텐츠전공, 인공지능융합전공,
    인공지능소프트웨어전공'
- source_sentence: '전공: 국어국문학과 학년: 3학년 희망직무: 개발 관심 자격증: 없음 취득 자격증: 없음 목적: 입문, 취업 준비'
  sentences:
  - '[자격증명: 철도운송산업기사] 자격증명: 철도운송산업기사 | 유형: 국가기술자격 | 분야: 철도운전.운송 | NCS분류: 운전.운송 | 시행기관:
    한국산업인력공단 | 등급: 산업기사 | 관련전공: 철도전기기관사과, 철도교통학부, 철도운수설비과, 철도운전제어공학과, 철도차량운전과'
  - '[자격증명: 데이터분석준전문가(ADsP)] 자격증명: 데이터분석준전문가(ADsP) | 유형: 국가민간자격 | 분야: 정보기술 | NCS분류:
    정보통신 | 시행기관: (재)한국데이터진흥원 | 등급: 1 | 관련전공: 모바일시스템공학과, 모바일융합공학과, 전자공학부모바일공학전공, 전자정보공학부,
    IT융합학부'
  - '[자격증명: 컴퓨터활용능력 2급] 자격증명: 컴퓨터활용능력 2급 | 유형: 국가기술자격 | 분야: 사업관리 | NCS분류: 사업관리 | 관련전공:
    IT학부, AI・데이터공학부, AI・빅데이터학과, AI・컴퓨터공학과, AI빅데이터전공'
- source_sentence: '전공: 소프트웨어학과 학년: 4학년 희망직무: 실무 관심 자격증: 없음 취득 자격증: 정보처리기사 목적: 취업
    준비'
  sentences:
  - '[자격증명: 측량및지형공간정보기사] 자격증명: 측량및지형공간정보기사 | 유형: 국가기술자격 | 분야: 정보기술 | NCS분류: 정보통신 |
    시행기관: 한국산업인력공단 | 등급: 기사 | 관련전공: 지리학과, 지리학과(자연계열), 지적학전공, 지적학과, 위치정보시스템학과'
  - '[자격증명: 데이터분석준전문가(ADsP)] 자격증명: 데이터분석준전문가(ADsP) | 유형: 국가민간자격 | 분야: 정보기술 | NCS분류:
    정보통신 | 시행기관: (재)한국데이터진흥원 | 등급: 1 | 관련전공: 모바일시스템공학과, 모바일융합공학과, 전자공학부모바일공학전공, 전자정보공학부,
    IT융합학부'
  - '[자격증명: SQL개발자(SQLD)] 자격증명: SQL개발자(SQLD) | 유형: 국가민간자격 | 분야: 정보기술 | NCS분류: 정보통신
    | 시행기관: 한국데이터산업진흥원 | 등급: 1 | 관련전공: IT미디어공학과, IT·디자인융합학부, ICT융합콘텐츠전공, 인공지능융합전공,
    인공지능소프트웨어전공'
- source_sentence: 비전공자인데 개발 공부 시작했어
  sentences:
  - '[자격증명: 종자기사] 자격증명: 종자기사 | 유형: 국가기술자격 | 분야: 농업 | NCS분류: 농림어업 | 시행기관: 한국산업인력공단
    | 등급: 기사 | 관련전공: 식량자원과학과, 식량생명공학과, 생물자원과학부, 자원공학과, 식의약자원개발학과'
  - '[자격증명: 빅데이터분석기사] 자격증명: 빅데이터분석기사 | 유형: 국가기술자격 | 분야: 정보기술 | NCS분류: 정보통신 | 시행기관:
    한국산업인력공단 | 등급: 기사'
  - '[자격증명: 정보처리기사] 자격증명: 정보처리기사 | 유형: 국가기술자격 | 분야: 정보기술 | NCS분류: 정보통신 | 시행기관: 한국산업인력공단
    | 등급: 기사 | 관련전공: 지능・데이터융합학부, 인공지능융합공학부, 첨단공학부, 소프트웨어학부, 정보전자공학과'
- source_sentence: '전공: 경영정보학과 학년: 4학년 희망직무: 사무 관심 자격증: 없음 취득 자격증: 없음 목적: 취업 준비'
  sentences:
  - '[자격증명: 종자기사] 자격증명: 종자기사 | 유형: 국가기술자격 | 분야: 농업 | NCS분류: 농림어업 | 시행기관: 한국산업인력공단
    | 등급: 기사 | 관련전공: 식량자원과학과, 식량생명공학과, 생물자원과학부, 자원공학과, 식의약자원개발학과'
  - '[자격증명: 컴퓨터활용능력 2급] 자격증명: 컴퓨터활용능력 2급 | 유형: 국가기술자격 | 분야: 사업관리 | NCS분류: 사업관리 | 관련전공:
    IT학부, AI・데이터공학부, AI・빅데이터학과, AI・컴퓨터공학과, AI빅데이터전공'
  - '[자격증명: 빅데이터분석기사] 자격증명: 빅데이터분석기사 | 유형: 국가기술자격 | 분야: 정보기술 | NCS분류: 정보통신 | 시행기관:
    한국산업인력공단 | 등급: 기사'
pipeline_tag: sentence-similarity
library_name: sentence-transformers
---

# SentenceTransformer based on jhgan/ko-sroberta-multitask

This is a [sentence-transformers](https://www.SBERT.net) model finetuned from [jhgan/ko-sroberta-multitask](https://huggingface.co/jhgan/ko-sroberta-multitask). It maps sentences & paragraphs to a 768-dimensional dense vector space and can be used for semantic textual similarity, semantic search, paraphrase mining, text classification, clustering, and more.

## Model Details

### Model Description
- **Model Type:** Sentence Transformer
- **Base model:** [jhgan/ko-sroberta-multitask](https://huggingface.co/jhgan/ko-sroberta-multitask) <!-- at revision ab957ae6a91e99c4cad36d52063a2a9cf1bf4419 -->
- **Maximum Sequence Length:** 256 tokens
- **Output Dimensionality:** 768 dimensions
- **Similarity Function:** Cosine Similarity
<!-- - **Training Dataset:** Unknown -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Documentation:** [Sentence Transformers Documentation](https://sbert.net)
- **Repository:** [Sentence Transformers on GitHub](https://github.com/huggingface/sentence-transformers)
- **Hugging Face:** [Sentence Transformers on Hugging Face](https://huggingface.co/models?library=sentence-transformers)

### Full Model Architecture

```
SentenceTransformer(
  (0): Transformer({'max_seq_length': 256, 'do_lower_case': False, 'architecture': 'RobertaModel'})
  (1): Pooling({'word_embedding_dimension': 768, 'pooling_mode_cls_token': False, 'pooling_mode_mean_tokens': True, 'pooling_mode_max_tokens': False, 'pooling_mode_mean_sqrt_len_tokens': False, 'pooling_mode_weightedmean_tokens': False, 'pooling_mode_lasttoken': False, 'include_prompt': True})
)
```

## Usage

### Direct Usage (Sentence Transformers)

First install the Sentence Transformers library:

```bash
pip install -U sentence-transformers
```

Then you can load this model and run inference.
```python
from sentence_transformers import SentenceTransformer

# Download from the 🤗 Hub
model = SentenceTransformer("sentence_transformers_model_id")
# Run inference
sentences = [
    '전공: 경영정보학과 학년: 4학년 희망직무: 사무 관심 자격증: 없음 취득 자격증: 없음 목적: 취업 준비',
    '[자격증명: 컴퓨터활용능력 2급] 자격증명: 컴퓨터활용능력 2급 | 유형: 국가기술자격 | 분야: 사업관리 | NCS분류: 사업관리 | 관련전공: IT학부, AI・데이터공학부, AI・빅데이터학과, AI・컴퓨터공학과, AI빅데이터전공',
    '[자격증명: 종자기사] 자격증명: 종자기사 | 유형: 국가기술자격 | 분야: 농업 | NCS분류: 농림어업 | 시행기관: 한국산업인력공단 | 등급: 기사 | 관련전공: 식량자원과학과, 식량생명공학과, 생물자원과학부, 자원공학과, 식의약자원개발학과',
]
embeddings = model.encode(sentences)
print(embeddings.shape)
# [3, 768]

# Get the similarity scores for the embeddings
similarities = model.similarity(embeddings, embeddings)
print(similarities)
# tensor([[ 1.0000,  0.3410, -0.1606],
#         [ 0.3410,  1.0000, -0.0415],
#         [-0.1606, -0.0415,  1.0000]])
```

<!--
### Direct Usage (Transformers)

<details><summary>Click to see the direct usage in Transformers</summary>

</details>
-->

<!--
### Downstream Usage (Sentence Transformers)

You can finetune this model on your own dataset.

<details><summary>Click to expand</summary>

</details>
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Dataset

#### Unnamed Dataset

* Size: 1,556 training samples
* Columns: <code>sentence_0</code>, <code>sentence_1</code>, and <code>sentence_2</code>
* Approximate statistics based on the first 1000 samples:
  |         | sentence_0                                                                        | sentence_1                                                                          | sentence_2                                                                          |
  |:--------|:----------------------------------------------------------------------------------|:------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------|
  | type    | string                                                                            | string                                                                              | string                                                                              |
  | details | <ul><li>min: 5 tokens</li><li>mean: 25.75 tokens</li><li>max: 58 tokens</li></ul> | <ul><li>min: 35 tokens</li><li>mean: 94.18 tokens</li><li>max: 119 tokens</li></ul> | <ul><li>min: 48 tokens</li><li>mean: 83.42 tokens</li><li>max: 110 tokens</li></ul> |
* Samples:
  | sentence_0                                                                             | sentence_1                                                                                                                                                                                    | sentence_2                                                                                                                                                                |
  |:---------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
  | <code>전공: 컴퓨터공학과 학년: 3학년 희망직무: 데이터분석 관심 자격증: 정보처리기사 취득 자격증: 없음 목적: 직무 관련 자격증 추천</code> | <code>[자격증명: SQL개발자(SQLD)] 자격증명: SQL개발자(SQLD) \| 유형: 국가민간자격 \| 분야: 정보기술 \| NCS분류: 정보통신 \| 시행기관: 한국데이터산업진흥원 \| 등급: 1 \| 관련전공: IT미디어공학과, IT·디자인융합학부, ICT융합콘텐츠전공, 인공지능융합전공, 인공지능소프트웨어전공</code>   | <code>[자격증명: 측량및지형공간정보기술사] 자격증명: 측량및지형공간정보기술사 \| 유형: 국가기술자격 \| 분야: 정보기술 \| NCS분류: 정보통신 \| 등급: 기술사</code>                                                                  |
  | <code>IT 쪽 취업하고 싶어</code>                                                              | <code>[자격증명: SQL개발자(SQLD)] 자격증명: SQL개발자(SQLD) \| 유형: 국가민간자격 \| 분야: 정보기술 \| NCS분류: 정보통신 \| 시행기관: 한국데이터산업진흥원 \| 등급: 1 \| 관련전공: IT미디어공학과, IT·디자인융합학부, ICT융합콘텐츠전공, 인공지능융합전공, 인공지능소프트웨어전공</code>   | <code>[자격증명: 종자기사] 자격증명: 종자기사 \| 유형: 국가기술자격 \| 분야: 농업 \| NCS분류: 농림어업 \| 시행기관: 한국산업인력공단 \| 등급: 기사 \| 관련전공: 식량자원과학과, 식량생명공학과, 생물자원과학부, 자원공학과, 식의약자원개발학과</code>              |
  | <code>전공: 산업데이터공학 학년: 2학년 희망직무: 개발 관심 자격증: 없음 취득 자격증: 없음 목적: 직무 관련 자격증 추천</code>       | <code>[자격증명: 데이터분석준전문가(ADsP)] 자격증명: 데이터분석준전문가(ADsP) \| 유형: 국가민간자격 \| 분야: 정보기술 \| NCS분류: 정보통신 \| 시행기관: (재)한국데이터진흥원 \| 등급: 1 \| 관련전공: 모바일시스템공학과, 모바일융합공학과, 전자공학부모바일공학전공, 전자정보공학부, IT융합학부</code> | <code>[자격증명: 측량및지형공간정보기사] 자격증명: 측량및지형공간정보기사 \| 유형: 국가기술자격 \| 분야: 정보기술 \| NCS분류: 정보통신 \| 시행기관: 한국산업인력공단 \| 등급: 기사 \| 관련전공: 지리학과, 지리학과(자연계열), 지적학전공, 지적학과, 위치정보시스템학과</code> |
* Loss: [<code>TripletLoss</code>](https://sbert.net/docs/package_reference/sentence_transformer/losses.html#tripletloss) with these parameters:
  ```json
  {
      "distance_metric": "TripletDistanceMetric.COSINE",
      "triplet_margin": 0.2
  }
  ```

### Training Hyperparameters
#### Non-Default Hyperparameters

- `per_device_train_batch_size`: 16
- `per_device_eval_batch_size`: 16
- `num_train_epochs`: 1
- `multi_dataset_batch_sampler`: round_robin

#### All Hyperparameters
<details><summary>Click to expand</summary>

- `do_predict`: False
- `eval_strategy`: no
- `prediction_loss_only`: True
- `per_device_train_batch_size`: 16
- `per_device_eval_batch_size`: 16
- `gradient_accumulation_steps`: 1
- `eval_accumulation_steps`: None
- `torch_empty_cache_steps`: None
- `learning_rate`: 5e-05
- `weight_decay`: 0.0
- `adam_beta1`: 0.9
- `adam_beta2`: 0.999
- `adam_epsilon`: 1e-08
- `max_grad_norm`: 1
- `num_train_epochs`: 1
- `max_steps`: -1
- `lr_scheduler_type`: linear
- `lr_scheduler_kwargs`: None
- `warmup_ratio`: None
- `warmup_steps`: 0
- `log_level`: passive
- `log_level_replica`: warning
- `log_on_each_node`: True
- `logging_nan_inf_filter`: True
- `enable_jit_checkpoint`: False
- `save_on_each_node`: False
- `save_only_model`: False
- `restore_callback_states_from_checkpoint`: False
- `use_cpu`: False
- `seed`: 42
- `data_seed`: None
- `bf16`: False
- `fp16`: False
- `bf16_full_eval`: False
- `fp16_full_eval`: False
- `tf32`: None
- `local_rank`: -1
- `ddp_backend`: None
- `debug`: []
- `dataloader_drop_last`: False
- `dataloader_num_workers`: 0
- `dataloader_prefetch_factor`: None
- `disable_tqdm`: False
- `remove_unused_columns`: True
- `label_names`: None
- `load_best_model_at_end`: False
- `ignore_data_skip`: False
- `fsdp`: []
- `fsdp_config`: {'min_num_params': 0, 'xla': False, 'xla_fsdp_v2': False, 'xla_fsdp_grad_ckpt': False}
- `accelerator_config`: {'split_batches': False, 'dispatch_batches': None, 'even_batches': True, 'use_seedable_sampler': True, 'non_blocking': False, 'gradient_accumulation_kwargs': None}
- `parallelism_config`: None
- `deepspeed`: None
- `label_smoothing_factor`: 0.0
- `optim`: adamw_torch_fused
- `optim_args`: None
- `group_by_length`: False
- `length_column_name`: length
- `project`: huggingface
- `trackio_space_id`: trackio
- `ddp_find_unused_parameters`: None
- `ddp_bucket_cap_mb`: None
- `ddp_broadcast_buffers`: False
- `dataloader_pin_memory`: True
- `dataloader_persistent_workers`: False
- `skip_memory_metrics`: True
- `push_to_hub`: False
- `resume_from_checkpoint`: None
- `hub_model_id`: None
- `hub_strategy`: every_save
- `hub_private_repo`: None
- `hub_always_push`: False
- `hub_revision`: None
- `gradient_checkpointing`: False
- `gradient_checkpointing_kwargs`: None
- `include_for_metrics`: []
- `eval_do_concat_batches`: True
- `auto_find_batch_size`: False
- `full_determinism`: False
- `ddp_timeout`: 1800
- `torch_compile`: False
- `torch_compile_backend`: None
- `torch_compile_mode`: None
- `include_num_input_tokens_seen`: no
- `neftune_noise_alpha`: None
- `optim_target_modules`: None
- `batch_eval_metrics`: False
- `eval_on_start`: False
- `use_liger_kernel`: False
- `liger_kernel_config`: None
- `eval_use_gather_object`: False
- `average_tokens_across_devices`: True
- `use_cache`: False
- `prompts`: None
- `batch_sampler`: batch_sampler
- `multi_dataset_batch_sampler`: round_robin
- `router_mapping`: {}
- `learning_rate_mapping`: {}

</details>

### Framework Versions
- Python: 3.12.12
- Sentence Transformers: 5.2.3
- Transformers: 5.0.0
- PyTorch: 2.10.0+cu128
- Accelerate: 1.12.0
- Datasets: 4.0.0
- Tokenizers: 0.22.2

## Citation

### BibTeX

#### Sentence Transformers
```bibtex
@inproceedings{reimers-2019-sentence-bert,
    title = "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks",
    author = "Reimers, Nils and Gurevych, Iryna",
    booktitle = "Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing",
    month = "11",
    year = "2019",
    publisher = "Association for Computational Linguistics",
    url = "https://arxiv.org/abs/1908.10084",
}
```

#### TripletLoss
```bibtex
@misc{hermans2017defense,
    title={In Defense of the Triplet Loss for Person Re-Identification},
    author={Alexander Hermans and Lucas Beyer and Bastian Leibe},
    year={2017},
    eprint={1703.07737},
    archivePrefix={arXiv},
    primaryClass={cs.CV}
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->