# Contrastive Embedding 학습 데이터

추천형 vector retrieval 정밀도 향상을 위한 contrastive fine-tuning용 데이터·스키마.

## 스키마

- **ContrastiveSample**: `query`, `positive_qual_ids`, `hard_negative_qual_ids`, `sample_id`, `query_slots`
- **ContrastiveTriplet**: `query`, `positive_qual_id`, `negative_qual_id` (pairwise loss용)

## 데이터 생성

```bash
uv run python scripts/build_contrastive_dataset.py \
  --golden path/to/reco_golden.jsonl \
  --out data/contrastive_train.jsonl \
  --triplet-out data/contrastive_triplets.jsonl \
  --max-hard-negatives 5
```

- reco golden JSONL: `query_text`, `gold_ranked` (cert_name, relevance) 필드 필요.
- Hard negative 규칙: positive와 같은 main_field/ncs_large를 가진 다른 자격증 우선.

## 데이터 품질 점검

생성 후 품질 검증 권장:

```bash
uv run python scripts/validate_contrastive_dataset.py \
  --samples data/contrastive_train.jsonl \
  --triplets data/contrastive_triplets.jsonl \
  --preview 5 \
  --report data/contrastive_quality_report.txt
```

- sample/triplet 수, query당 positive/negative 수, 중복 여부 확인.
- preview로 사람 검토용 샘플 출력.
- Hard negative 타당성: 동일 main_field/ncs_large 기반은 "같은 분야 다른 자격"으로 적절한지 검토.

## 학습 진입점 (Entry point)

필요 인자 및 포맷:

- **입력**: `contrastive_triplets.jsonl` (또는 samples에서 생성한 triplet 리스트).
- **한 줄**: `{"query": str, "positive_qual_id": int, "negative_qual_id": int, "sample_id": str|null}`.
- **텍스트 확보**: query는 그대로 사용; positive/negative는 DB 또는 dense_content에서 qual_id로 문서 텍스트 조회 후 사용.
- **권장 loss**: `MultipleNegativesRankingLoss` 또는 `TripletLoss` (sentence-transformers).
- **모델**: 기존 임베딩 모델(예: text-embedding-3-small)과 호환되는 차원으로 fine-tune 시 서비스 교체 가능.

실제 학습 루프는 Colab/로컬에서 별도 구현. 이 데이터로 sentence-transformers 등 contrastive fine-tuning 실행 가능.

## Future work

- Retrieval 실패 사례 기반 hard negative mining: 상위에 나온 오답 qual_id를 negative 후보로 추가하면 더 강한 contrast 학습 가능.
