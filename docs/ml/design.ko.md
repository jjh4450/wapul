# 설계

블럭 분할 모델의 설계와 근거가 된 연구입니다. 구성 요소를 바꾸거나 더할 때 이 문서의 상태 표와 결과 표를 함께 고칩니다. 실험별 설정과 전체 수치는 [실험 기록](experiments.md)에 있습니다.

## 서비스가 정한 조건

기획서(`data/docs/`의 PS 공부 기록 사이트 기획서)와 그 뒤의 결정에서 모델에 걸리는 조건입니다.

- **출력은 종류와 "로직 n"까지입니다.** 블럭 이름은 만들지 않습니다.
- **잘못 자르기와 잘못 합치기를 같은 무게로 봅니다.** 고르는 값은 같은 블럭 쌍 F1로 정합니다([실험 12](experiments.md)).
- **완벽한 분할이 목표가 아닙니다.** 사용자가 블럭을 고칠 수 있습니다.
- **추론은 CPU에서 돕니다.** 풀이 길이에 따라 비용이 제곱으로 늘어나는 구성은 쓰지 않습니다.
- 경계 질문(조건, 비교)과 구조 질문(재귀, 반복)을 붙일 블럭은 모델이 아니라 정적 분석이 고릅니다. wapul-seg의 `segment()`가 문장마다 `condition`, `loop`, `recursion`을 붙이고, `blockTags()`가 블럭 단위로 모읍니다(`js/src/tags.ts`).

## 문제를 두 개의 알려진 문제로 본다

| 우리 단계 | 같은 구조의 문제 | 이유 |
|-----------|------------------|------|
| 종류 분류 | 문장 분류 (CodeSeg) | 문장마다 4개 중 하나. 학습 예시가 문장 수(6,435개)만큼 있음 |
| 블럭 묶기 | 대화 분리(conversation disentanglement), 상호참조 해결 | 앞에서부터 읽으며 "기존 묶음에 붙일지, 새로 열지"를 정하고, 묶음이 떨어져 있을 수 있음 |

검토된 풀이의 42%에 떨어진 로직 블럭이 있습니다. logic 문장만 순서대로 보면 블럭의 81%는 이어져 있지만, 이어진 구간만 자르는 방식은 나머지 19%를 표현하지 못하고 경계 판단도 더 낫지 않았습니다([실험 14](experiments.md)). 그래서 떨어진 블럭을 그대로 다루는 방식을 씁니다.

## 구성 요소와 상태

| 구성 요소 | 근거 | 상태 |
|-----------|------|------|
| 정규화 + tree-sitter 문장 단위 | 라벨이 이 단위로 만들어짐 | 적용 (`normalize.py`, `units.py`) |
| 종류 분류: 문장과 앞뒤 3문장의 토큰, 감싸는 제어문·함수 머리, AST 사실을 특징으로 LightGBM | CodeSeg의 맥락 붙이기 | 적용 (`features/kind_features.py`, `models/kind_lgbm.py`) |
| 종류 특징: 식별자의 글자 3·4-gram | 학습하지 않은 언어의 입출력 관용구 | 적용 (`with_ngrams`, [실험 23](experiments.md)). Rust를 학습 없이 지원 |
| 종류 특징: 저장소 5곳 이상에 나온 것만 | 한 저장소에만 나오는 특징은 일반화되지 않고 모델만 키움 | 적용 (`common_features`, [실험 24](experiments.md)) |
| 종류 특징: 문자열 리터럴은 내용 대신 `""` | 리터럴 내용은 문제마다 달라 일반화되지 않음 | 적용 (`LITERALS`, [실험 25](experiments.md)) |
| 종류 분류: 앞뒤 3문장 맥락을 붙인 입력으로 CodeBERT 미세조정 | CodeSeg | `segmenter-v1`에만: LightGBM과 점수가 같고 크기와 CPU 시간이 수백 배 ([실험 22](experiments.md), `models/kind_classifier.py`) |
| 블럭 특징: 데이터 흐름 사슬, 제어문 덩어리, 같은 문법 유형 + 거리, 깊이 | SEGMENT | 적용 (`features/unit_ast.py`) |
| 블럭 묶기: logic 문장마다 지금까지 만든 블럭 중 하나 또는 새 블럭을 고름 | 대화 분리, 군집 순위(cluster ranking) | 적용 (`features/candidates.py`, `models/block_ranker.py`, 블럭 단위) |
| 블럭 점수기: LightGBM LambdaRank | LambdaRank | 적용 |
| 블럭 점수기: 작은 MLP(softmax, 정답 후보 확률 합 최대화) + LightGBM의 확률 평균 | Lee 외 2017 | `segmenter-v1`에만: LightGBM만 쓸 때보다 B³ 0.007 높지만 잡음 안이고, v2는 런타임을 하나로 둠 |
| 최종 모델 묶음과 예측 | — | 적용 (`wapul_ml/models/segmenter.py`, 저장은 `models/segmenter-v3/`). 이전 버전은 고정된 `segmenter_v1.py`, `segmenter_v2.py`로 읽음 |
| 쌍 "같은 블럭?" 분류(RBF SVM) + α 임계값 + 순서대로 붙이기 | 상호참조 점진적 군집 | 비교 기준으로 남김 (`models/baseline.py`, `notebooks/baseline_cv.py`) |
| 문장 임베딩(E5 등) | SetFit의 linear probe | 제외: 블럭 묶기에 기여 없음, 종류 분류는 문자열 특징 LightGBM이 더 높음 |
| 임베딩 미세조정(SetFit, TSDAE, E5 쌍 점수기) | SetFit, TSDAE | 제외: 블럭 묶기가 오르지 않거나 떨어짐 |
| CodeBERT로 문장 쌍을 함께 읽는 블럭 점수기 | 대화 분리의 BERT 쌍 점수기 | 제외: AST MLP보다 높지 않고 CPU 비용이 logic 문장 수의 제곱 |
| 문장 모양(AST 잎 토큰) 유사도, 사용자 함수 호출 관계 | 오류 분석 | 제외: 라벨에서 같은 블럭 신호가 약하고 점수 차이가 잡음 안([실험 20, 21](experiments.md)) |
| 이어진 구간 경계 찍기 | CodeSeg의 범위 묶기, 텍스트 분할 | 제외: 떨어진 블럭 19%를 표현 못 함 |
| 스코프를 구분한 def-use 연결 (가장 최근 정의 → 사용) | SEGMENT의 데이터 흐름 사슬 | 제외: 이름만 같아 생긴 잘못된 연결은 잘못 합친 쌍의 1.5%에만 걸림([실험 18](experiments.md)) |
| 평가: B³, CEAF-e | 상호참조 평가 | 적용 (`evaluation/metrics.py`) |

## 현재 결과

사람이 검토한 풀이 300건(6,435문장)에 대한 5-fold 교차 검증입니다. 블럭 묶기는 정답 종류를 준 상태에서 logic 문장만 묶은 점수입니다. 300건에서는 B³ 약 0.018, 쌍 F1 약 0.040 미만의 차이를 확정할 수 없습니다.

**최종 모델** (`segmenter-v3`)

| 대상 | 점수 |
|------|------|
| 종류 macro-F1 | 0.902 (학습하지 않은 Rust 12개: 특징을 줄이기 전 0.870) |
| 블럭 묶기 B³ / CEAF-e | 0.809 / 0.732 |
| 같은 블럭 쌍 정밀도 / 재현율 / F1 | 0.654 / 0.682 / 0.668 |
| 모델 크기 | 7.8MB (종류 트리 6.8MB, 특징 이름 0.4MB, 블럭 트리 0.5MB) |
| CPU 추론, 풀이 하나 (4스레드, 중앙값 / 최대) | 0.00초 / 0.01초 |

- 이 구성 그대로의 전체(end to end) 점수는 아직 없습니다. 블럭 묶기가 SVM + α 군집일 때 전체 B³는 0.830이었습니다.
- CPU 시간은 Ryzen 9 9900X에서 `segmenter-v2`로 잰 값입니다.

**비교 기준** (블럭 묶기, 정답 종류)

| 기준 | B³ | 쌍 F1 |
|------|----|-------|
| 전부 한 블럭 | 0.485 | 0.349 |
| 쌍 + α 군집 (`notebooks/baseline_cv.py`) | 0.793 | 0.630 |
| `segmenter-v1` (MLP + LightGBM) | 0.816 | 0.678 |
| **최종 모델** (LightGBM) | **0.809** | **0.668** |

## 근거

**CodeSeg** — 코드를 기능 단위 블럭으로 나누는 가장 가까운 선행 연구. 줄마다 앞뒤 줄을 맥락으로 붙여 분류하는 방식이 범위를 통째로 뽑는 방식보다 나았고, 미세조정한 CodeBERT·CodeT5+가 LLM보다 정확했습니다. 방법만 가져와 종류 분류에 씁니다. 같은 범주가 연속된 줄을 묶을 뿐이라 떨어진 블럭은 다루지 않습니다.
[논문](https://dl.acm.org/doi/10.1145/3820755.3821483) · [코드](https://github.com/Dahouabdelhalim/CodeSeg)

**대화 분리** — 여러 대화가 섞인 채팅에서 메시지마다 "앞의 어느 메시지에 대한 답인가(없으면 자기 자신)"를 골라 대화를 나눕니다. 손으로 만든 특징 + 작은 신경망이 강한 기준선이었습니다. 우리는 메시지를 logic 문장, 대화를 블럭으로 보고 같은 형식을 씁니다.
[Kummerfeld 외 2019](https://aclanthology.org/P19-1374/)

**군집 순위와 정답 후보 확률 합** — 상호참조에서 표현 하나를 앞 표현 하나가 아니라 지금까지의 군집과 비교하는 방식(cluster ranking)이 군집 단위 특징을 쓸 수 있어 더 나았습니다. 정답 후보가 여럿이면 그 확률의 합을 최대화합니다.
[Clark & Manning 2016](https://aclanthology.org/P16-1061/) · [Lee 외 2017](https://aclanthology.org/D17-1018/)

**LambdaRank** — 각 logic 문장의 후보들을 질의 하나로 봅니다.
[Burges 2010](https://www.microsoft.com/en-us/research/publication/from-ranknet-to-lambdarank-to-lambdamart-an-overview/)

**SEGMENT** — 메서드 코드를 "의미 있는 블럭"으로 나누는 규칙 기반 도구. 블럭을 데이터 흐름 사슬, 제어문 덩어리, 같은 문법 유형의 연속으로 봅니다. 블럭 점수기의 특징입니다.
[Wang 외 2011](https://pdfs.semanticscholar.org/eae0/a9d1a3df1be559af97a8885056a8b85300c5.pdf)

**평가 지표** — B³와 CEAF는 상호참조 평가의 표준입니다. MUC는 한 원소짜리 군집을 무시하고 군집을 적게 만들수록 유리하며, 단순 Rand 지수는 1 근처로 몰려 차이를 잘 보여 주지 못합니다.
[Cai & Strube 2010](https://aclanthology.org/W10-4305.pdf) · [BLANC](https://www.cs.cmu.edu/~hovy/papers/10BLANC-coref-metric.pdf)

**하위목표 학습** — 코드 예제를 기능 단위(하위목표)로 묶어 보여 주면 학습에 도움이 됩니다. CodeTree는 학습자 몇 명의 묶음을 모아 만들고, AlgoSolve는 알고리즘 풀이의 하위목표 라벨을 학습자가 쓰고 비교하게 합니다. 우리 모델은 묶음을 자동으로 만들고, 설명은 사용자가 씁니다.
[학습자 묶음으로 하위목표 계층 만들기 (CodeTree의 선행 연구)](https://ceur-ws.org/Vol-3410/short4.pdf) · [AlgoSolve](https://algosolve.kixlab.org/)

## 순서

`segmenter-v2`는 모델 경량화 실험의 결과로 고정합니다. 다음 버전은 배포 실험입니다.

1. `segmenter-v3`: 다른 시스템이 WASM 하나로 모델을 쓰게 하는 배포 실험. 구성과 결정은 [배포](deploy.md)에 있습니다
2. 최종 모델 구성 그대로 전체(end to end) 점수 재기
3. 라벨 늘리기: LLM 초안을 학습 데이터로 쓰는 방안을 검토
