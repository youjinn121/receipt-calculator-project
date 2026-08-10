import json
import csv
import re
from pathlib import Path
from collections import Counter, defaultdict


BEFORE_ROOT = Path("data/categorized_before_kan")
AFTER_ROOT = Path("data/categorized")

OUTPUT_DIFF_JSON = Path("category_diff_result.json")
OUTPUT_REVIEW_JSON = Path("category_diff_review.json")
OUTPUT_REVIEW_CSV = Path("category_diff_review.csv")


CORE_CATEGORIES = {"식재료", "간편식", "간식", "음료", "주류"}
SUPPORT_CATEGORIES = {"생활용품", "기타", "반려동물", "Uncategorized"}


def normalize_category(category: str) -> str:
    if category == "반려동물":
        return "기타"
    return category or "Uncategorized"


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", "", name or "").lower()


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def collect_json_files(root: Path):
    return sorted(root.rglob("*.json"))


def get_relative_key(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("/", "\\")


def get_items(data: dict):
    items = data.get("items", [])
    if not isinstance(items, list):
        return []
    return items


def get_category(item: dict) -> str:
    return (
        item.get("category")
        or item.get("primary_category")
        or item.get("llm_category")
        or item.get("category_primary")
        or "Uncategorized"
    )


def make_item_key(item: dict, index: int):
    """
    동일 파일 내 동일 상품명이 반복될 수 있으므로 index 기반으로 비교한다.
    """
    return index


def classify_change(before_category: str, after_category: str) -> str:
    before_norm = normalize_category(before_category)
    after_norm = normalize_category(after_category)

    if before_category == "반려동물" and after_norm == "기타":
        return "policy_change_pet_to_etc"

    if before_norm == after_norm:
        return "support_category_changed"

    if before_norm in CORE_CATEGORIES or after_norm in CORE_CATEGORIES:
        return "core_category_changed"

    return "support_category_changed"


def recommend_gt(name: str, before: str, after: str):
    """
    diff 해석용 권장 GT.
    핵심은 '상품명 하드코딩'이 아니라 상품군 기준으로 정상 변경/오분류/애매를 분리하는 것.
    """
    raw = name or ""
    n = normalize_name(raw)

    before_norm = normalize_category(before)
    after_norm = normalize_category(after)

    # 1. 정책 변경: 반려동물 제거
    if before == "반려동물" or any(k in n for k in ["반려", "강아지", "고양이", "껌1kg"]):
        return {
            "final_gt": "기타",
            "basis_group": "policy_pet_to_etc",
            "judgement": "정상 기준 변경",
            "reason": "반려동물 카테고리를 별도 유지하지 않고 기타로 통합한 기준 변경",
        }

    # 2. 우유류: 본 연구 기준에서 음료
    if "우유" in n or "밀크" in n or "굿밀크" in n:
        # 생크림은 우유 음료가 아니라 조리/제과용 유제품으로 봄
        if "생크림" in n:
            return {
                "final_gt": "식재료",
                "basis_group": "dairy_ingredient",
                "judgement": "프롬프트 오류",
                "reason": "생크림은 액상 음용 우유가 아니라 조리/제과용 유제품이므로 식재료",
            }

        # 치즈/버터는 식재료
        if any(k in n for k in ["치즈", "버터"]):
            return {
                "final_gt": "식재료",
                "basis_group": "dairy_ingredient",
                "judgement": "프롬프트 오류",
                "reason": "치즈/버터류는 조리·식사용 부재료이므로 식재료",
            }

        return {
            "final_gt": "음료",
            "basis_group": "milk_to_beverage_policy",
            "judgement": "정상 기준 변경",
            "reason": "본 연구 기준에서 일반 우유류는 액상 음용 제품으로 보아 음료로 재매핑",
        }

    # 3. 계란/란
    if any(k in n for k in ["계란", "달걀", "유정란", "동물복지란"]) or re.search(r"란\d|란[0-9]|란[가-힣]*\d", n):
        return {
            "final_gt": "식재료",
            "basis_group": "egg_basic_food",
            "judgement": "프롬프트 오류",
            "reason": "계란/달걀/란은 기본 식품이므로 식재료",
        }

    # 4. 수산물 원물/전처리 수산물
    if any(k in n for k in [
        "새우", "고등", "우렁", "임연수", "생선", "수산류", "수산",
        "황태채", "오징어채", "조미오징어", "건어물", "구운김", "재래김", "돌김", "곱창돌김"
    ]):
        # 회는 바로 섭취 가능 완제품
        if any(k in n for k in ["홍어회", "광어회", "회모둠", "모둠회"]):
            return {
                "final_gt": "간편식",
                "basis_group": "ready_to_eat_seafood",
                "judgement": "정상 기준 변경",
                "reason": "회류는 손질 완료되어 바로 먹는 수산물로 간편식",
            }

        return {
            "final_gt": "식재료",
            "basis_group": "seafood_raw_or_preprocessed",
            "judgement": "프롬프트 오류",
            "reason": "수산물 원물 또는 손질·냉동·건조 수산물은 조리 완료 반찬이 아니면 식재료",
        }

    # 5. 육류: 원재료 vs 반조리/가공육 분리
    if any(k in n for k in ["양념", "훈제", "델리햄", "슬라이스햄", "햄슬라이스", "훈제오리"]):
        # 양념육은 애매하지만 본 연구 기준에서는 반조리 식품으로 간편식 우선
        if "양념" in n:
            return {
                "final_gt": "간편식",
                "basis_group": "marinated_meat_ambiguous",
                "judgement": "애매하지만 새 기준 채택",
                "reason": "양념육은 조리가 필요하지만 조리 부담이 줄어든 반조리 식품으로 보고 간편식 우선 매핑",
            }

        return {
            "final_gt": "간편식",
            "basis_group": "processed_ready_meat",
            "judgement": "정상 기준 변경",
            "reason": "훈제/햄/델리류는 가공·즉시 섭취 단서가 강하므로 간편식",
        }

    if any(k in n for k in [
        "삼겹살", "부채살", "스테이크", "포크립", "포크 립".replace(" ", ""),
        "계육류", "구이용", "볶음탕용", "불고기", "돼지갈비"
    ]):
        return {
            "final_gt": "식재료",
            "basis_group": "meat_raw_ingredient",
            "judgement": "프롬프트 오류" if after_norm != "식재료" else "새 기준 채택",
            "reason": "부위명/구이용/조리 전 육류 원재료는 식재료. 단, 양념/훈제/햄/델리 단서가 있으면 간편식",
        }

    # 6. 샐러드
    if "샐러드" in n:
        if any(k in n for k in ["곡물", "시즌", "2종", "완제품"]):
            return {
                "final_gt": "간편식",
                "basis_group": "ready_made_salad",
                "judgement": "정상 기준 변경",
                "reason": "곡물/시즌/복수 구성 샐러드는 즉석 섭취형 완제품 샐러드로 보고 간편식",
            }

        return {
            "final_gt": "식재료",
            "basis_group": "salad_raw_vegetable",
            "judgement": "기타 허용",
            "reason": "샐러드 단독은 원물/완제품이 애매하므로 문맥 검토 필요",
        }

    # 7. 빵/제과/간식
    if any(k in n for k in [
        "크라상", "크루아상", "베이글", "버터빵", "깜빠뉴", "브레드",
        "비스킷", "샌드", "과자", "쿠키", "약과", "초콜릿", "초코",
        "누텔라", "cemoi", "vicenzi", "firenze", "crisp", "그레이스", "국희"
    ]):
        if any(k in n for k in ["샌드위치", "핫도그", "피자빵"]):
            return {
                "final_gt": "간편식",
                "basis_group": "meal_replacement_bread",
                "judgement": "정상 기준 변경",
                "reason": "샌드위치/핫도그/피자빵은 식사 대체형 조리빵으로 간편식",
            }

        return {
            "final_gt": "간식",
            "basis_group": "snack_bakery_dessert",
            "judgement": "프롬프트 오류" if after_norm != "간식" else "새 기준 채택",
            "reason": "제과·디저트성 빵류/과자/초콜릿/스프레드성 간식은 간식",
        }

    # 8. 요거트/요구르트/발효유
    if any(k in n for k in ["요거트", "요구르트", "비피더스", "엔요"]):
        if any(k in n for k in ["그릭", "무가당", "플레인"]):
            return {
                "final_gt": "식재료",
                "basis_group": "plain_yogurt_ingredient",
                "judgement": "프롬프트 오류",
                "reason": "플레인/그릭/무가당 요거트는 기본 유제품으로 식재료",
            }

        if any(k in n for k in ["생크림", "디저트"]):
            return {
                "final_gt": "간식",
                "basis_group": "dessert_yogurt",
                "judgement": "프롬프트 오류" if after_norm != "간식" else "새 기준 채택",
                "reason": "생크림/디저트 요거트는 유제품 디저트로 간식",
            }

        return {
            "final_gt": "음료",
            "basis_group": "fermented_milk_drink",
            "judgement": "프롬프트 오류" if after_norm != "음료" else "새 기준 채택",
            "reason": "요구르트음료/비피더스/액상 발효유는 음료",
        }

    # 9. 조미료/소스/부재료/유제품 부재료
    if any(k in n for k in [
        "후추", "시즈닝", "솔트", "식초", "드레싱", "소스", "그레이즈",
        "맛기름", "식용유", "스테비아", "감미료", "잼", "본마망",
        "프루츠", "메이플버터", "버터", "치즈", "케이퍼", "생크림"
    ]):
        # 슈가버블은 식품이 아니라 세제 브랜드 가능성이 큼. 아래 생활용품/기타에서 처리
        if "슈가버블" in n:
            return {
                "final_gt": "기타",
                "basis_group": "brand_or_line_ambiguous",
                "judgement": "기타 허용",
                "reason": "브랜드/향 표현 중심이고 식품 용도 단서가 부족하므로 기타 허용",
            }

        return {
            "final_gt": "식재료",
            "basis_group": "seasoning_sauce_ingredient",
            "judgement": "프롬프트 오류" if after_norm != "식재료" else "새 기준 채택",
            "reason": "조미료/소스/식초/감미료/치즈/버터/스프레드류는 조리·식사용 부재료로 식재료",
        }

    # 10. 면류
    if any(k in n for k in ["사리면", "스파게티", "파스타면"]):
        return {
            "final_gt": "식재료",
            "basis_group": "noodle_ingredient",
            "judgement": "정상 기준 변경" if after_norm == "식재료" else "프롬프트 오류",
            "reason": "사리면/파스타면은 조리 전 면 재료로 식재료",
        }

    if any(k in n for k in ["튀김우동", "컵라면", "컵면"]):
        return {
            "final_gt": "간편식",
            "basis_group": "instant_noodle_meal",
            "judgement": "프롬프트 오류" if after_norm != "간편식" else "새 기준 채택",
            "reason": "즉석 조리 면류는 식사 대체형 간편식",
        }

    # 11. 생활용품
    if any(k in n for k in [
        "샴푸", "퍼실", "세제", "딥클린", "칫솔", "리스테린", "토탈케어",
        "구강", "스푼", "국자", "볶음스푼", "키친타월", "랩", "봉투",
        "비닐백", "종량제", "프레스앤씰"
    ]):
        return {
            "final_gt": "생활용품",
            "basis_group": "daily_household_goods",
            "judgement": "프롬프트 오류" if after_norm != "생활용품" else "새 기준 채택",
            "reason": "생활·위생·주방 목적이 상품명에 직접 드러나는 비식품은 생활용품",
        }

    # 12. 주류
    if any(k in n for k in ["테라", "필굿", "필라이트", "하이네켄", "카스후레쉬", "맥주", "소주", "와인", "막걸리", "동동주", "발포주"]):
        # 카스테라 false positive 방지
        if "카스테라" in n:
            return {
                "final_gt": "간식",
                "basis_group": "alcohol_false_positive_food",
                "judgement": "프롬프트 오류",
                "reason": "카스테라는 주류가 아니라 제과류",
            }

        return {
            "final_gt": "주류",
            "basis_group": "alcohol_explicit",
            "judgement": "프롬프트 오류" if after_norm != "주류" else "새 기준 채택",
            "reason": "맥주/발포주/주류 브랜드 단서가 직접 드러나면 주류",
        }

    # 13. 농산물/과일
    if any(k in n for k in ["과일", "바나나", "맛타리", "흙대", "대파", "채소", "버섯"]):
        return {
            "final_gt": "식재료",
            "basis_group": "fresh_produce",
            "judgement": "프롬프트 오류" if after_norm != "식재료" else "새 기준 채택",
            "reason": "과일/채소/버섯류는 신선식품으로 식재료",
        }

    # 14. 젓갈/어묵/참치
    if any(k in n for k in ["젓", "어묵"]):
        return {
            "final_gt": "간편식",
            "basis_group": "ready_side_dish",
            "judgement": "프롬프트 오류" if after_norm != "간편식" else "새 기준 채택",
            "reason": "젓갈/어묵류는 조리 완료 반찬 또는 즉시 섭취 가능한 식품으로 간편식",
        }

    if "참치" in n:
        return {
            "final_gt": "식재료",
            "basis_group": "canned_food_ingredient",
            "judgement": "기준 선택 필요",
            "reason": "참치캔은 바로 섭취 가능하지만 식사/조리 재료로도 쓰임. 현재 기준에서는 통조림/식사용 부재료로 식재료 우선 권장",
        }

    # 기본값: after를 임시 GT로 두되 수동 검토
    return {
        "final_gt": after_norm,
        "basis_group": "needs_manual_review",
        "judgement": "수동 검토",
        "reason": "현재 규칙으로 명확히 해석되지 않는 diff. 상품명 품질과 문맥 확인 필요",
    }


def build_diff_result():
    before_files = {get_relative_key(p, BEFORE_ROOT): p for p in collect_json_files(BEFORE_ROOT)}
    after_files = {get_relative_key(p, AFTER_ROOT): p for p in collect_json_files(AFTER_ROOT)}

    all_keys = sorted(set(before_files) | set(after_files))

    diffs = []

    for key in all_keys:
        before_path = before_files.get(key)
        after_path = after_files.get(key)

        if before_path is None:
            after_data = load_json(after_path)
            for idx, item in enumerate(get_items(after_data)):
                diffs.append({
                    "file": key,
                    "type": "added_item",
                    "item_index": idx,
                    "name": item.get("name"),
                    "qty": item.get("qty"),
                    "base_price": item.get("base_price"),
                    "final_price": item.get("final_price"),
                    "before_category": None,
                    "after_category": get_category(item),
                    "before_category_normalized": None,
                    "after_category_normalized": normalize_category(get_category(item)),
                })
            continue

        if after_path is None:
            before_data = load_json(before_path)
            for idx, item in enumerate(get_items(before_data)):
                diffs.append({
                    "file": key,
                    "type": "removed_item",
                    "item_index": idx,
                    "name": item.get("name"),
                    "qty": item.get("qty"),
                    "base_price": item.get("base_price"),
                    "final_price": item.get("final_price"),
                    "before_category": get_category(item),
                    "after_category": None,
                    "before_category_normalized": normalize_category(get_category(item)),
                    "after_category_normalized": None,
                })
            continue

        before_data = load_json(before_path)
        after_data = load_json(after_path)

        before_items = get_items(before_data)
        after_items = get_items(after_data)

        max_len = max(len(before_items), len(after_items))

        for idx in range(max_len):
            if idx >= len(before_items):
                item = after_items[idx]
                diffs.append({
                    "file": key,
                    "type": "added_item",
                    "item_index": idx,
                    "name": item.get("name"),
                    "qty": item.get("qty"),
                    "base_price": item.get("base_price"),
                    "final_price": item.get("final_price"),
                    "before_category": None,
                    "after_category": get_category(item),
                    "before_category_normalized": None,
                    "after_category_normalized": normalize_category(get_category(item)),
                })
                continue

            if idx >= len(after_items):
                item = before_items[idx]
                diffs.append({
                    "file": key,
                    "type": "removed_item",
                    "item_index": idx,
                    "name": item.get("name"),
                    "qty": item.get("qty"),
                    "base_price": item.get("base_price"),
                    "final_price": item.get("final_price"),
                    "before_category": get_category(item),
                    "after_category": None,
                    "before_category_normalized": normalize_category(get_category(item)),
                    "after_category_normalized": None,
                })
                continue

            before_item = before_items[idx]
            after_item = after_items[idx]

            before_category = get_category(before_item)
            after_category = get_category(after_item)

            before_norm = normalize_category(before_category)
            after_norm = normalize_category(after_category)

            if before_norm == after_norm:
                continue

            item_name = after_item.get("name") or before_item.get("name")

            diffs.append({
                "file": key,
                "type": classify_change(before_category, after_category),
                "item_index": idx,
                "name": item_name,
                "qty": after_item.get("qty", before_item.get("qty")),
                "base_price": after_item.get("base_price", before_item.get("base_price")),
                "final_price": after_item.get("final_price", before_item.get("final_price")),
                "before_category": before_category,
                "after_category": after_category,
                "before_category_normalized": before_norm,
                "after_category_normalized": after_norm,
            })

    summary = Counter(d["type"] for d in diffs)
    result = {
        "summary": {
            "total_diffs": len(diffs),
            "policy_change_pet_to_etc": summary.get("policy_change_pet_to_etc", 0),
            "core_category_changed": summary.get("core_category_changed", 0),
            "support_category_changed": summary.get("support_category_changed", 0),
            "added_item": summary.get("added_item", 0),
            "removed_item": summary.get("removed_item", 0),
            "missing_after_file": summary.get("missing_after_file", 0),
        },
        "diffs": diffs,
    }

    return result


def build_review(diff_result: dict):
    reviewed = []

    for d in diff_result.get("diffs", []):
        rec = recommend_gt(
            name=d.get("name"),
            before=d.get("before_category"),
            after=d.get("after_category"),
        )

        before_norm = d.get("before_category_normalized")
        after_norm = d.get("after_category_normalized")
        final_gt = rec["final_gt"]

        # 실제 판단 형태 보정
        if rec["judgement"] not in {"정상 기준 변경", "애매하지만 새 기준 채택", "기타 허용", "기준 선택 필요", "수동 검토"}:
            if after_norm == final_gt:
                rec["judgement"] = "새 기준 채택"
            elif before_norm == final_gt:
                rec["judgement"] = "프롬프트 오류"
            else:
                rec["judgement"] = "수동 검토"

        reviewed.append({
            **d,
            "final_gt": final_gt,
            "basis_group": rec["basis_group"],
            "judgement": rec["judgement"],
            "reason": rec["reason"],
        })

    summary_by_judgement = Counter(r["judgement"] for r in reviewed)
    summary_by_basis = Counter(r["basis_group"] for r in reviewed)

    result = {
        "summary": {
            "total_reviewed": len(reviewed),
            "by_judgement": dict(summary_by_judgement),
            "by_basis_group": dict(summary_by_basis),
        },
        "reviewed_diffs": reviewed,
    }

    return result


def save_json(path: Path, data: dict):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_csv(path: Path, reviewed: list):
    fieldnames = [
        "file",
        "item_index",
        "name",
        "before_category",
        "after_category",
        "final_gt",
        "basis_group",
        "judgement",
        "reason",
        "type",
        "qty",
        "base_price",
        "final_price",
    ]

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in reviewed:
            writer.writerow({k: r.get(k) for k in fieldnames})


def print_summary(diff_result: dict, review_result: dict):
    print("\n[CATEGORY DIFF SUMMARY]")
    for k, v in diff_result["summary"].items():
        print(f"- {k}: {v:,}")

    print("\n[REVIEW SUMMARY BY JUDGEMENT]")
    for k, v in review_result["summary"]["by_judgement"].items():
        print(f"- {k}: {v:,}")

    print("\n[REVIEW SUMMARY BY BASIS GROUP]")
    for k, v in review_result["summary"]["by_basis_group"].items():
        print(f"- {k}: {v:,}")

    print(f"\n저장 완료: {OUTPUT_DIFF_JSON}")
    print(f"저장 완료: {OUTPUT_REVIEW_JSON}")
    print(f"저장 완료: {OUTPUT_REVIEW_CSV}")


def main():
    if not BEFORE_ROOT.exists():
        raise FileNotFoundError(f"before root not found: {BEFORE_ROOT}")

    if not AFTER_ROOT.exists():
        raise FileNotFoundError(f"after root not found: {AFTER_ROOT}")

    diff_result = build_diff_result()
    review_result = build_review(diff_result)

    save_json(OUTPUT_DIFF_JSON, diff_result)
    save_json(OUTPUT_REVIEW_JSON, review_result)
    save_csv(OUTPUT_REVIEW_CSV, review_result["reviewed_diffs"])

    print_summary(diff_result, review_result)


if __name__ == "__main__":
    main()