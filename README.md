# receipt-calculator-project

> **3줄 요약**
> 1. OCR로 추출된 비정형 영수증 텍스트를 매장별 규칙(Store KB)을 통해 구조화된 데이터로 변환합니다.
> 2. 할인 및 쿠폰 정보를 상품 단위로 정확히 귀속시키는 Semantic 해석 과정을 거쳐 공통 상품 객체를 생성합니다.
> 3. 상품별 인원 할당 기반의 정산 엔진과 데이터 정합성 검증(Validation)을 포함한 Full-Pipeline을 제공합니다.

---

## 1. 프로젝트 개요
본 프로젝트는 단순한 OCR 텍스트 정리를 넘어, 매장마다 상이한 영수증 포맷을 분석하고 **할인 정보의 정확한 상품 귀속** 및 **금액 정합성 검증**을 통해 신뢰할 수 있는 상품 단위 정산 데이터를 구축하는 시스템입니다. 현재 Costco, Emart, 하나로마트의 포맷을 안정적으로 지원합니다.

---

## 2. 서비스 로직 (Pipeline)
사용자 촬영부터 최종 정산 출력까지의 단계별 역할 분리(Separation of Concerns)를 지향합니다.

1. **OCR / Layout Reconstruction**: 좌표 기반 줄 정렬 및 토큰 병합으로 원문 `line_text` 복원
2. **Store Detector**: 헤더 정보를 바탕으로 매장(Costco, Emart, Hanaro) 자동 판별
3. **Parser (KB 기반 구조화)**: Store KB를 참조하여 라인별 타입 분류 및 핵심 필드 추출
4. **Semantic Interpreter (의미 해석)**: 상품명-상세-할인 라인을 하나의 상품 객체로 결합 및 할인 귀속
5. **Canonical Schema Normalization**: 매장과 무관한 공통 상품 객체(Standard Item) 생성
6. **Validation**: 산술 연산 및 구조적 결함 여부 검증 (Total, Qty, Price check)
7. **Settlement Engine**: 상품별 참여자 선택에 따른 인원별 정산 금액 분배 및 UI 출력

---

## 3. 핵심 설계 정책

### 3.1 분석 종료 및 유효성 정책
* **신뢰 구간 한정**: 종료 키워드(합계, 부가세, 과세, 면세 등)가 확인되지 않는 영수증은 불완전 입력으로 간주하여 오검출을 방지합니다.
* **Tail 영역 분리**: 종료 키워드 이후에 나타나는 결제 승인, 안내문, 잔돈 등의 라인은 분석 대상에서 제외하여 데이터 노이즈를 최소화합니다.

### 3.2 상품명 및 수량 추출 정책
* **소거법 판별**: 상세, 할인, 합계, 노이즈 등 정의된 타입을 제외한 나머지 라인을 상품명으로 간주합니다.
* **수량(Qty) 엄격 모드**: 상품명 내부에 포함된 숫자(예: 4PK, 500G)는 구매 수량으로 오인하지 않도록 하며, 반드시 상세 라인의 구조화된 필드에서만 수량을 추출합니다.

### 3.3 할인 매칭 정책 (Location-based)
* **위치 기반 귀속**: 할인 상품명은 OCR 오인식이 잦으므로 문자열 매칭 대신, **가장 가까운 이전 상품(Item) 또는 명시적 타겟 라인**에 귀속시키는 위치 기반 로직을 최우선합니다.

---

## 4. 프로젝트 구조
```text
receipt-calculator-project/
├── receipt_parser/         # Line 단위 Parsing 및 구조화 모듈
│   ├── store_rules/        # 매장별 패턴(Regex) 및 키워드 정의
│   ├── field_extractor.py      # 정규식 기반 필드 추출
│   ├── line_classifier.py      # 라인 타입 분류 로직
│   ├── normalizer.py           # 텍스트 정규화 및 전처리
│   └── parser_pipeline.py      # 파싱 프로세스 제어
├── semantic/               # 문맥 기반 Item 생성 및 할인 귀속 로직
├── validation/             # 금액 및 수량 정합성 검증 모듈
├── data/                   # 단계별 처리 결과 데이터 (Git 제외)
│   ├── raw/ / parsed/ / semantic/ / validation/
├── main.py                 # 시스템 메인 실행부
├── run_pipeline.py         # 전체 파이프라인 제어 스크립트
└── README.md
```

---

## 5. 데이터 규격 예시 (Data Contract)

### Parser Output (구조화)
```json
[
  { "line_idx": 0, "line_text": "유기농 우유", "line_type": "item_name" },
  {
    "line_idx": 1, "line_text": "650635 1 9590 9,590",
    "line_type": "item_detail", "code": "650635", "qty": 1, "price_raw": "9,590"
  },
  { "line_idx": 4, "line_text": "11816 1 1800 1,800-", "line_type": "discount_detail", "discount_raw": "1,800-" }
]
```

### Canonical Item (최종 객체)
```json
{
  "name": "유기농 우유",
  "qty": 1,
  "base_price": 9590,
  "discount": 1800,
  "final_price": 7790
}
```

---

## 6. 보안 및 운영 방침
* **개인정보 보호**: 실제 영수증 이미지 및 결과 데이터(`data/` 폴더)는 개인정보 포함 가능성을 고려하여 Repository에 포함하지 않으며, 로직과 규격 중심의 코드를 관리합니다.
* **오류 대응**: `qty * unit_price != total_price` 등 정합성 오류 탐지 시 사용자에게 즉시 알림을 제공하거나 재촬영을 유도합니다.
