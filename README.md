# Receipt Calculator Project

 1. CLOVA OCR로 추출된 비정형 영수증 데이터를 좌표 기반으로 정렬하고, 유통사별(Costco, Emart, Hanaro) 규칙을 통해 **상품 단위 데이터로 구조화**합니다.
 2. 상품명, 수량, 단가, 할인, 최종 금액을 공통 Item Schema로 변환하고, **Validation으로 금액 정합성**을 검증합니다.
 3. 검증을 통과한 데이터에 한해 **LLM 기반 카테고리 정규화**를 적용하여 장바구니 소비 분석에 활용 가능한 데이터로 변환합니다.


## Pipeline Architecture

```mermaid
graph LR
    A[Receipt Image] --> B[CLOVA OCR]
    B --> C[OCR Preprocessing]
    C --> D[Receipt Parser]
    D --> E[Semantic Interpreter]
    E --> F{Validation}
    F -->|Pass| G[LLM Category Normalization]
    F -->|Fail| H[Error Analysis / Recapture]
    G --> I[Basket Analytics]
````

1. **OCR Preprocessing**
   CLOVA OCR 결과의 bounding box 좌표를 기반으로 텍스트를 라인 단위로 정렬하고 보정합니다.

2. **Parser & Semantic Interpreter**
   OCR 라인을 `item_name`, `item_detail`, `discount_detail`, `total` 등으로 분류한 뒤, 상품명, 수량, 단가, 할인 정보를 하나의 상품 객체로 병합합니다.

3. **Validation**
   `단가 × 수량`, `할인 반영 금액`, `영수증 총합`을 기준으로 상품 단위 및 영수증 단위 금액 정합성을 검증합니다. 잘못된 데이터가 소비 분석으로 전파되는 것을 차단하는 품질 게이트 역할을 합니다.

4. **LLM Category Normalization**
   전체 파싱을 LLM에 맡기지 않고, Validation을 통과한 구조화 데이터에 대해서만 카테고리 정규화를 수행합니다.


## How to Run

본 프로젝트는 목적에 따라 배치 처리, LLM 카테고리 정규화, 평가 스크립트를 분리하여 실행합니다.

### 1. Parser, Semantic, Validation 실행

`data/raw`의 OCR JSON 파일을 읽어 Parser, Semantic Interpreter, Validation 단계까지 일괄 처리합니다.

```bash
python run_pipeline.py
```

```text
data/raw
→ data/parsed
→ data/semantic
→ data/validation
```

### 2. LLM Category Normalization 실행

`data/validation`에서 `is_valid=True`로 검증된 파일만 대상으로 LLM 기반 카테고리 정규화를 수행합니다.

```bash
python run_llm_category.py
```

```text
data/semantic + data/validation
→ data/categorized
```

### 3. Evaluation 실행

`evaluation/` 폴더의 스크립트를 통해 구조화, Validation, 카테고리 정규화 결과를 평가합니다.
평가 결과는 `evaluation/results/`에 저장됩니다.

```bash
python -m evaluation.evaluate_structure
python -m evaluation.evaluate_validation
python -m evaluation.evaluate_category
```

### 4. Backend 연동용 Pipeline

`pipeline_runner.py`는 Backend/API 서비스에서 단일 영수증 객체를 처리하기 위한 모듈입니다.
파일 저장을 수행하지 않고, 입력 객체에 대해 `parsed`, `semantic`, `validation` 결과를 반환합니다.

```text
Receipt Object
→ parsed
→ semantic
→ validation
```


## Project Structure

```text
receipt-calculator-project/
├── frontend/                # Android 클라이언트 앱 모듈
├── backend/                 # FastAPI 기반 API 및 DB 연동
├── ocr_preprocess/          # OCR bounding box 기반 라인 정렬 및 위치 보정
├── receipt_parser/          # Line type 분류 및 핵심 필드 추출
├── semantic/                # 상품 객체 생성 및 할인 귀속 로직
├── validation/              # 상품 및 영수증 단위 금액 정합성 검증
├── llm/                     # LLM 기반 카테고리 정규화
├── evaluation/              # 파이프라인 단계별 성능 평가
│   └── results/             # 최종 평가 결과 CSV/JSON
├── data/                    # 단계별 입출력 데이터
├── run_pipeline.py          # Parser ~ Validation 배치 실행
├── run_llm_category.py      # LLM Category 정규화 실행
└── pipeline_runner.py       # Backend 연동용 단일 영수증 처리 모듈
```


## Output Example

LLM 카테고리 정규화까지 완료된 최종 상품 객체 예시는 다음과 같습니다.

```json
{
  "name": "KS VFGFTARLE 5 5",
  "name_source": "item_name+item_detail",
  "code": "666853",
  "qty": 1,
  "unit_price": 18990,
  "base_price": 18990,
  "discount": 0,
  "final_price": 18990,
  "discount_meta": [],
  "source_line_indices": [4],
  "category": "기타",
  "category_meta": {
    "method": "llm",
    "allowed_categories": [
      "식재료",
      "간편식",
      "간식",
      "음료",
      "주류",
      "생활용품",
      "기타",
      "Uncategorized"
    ],
    "use_llm": true,
    "use_cache": false,
    "cache_hit": false
  }
}
```


## Evaluation

주요 평가 항목은 다음과 같습니다.

* 구조화 성공률
* Validation 통과율
* Item-level Validation 성공률
* Category Strict Accuracy
* Category Allowed Accuracy
* Uncategorized Rate
* Effective Error Rate

평가 결과 파일은 `evaluation/results/`에 저장됩니다.


## Security Notes

실제 영수증 원본 이미지, API Key, 개인정보가 포함될 수 있는 로컬 데이터, 캐시 파일, archive 폴더는 Git 추적 대상에서 제외합니다.
