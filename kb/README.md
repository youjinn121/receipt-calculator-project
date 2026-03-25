# Receipt Parser Knowledge Base (KB)

이 디렉토리는 영수증 OCR 결과를 구조화하기 위한 규칙 기반 Knowledge Base(KB)를 정의한다.

본 시스템은 Parser와 Semantic Interpreter를 분리한 구조를 기반으로 동작한다.

---

# 시스템 처리 흐름

OCR
→ Line Reconstruction
→ Parser (구조 추출)
→ Semantic Interpreter (의미 해석)
→ Canonical Schema
→ Settlement
→ Frontend

---

# 디렉토리 구조

kb/
  common/
    line_types.json
    normalization_rules.json
    parser_pipeline_guide.json

  costco/
    roles_map.json
    item_patterns.json
    discount_patterns.json
    summary_patterns.json
    noise_patterns.json
    policies.json
    keyword_aliases.json

  emart/
    roles_map.json
    item_patterns.json
    discount_patterns.json
    summary_patterns.json
    noise_patterns.json
    policies.json
    keyword_aliases.json

  hanaro/
    roles_map.json
    item_patterns.json
    discount_patterns.json
    summary_patterns.json
    noise_patterns.json
    policies.json
    keyword_aliases.json

---

# 설계 원칙

## 1. Parser와 Semantic 역할 분리

Parser:
- 텍스트를 구조화된 데이터로 변환
- line_type 분류
- 필드 추출 (code, qty, price 등)
- normalization 적용

Semantic Interpreter:
- 할인 → 상품 연결
- 상품 객체 생성
- 가격 계산
- canonical schema 변환

---

## 2. Parser 책임 범위

Parser는 다음만 수행한다:

- line_type 분류
- code, qty, unit_price_raw, price_raw 추출
- normalization 적용

Parser가 하지 않는 것:

- 할인 귀속
- 상품 생성
- 가격 계산
- 의미 해석

---

## 3. Semantic Interpreter 책임

- discount → item 연결
- 상품 단위 객체 생성
- base_price / discount / final_price 계산
- 정산용 데이터 생성

---

# Common KB 설명

## line_types.json

파서 출력 타입 정의

가능한 값:

- item_name
- item_detail
- discount_detail
- receipt_discount
- subtotal
- total
- noise

모든 라인은 반드시 위 타입 중 하나로 분류되어야 한다.

---

## normalization_rules.json

OCR 결과 정규화 규칙

주요 기능:

- 공백 정리
- 숫자 내부 공백 제거
- 콤마/점 금액 표기 통일
- prefix 제거 (*, 상품번호 등)
- qty 보정 (누락 시 1)
- OCR 키워드 보정

정규화는 문자열 복원까지만 수행하며 의미 해석은 하지 않는다.

---

## parser_pipeline_guide.json

파서 처리 흐름 정의

1. 공통 normalization 적용
2. 스토어별 normalization override 적용
3. line_type 분류
4. 필드 추출
5. 숫자 casting
6. parser output 생성

---

# Store KB 구조

각 스토어는 동일한 구조를 가진다.

## roles_map.json
스토어 역할 → 공통 line_type 매핑

예:
discount_keyword → discount_detail

---

## item_patterns.json
상품명 및 상품 상세 패턴 정의

---

## discount_patterns.json
할인 관련 패턴 정의

- 할인 키워드
- 할인 대상
- 할인 금액 패턴

---

## summary_patterns.json
소계, 합계, 종료 구간 정의

---

## noise_patterns.json
무시할 라인 정의

- 헤더
- 내부 코드
- 판매자 정보
- 세금 라인

---

## policies.json
후처리 정책

- qty 보정
- 동일 상품 merge
- 할인 중복 제거

---

## keyword_aliases.json
OCR 오인식 키워드 보정

예:
- 제대상금액 → 결제대상금액
- 끝 전할 인 → 끝전할인

---

# 핵심 개념

## Raw vs Canonical

스토어별 원문 구조는 다르지만,
최종 데이터 구조는 동일하다.

Canonical 구조:

{
  "code": "...",
  "qty": 1,
  "unit_price": 9590,
  "total_price": 9590
}

---

# 중요 규칙

- KB는 패턴 정의만 담당한다
- Parser는 구조만 추출한다
- Semantic은 의미를 해석한다

---

# 한 줄 정의

이 KB는 영수증 데이터를 "줄 → 구조 → 의미"로 변환하기 위한 규칙 집합이다.