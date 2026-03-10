import json
import os
import math
import re
from copy import deepcopy
from difflib import SequenceMatcher


# ============================================================
# ✅ [하이퍼파라미터]
# ============================================================
THR_K = 0.5485481857974387         # 1차 정렬
THR_K_HORIZ = 0.47                 # 2차 좌우
THR_K_VERT = 0.5                   # 3차 위아래

ATTEN_S = 215.55
W_MIN = 9.796612347833586
AGG = "min"                        # "min" | "mean" | "median"

MAX_REPASS_HORIZ = 20
MAX_REPASS_VERT = 20

LOCK_AFTER_CONSEC_DOWN = 1

NOISE_TEXTS = {">", ">>", "<<<", ">>>", "<", "<<", ".", "·", "◆", "=", "eve"}

START_SIM_THRESHOLD = 0.82
END_SIM_THRESHOLD = 0.82

START_SINGLE_KEYWORDS = [
    "판매",
    "상품명",
    "상품(코드)",
    "상품코드",
    "단가",
    "수량",
    "금액",
]

START_TOKEN_GROUPS = [
    ["상품명", "단가", "수량", "금액"],
    ["상품(코드)", "단가", "수량", "금액"],
    ["상품코드", "단가", "수량", "금액"],
    ["단가", "수량", "금액"],
]

END_KEYWORDS = [
    "합계",
    "총구매액",
    "결제대상금액",
    "내실금액",
    "쿠폰할인",
    "총할인액",
]

TAIL_SECTION_START_KEYWORDS = [
    "총품목수량",
    "면세",
    "과세",
    "부가세",
    "합계",
    "면세물품",
    "과세물품",
    "결제대상금액",
]

PROTECTED_HEADER_WORDS_EXACT = {
    "판매", "상품명", "상품(코드)", "상품코드", "단가", "수량", "금액"
}


# ============================================================
# ✅ 유틸
# ============================================================
def normalize_text(text):
    if text is None:
        return ""
    text = str(text)
    text = text.replace(" ", "")
    text = re.sub(r"[^0-9A-Za-z가-힣]", "", text)
    return text


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def fuzzy_contains(line_text, keyword, sim_threshold=0.82):
    norm_line = normalize_text(line_text)
    norm_kw = normalize_text(keyword)

    if not norm_line or not norm_kw:
        return False

    if norm_kw in norm_line:
        return True

    if similarity(norm_line, norm_kw) >= sim_threshold:
        return True

    if len(norm_line) >= len(norm_kw):
        win = len(norm_kw)
        for i in range(len(norm_line) - win + 1):
            chunk = norm_line[i:i + win]
            if similarity(chunk, norm_kw) >= sim_threshold:
                return True

    return False


def token_match_count(line_text, token_group, sim_threshold=0.82):
    norm_line = normalize_text(line_text)
    count = 0

    for token in token_group:
        norm_token = normalize_text(token)
        if not norm_token:
            continue

        matched = False

        if norm_token in norm_line:
            matched = True
        else:
            if len(norm_line) >= len(norm_token):
                win = len(norm_token)
                for i in range(len(norm_line) - win + 1):
                    chunk = norm_line[i:i + win]
                    if similarity(chunk, norm_token) >= sim_threshold:
                        matched = True
                        break
            else:
                if similarity(norm_line, norm_token) >= sim_threshold:
                    matched = True

        if matched:
            count += 1

    return count


def point_line_distance(point, slope, intercept):
    denom = math.sqrt(slope ** 2 + 1)
    return abs((slope * point["x"]) - point["y"] + intercept) / denom


def line_to_plain_text(line):
    line = sorted(line, key=lambda x: x["xmin"])
    return " ".join([w["text"] for w in line])


def parse_receipt_filename(file_name):
    stem = file_name.replace(".json", "")

    m = re.match(r"^(.*)_([a-zA-Z])$", stem)
    if m:
        parent_name = m.group(1)
        suffix = m.group(2).lower()
        return {
            "is_split_piece": True,
            "parent_name": parent_name,
            "piece_suffix": suffix,
        }

    return {
        "is_split_piece": False,
        "parent_name": stem,
        "piece_suffix": None,
    }


def piece_suffix_order(suffix):
    if suffix is None:
        return -1
    suffix = str(suffix).lower()
    if len(suffix) == 1 and "a" <= suffix <= "z":
        return ord(suffix) - ord("a")
    return 9999


# ============================================================
# ✅ 보호 관련
# ============================================================
def is_protected_header_word(word):
    text = normalize_text(word.get("text", ""))
    if not text:
        return False

    for kw in PROTECTED_HEADER_WORDS_EXACT:
        if text == normalize_text(kw):
            return True
    return False


def is_protected_line(line):
    return any(w.get("protected_line", False) for w in line)


def mark_line_as_protected(line):
    for w in line:
        w["protected_line"] = True


def is_start_protected_candidate(line_text):
    single_hit = any(
        fuzzy_contains(line_text, kw, START_SIM_THRESHOLD)
        for kw in START_SINGLE_KEYWORDS
    )

    group_hit = False
    for group in START_TOKEN_GROUPS:
        cnt = token_match_count(line_text, group, START_SIM_THRESHOLD)
        if cnt >= max(1, len(group) - 1):
            group_hit = True
            break

    return single_hit or group_hit


def is_tail_section_start_line(line):
    line_text = line_to_plain_text(line)
    return any(
        fuzzy_contains(line_text, kw, END_SIM_THRESHOLD)
        for kw in TAIL_SECTION_START_KEYWORDS
    )


def apply_protected_line_flags(receipts):
    for receipt in receipts:
        lines = receipt.get("lines", [])
        protected_indices = []

        for i, line in enumerate(lines):
            plain = line_to_plain_text(line)
            if is_start_protected_candidate(plain):
                mark_line_as_protected(line)
                protected_indices.append(i)

        receipt["protected_line_indices"] = protected_indices

    return receipts


# ============================================================
# ✅ 잠금
# ============================================================
def apply_move_and_lock(word):
    word["total_down_moves"] = word.get("total_down_moves", 0) + 1

    if (not word.get("locked", False)) and (word["total_down_moves"] >= LOCK_AFTER_CONSEC_DOWN):
        word["locked"] = True
        return True
    return False


# ============================================================
# ✅ 계산 로직
# ============================================================
def calculate_primary_line_error(anchor, curr, k_value):
    x_dist = abs(curr["xmin"] - anchor["xmin"])

    dx = anchor["v1"]["x"] - anchor["v0"]["x"]
    dy = anchor["v1"]["y"] - anchor["v0"]["y"]

    raw_slope = dy / dx if (dx != 0 and anchor["width"] > W_MIN) else 0.0
    attenuation = 1.0 / (1.0 + (x_dist / ATTEN_S))
    slope = raw_slope * attenuation
    intercept = anchor["v0"]["y"] - (slope * anchor["v0"]["x"])

    target_points = [curr["v0"], curr["v1"], curr["v2"], curr["v3"]]
    errors = []

    denom = math.sqrt((slope * slope) + 1.0)
    for p in target_points:
        dist = abs((slope * p["x"]) - p["y"] + intercept) / denom
        errors.append(dist)

    if AGG == "min":
        err = min(errors)
    elif AGG == "mean":
        err = sum(errors) / len(errors)
    elif AGG == "median":
        e = sorted(errors)
        err = 0.5 * (e[1] + e[2])
    else:
        err = min(errors)

    threshold = abs(anchor["height"]) * k_value
    return err <= threshold, err, threshold


def calculate_horizontal_alignment(anchor, curr, k_value):
    ref_height = max(abs(anchor["height"]), abs(curr["height"]))
    threshold = ref_height * k_value

    anchor_top_points = [anchor["v0"], anchor["v1"]]
    curr_top_points = [curr["v0"], curr["v1"]]

    min_x_dist_a = float("inf")
    chosen_curr_point_a = None

    for a_pt in anchor_top_points:
        for c_pt in curr_top_points:
            x_dist = abs(a_pt["x"] - c_pt["x"])
            if x_dist < min_x_dist_a:
                min_x_dist_a = x_dist
                chosen_curr_point_a = c_pt

    if chosen_curr_point_a is None:
        chosen_curr_point_a = curr["v0"]

    dx_a = anchor["v1"]["x"] - anchor["v0"]["x"]
    dy_a = anchor["v1"]["y"] - anchor["v0"]["y"]
    raw_slope_a = dy_a / dx_a if (dx_a != 0 and anchor["width"] > W_MIN) else 0.0
    slope_a = raw_slope_a
    intercept_a = anchor["v0"]["y"] - (slope_a * anchor["v0"]["x"])

    err_anchor_to_curr = point_line_distance(chosen_curr_point_a, slope_a, intercept_a)
    pass_anchor_to_curr = (err_anchor_to_curr <= threshold)

    min_x_dist_b = float("inf")
    chosen_anchor_point_b = None

    for c_pt in curr_top_points:
        for a_pt in anchor_top_points:
            x_dist = abs(c_pt["x"] - a_pt["x"])
            if x_dist < min_x_dist_b:
                min_x_dist_b = x_dist
                chosen_anchor_point_b = a_pt

    if chosen_anchor_point_b is None:
        chosen_anchor_point_b = anchor["v0"]

    dx_c = curr["v1"]["x"] - curr["v0"]["x"]
    dy_c = curr["v1"]["y"] - curr["v0"]["y"]
    raw_slope_c = dy_c / dx_c if (dx_c != 0 and curr["width"] > W_MIN) else 0.0
    slope_c = raw_slope_c
    intercept_c = curr["v0"]["y"] - (slope_c * curr["v0"]["x"])

    err_curr_to_anchor = point_line_distance(chosen_anchor_point_b, slope_c, intercept_c)
    pass_curr_to_anchor = (err_curr_to_anchor <= threshold)

    return pass_anchor_to_curr or pass_curr_to_anchor


def calculate_horizontal_chain_alignment(anchor, curr, k_value):
    ref_height = max(abs(anchor["height"]), abs(curr["height"]))
    threshold = ref_height * k_value

    dx_a = anchor["v1"]["x"] - anchor["v0"]["x"]
    dy_a = anchor["v1"]["y"] - anchor["v0"]["y"]
    raw_slope_a = dy_a / dx_a if (dx_a != 0 and anchor["width"] > W_MIN) else 0.0
    slope_a = raw_slope_a
    intercept_a = anchor["v0"]["y"] - (slope_a * anchor["v0"]["x"])

    err_a_v0 = point_line_distance(curr["v0"], slope_a, intercept_a)
    err_a_v1 = point_line_distance(curr["v1"], slope_a, intercept_a)
    err_anchor_to_curr = min(err_a_v0, err_a_v1)
    pass_anchor_to_curr = (err_anchor_to_curr <= threshold)

    dx_c = curr["v1"]["x"] - curr["v0"]["x"]
    dy_c = curr["v1"]["y"] - curr["v0"]["y"]
    raw_slope_c = dy_c / dx_c if (dx_c != 0 and curr["width"] > W_MIN) else 0.0
    slope_c = raw_slope_c
    intercept_c = curr["v0"]["y"] - (slope_c * curr["v0"]["x"])

    err_c_v0 = point_line_distance(anchor["v0"], slope_c, intercept_c)
    err_c_v1 = point_line_distance(anchor["v1"], slope_c, intercept_c)
    err_curr_to_anchor = min(err_c_v0, err_c_v1)
    pass_curr_to_anchor = (err_curr_to_anchor <= threshold)

    return pass_anchor_to_curr or pass_curr_to_anchor


def calculate_vertical_alignment(anchor, curr, k_value, use_attenuation=False):
    dx = anchor["v1"]["x"] - anchor["v0"]["x"]
    dy = anchor["v1"]["y"] - anchor["v0"]["y"]
    raw_slope = dy / dx if (dx != 0 and anchor["width"] > W_MIN) else 0.0

    anchor_points = [anchor["v0"], anchor["v1"], anchor["v2"], anchor["v3"]]
    target_top_points = [curr["v0"], curr["v1"]]

    min_x_dist = float("inf")
    chosen_target_p = None

    for ap in anchor_points:
        for tp in target_top_points:
            x_dist = abs(ap["x"] - tp["x"])
            if x_dist < min_x_dist:
                min_x_dist = x_dist
                chosen_target_p = tp

    if chosen_target_p is None:
        chosen_target_p = curr["v0"]

    if use_attenuation:
        attenuation = 1.0 / (1.0 + (min_x_dist / ATTEN_S))
        slope = raw_slope * attenuation
    else:
        slope = raw_slope

    intercept = anchor["v0"]["y"] - (slope * anchor["v0"]["x"])
    denom = math.sqrt(slope ** 2 + 1)

    err = abs((slope * chosen_target_p["x"]) - chosen_target_p["y"] + intercept) / denom
    ref_height = max(abs(anchor["height"]), abs(curr["height"]))
    threshold = ref_height * k_value

    return err, threshold


# ============================================================
# ✅ OCR JSON -> receipt words
# ============================================================
def extract_receipt_words_from_json(clova_json, file_name="unknown.json"):
    if "images" not in clova_json or len(clova_json["images"]) == 0:
        return {
            "file_name": file_name,
            "file_meta": parse_receipt_filename(file_name),
            "words": [],
        }

    raw_fields = clova_json["images"][0].get("fields", [])
    refined_data = []
    word_idx = 0
    file_meta = parse_receipt_filename(file_name)

    for field in raw_fields:
        text = field.get("inferText", "")
        if text is None:
            continue
        if text.strip() in NOISE_TEXTS:
            continue

        try:
            v = field["boundingPoly"]["vertices"]
            if isinstance(v, dict):
                v = [v[str(i)] for i in range(4)]
        except Exception:
            continue

        width = abs(v[1]["x"] - v[0]["x"])
        height = min(v[2]["y"], v[3]["y"]) - max(v[0]["y"], v[1]["y"])
        xmin = min(v[0]["x"], v[3]["x"])
        xmax = max(v[1]["x"], v[2]["x"])

        refined_data.append({
            "uid": f"{file_name}::w{word_idx:06d}",
            "text": text,
            "v0": v[0], "v1": v[1], "v2": v[2], "v3": v[3],
            "xmin": xmin,
            "xmax": xmax,
            "width": width,
            "height": height,
            "locked": False,
            "total_down_moves": 0,
            "protected_line": False,
        })
        word_idx += 1

    return {
        "file_name": file_name,
        "file_meta": file_meta,
        "words": refined_data,
    }


# ============================================================
# ✅ 정렬 단계
# ============================================================
def sort_words_by_y(receipts):
    for receipt in receipts:
        receipt["words"].sort(key=lambda x: x["v0"]["y"])
    return receipts


def group_words_into_lines(receipts):
    for receipt in receipts:
        words = receipt["words"]

        if not words:
            receipt["lines"] = []
            continue

        lines = []
        current_line = [words[0]]

        for i in range(1, len(words)):
            curr = words[i]
            anchor = min(current_line, key=lambda w: abs(w["xmin"] - curr["xmin"]))
            is_same_line, _, _ = calculate_primary_line_error(anchor, curr, THR_K)

            if is_same_line:
                current_line.append(curr)
            else:
                lines.append(current_line)
                current_line = [curr]

        lines.append(current_line)
        receipt["lines"] = lines

    return receipts


def sort_line_words_by_x(receipts):
    for receipt in receipts:
        for line in receipt.get("lines", []):
            line.sort(key=lambda x: x["xmin"])
    return receipts


# ============================================================
# ✅ 2차 HORIZ 재검토
# ============================================================
def refine_lines_horizontal(receipts, thr_k_h=THR_K_HORIZ, max_moves_per_line=200):
    move_count_total = 0

    def move_word_to_next_line(lines, li, src_line, word):
        nonlocal move_count_total

        if li + 1 >= len(lines):
            lines.append([])

        target_line = lines[li + 1]

        if is_protected_line(target_line):
            return False

        if is_protected_header_word(word):
            return False

        if word.get("locked", False):
            return False

        if word not in src_line:
            return False

        src_line.remove(word)
        target_line.append(word)
        target_line.sort(key=lambda x: x["xmin"])

        move_count_total += 1
        apply_move_and_lock(word)
        return True

    for receipt in receipts:
        lines = receipt.get("lines", [])
        li = 0

        while li < len(lines):
            line = lines[li]

            if not line:
                li += 1
                continue

            line.sort(key=lambda x: x["xmin"])

            if len(line) < 2:
                li += 1
                continue

            moves_in_this_line = 0
            i = 0

            while i < len(line) - 1:
                line.sort(key=lambda x: x["xmin"])
                left = line[i]
                curr = line[i + 1]

                left_protected = is_protected_header_word(left)
                curr_protected = is_protected_header_word(curr)

                is_pass = calculate_horizontal_alignment(left, curr, thr_k_h)

                if is_pass:
                    i += 1
                    continue

                move_target = None
                move_reason = None

                if left_protected and curr_protected:
                    move_target = None
                elif curr_protected and not left_protected:
                    move_target = left
                    move_reason = "curr_protected_move_left"
                else:
                    move_target = curr
                    move_reason = "default_move_curr"

                if move_target is None:
                    i += 1
                    continue

                moved = move_word_to_next_line(lines, li, line, move_target)

                if not moved:
                    i += 1
                    continue

                moves_in_this_line += 1

                if moves_in_this_line >= max_moves_per_line:
                    break

                if len(line) < 2:
                    break

                if move_reason == "curr_protected_move_left":
                    continue

                chain_anchor = move_target

                while i + 1 < len(line):
                    next_word = line[i + 1]

                    next_word_protected = is_protected_header_word(next_word)
                    chain_anchor_protected = is_protected_header_word(chain_anchor)

                    chain_pass = calculate_horizontal_chain_alignment(chain_anchor, next_word, thr_k_h)

                    if not chain_pass:
                        break

                    chain_move_target = None
                    chain_move_reason = None

                    if chain_anchor_protected and next_word_protected:
                        chain_move_target = None
                    elif next_word_protected and not chain_anchor_protected:
                        chain_move_target = chain_anchor
                        chain_move_reason = "chain_next_protected_move_anchor"
                    else:
                        chain_move_target = next_word
                        chain_move_reason = "chain_move_next"

                    if chain_move_target is None:
                        break

                    moved_chain = move_word_to_next_line(lines, li, line, chain_move_target)

                    if not moved_chain:
                        break

                    moves_in_this_line += 1

                    if moves_in_this_line >= max_moves_per_line:
                        break

                    if len(line) < 2:
                        break

                    if chain_move_reason == "chain_next_protected_move_anchor":
                        break

                    chain_anchor = chain_move_target

            li += 1

        receipt["lines"] = [l for l in lines if l]

    return receipts, move_count_total


# ============================================================
# ✅ 3차 VERT 재검토
# ============================================================
def refine_lines_vertical(receipts, thr_k_v=THR_K_VERT):
    move_count_total = 0

    def x_overlap(a, b):
        return (b["xmin"] <= a["xmax"]) and (b["xmax"] >= a["xmin"])

    for receipt in receipts:
        lines = receipt.get("lines", [])
        tail_section_started = False
        idx = 0

        while idx < len(lines) - 1:
            upper_line = lines[idx]
            lower_line = lines[idx + 1]

            upper_line.sort(key=lambda x: x["xmin"])
            lower_line.sort(key=lambda x: x["xmin"])

            if not upper_line or not lower_line:
                idx += 1
                continue

            if not tail_section_started:
                if is_tail_section_start_line(upper_line) or is_tail_section_start_line(lower_line):
                    tail_section_started = True

            any_candidate_exists = False

            for uw in upper_line:
                cands = [lw for lw in lower_line if x_overlap(uw, lw)]
                if cands:
                    any_candidate_exists = True

            if not any_candidate_exists:
                if tail_section_started:
                    movable_words = []

                    for uw in list(upper_line):
                        if is_protected_header_word(uw):
                            continue
                        if uw.get("locked", False):
                            continue
                        movable_words.append(uw)

                    if not is_protected_line(lower_line):
                        for uw in movable_words:
                            if uw in upper_line:
                                upper_line.remove(uw)
                                lower_line.append(uw)
                                lower_line.sort(key=lambda x: x["xmin"])
                                move_count_total += 1
                                apply_move_and_lock(uw)

                    lines = [l for l in lines if l]
                    receipt["lines"] = lines
                    idx += 1
                    continue

            upper_words_copy = list(upper_line)

            for anchor_word in upper_words_copy:
                if not lower_line:
                    break

                candidates = [w for w in lower_line if x_overlap(anchor_word, w)]

                if not candidates:
                    continue

                best_pass = None

                for target_word in candidates:
                    err, thr = calculate_vertical_alignment(
                        anchor_word, target_word, thr_k_v, True
                    )
                    is_pass = (err <= thr)

                    if is_pass:
                        if best_pass is None or err < best_pass[0]:
                            best_pass = (err, target_word)

                if best_pass is None:
                    continue

                if is_protected_header_word(anchor_word):
                    continue

                if anchor_word.get("locked", False):
                    continue

                if anchor_word not in upper_line:
                    continue

                if is_protected_line(lower_line):
                    continue

                upper_line.remove(anchor_word)
                lower_line.append(anchor_word)
                lower_line.sort(key=lambda x: x["xmin"])

                move_count_total += 1
                apply_move_and_lock(anchor_word)

            lines = [l for l in lines if l]
            receipt["lines"] = lines
            idx += 1

    return receipts, move_count_total


# ============================================================
# ✅ 병합
# ============================================================
def merge_receipt_pieces(receipts):
    single_receipts = []
    split_groups = {}

    for receipt in receipts:
        meta = receipt.get("file_meta", {})
        if meta.get("is_split_piece", False):
            parent = meta.get("parent_name", receipt["file_name"].replace(".json", ""))
            split_groups.setdefault(parent, []).append(receipt)
        else:
            single_receipts.append(receipt)

    merged_results = []

    for receipt in single_receipts:
        merged_results.append({
            "file_name": receipt["file_name"],
            "file_meta": {
                **receipt.get("file_meta", {}),
                "merge_type": "single",
                "merged_from": [receipt["file_name"]],
                "is_merged_output": False,
            },
            "lines": receipt.get("lines", []),
            "cut_meta": {},
        })

    for parent_name, receipts_group in split_groups.items():
        receipts_sorted = sorted(
            receipts_group,
            key=lambda r: piece_suffix_order(r.get("file_meta", {}).get("piece_suffix"))
        )

        merged_lines = []
        merged_from = []
        piece_order = []

        for r in receipts_sorted:
            merged_lines.extend(r.get("lines", []))
            merged_from.append(r["file_name"])
            piece_order.append(r.get("file_meta", {}).get("piece_suffix"))

        merged_receipt = {
            "file_name": f"{parent_name}.json",
            "file_meta": {
                "is_split_piece": False,
                "parent_name": parent_name,
                "piece_suffix": None,
                "merge_type": "split_merged",
                "is_merged_output": True,
                "merged_from": merged_from,
                "piece_order": piece_order,
                "piece_count": len(receipts_sorted),
            },
            "lines": merged_lines,
            "cut_meta": {
                "merged": True,
                "piece_count": len(receipts_sorted),
            },
        }
        merged_results.append(merged_receipt)

    merged_results.sort(key=lambda x: x["file_name"])
    return merged_results


# ============================================================
# ✅ 최종 커팅
# ============================================================
def cut_receipt_body(receipts):
    for receipt in receipts:
        lines = receipt.get("lines", [])

        if not lines:
            receipt["cut_meta"] = {
                "start_idx": None,
                "end_idx": None,
                "cut_applied": False,
                "reason": "empty_lines",
            }
            continue

        line_texts = [line_to_plain_text(line) for line in lines]
        protected_idxs = [i for i, line in enumerate(lines) if is_protected_line(line)]

        if protected_idxs:
            start_idx = protected_idxs[0]
        else:
            start_idx = 0

        last_end_idx = None
        last_end_kw_hit = None
        end_match_history = []

        for i in range(start_idx, len(line_texts)):
            text = line_texts[i]
            matched_keywords_this_line = []

            for kw in END_KEYWORDS:
                matched_end = fuzzy_contains(text, kw, END_SIM_THRESHOLD)
                if matched_end:
                    matched_keywords_this_line.append(kw)
                    last_end_idx = i
                    last_end_kw_hit = kw

            if matched_keywords_this_line:
                end_match_history.append({
                    "line_idx": i,
                    "line_text": text,
                    "matched_keywords": matched_keywords_this_line,
                })

        if last_end_idx is None:
            end_idx = len(lines) - 1
        else:
            end_idx = last_end_idx

        receipt["lines"] = lines[start_idx:end_idx + 1]
        receipt["cut_meta"] = {
            "start_idx": start_idx,
            "end_idx": end_idx,
            "cut_applied": True,
            "last_end_keyword": last_end_kw_hit,
            "end_match_history": end_match_history,
        }

    return receipts


# ============================================================
# ✅ 결과 생성
# ============================================================
def build_lines_structured(lines):
    structured = []
    for line in lines:
        row = []
        for w in sorted(line, key=lambda x: x["xmin"]):
            row.append({
                "text": w["text"],
                "x": w["v0"]["x"],
                "y": w["v0"]["y"],
            })
        structured.append(row)
    return structured


def build_output_receipt(receipt):
    lines = receipt.get("lines", [])
    return {
        "source": receipt.get("file_name", ""),
        "lines_structured": build_lines_structured(lines),
    }


# ============================================================
# ✅ 핵심 엔진
# ============================================================
def run_parser_engine(receipts):
    receipts = deepcopy(receipts)

    receipts = sort_words_by_y(receipts)
    receipts = group_words_into_lines(receipts)
    receipts = sort_line_words_by_x(receipts)
    receipts = apply_protected_line_flags(receipts)

    for _ in range(MAX_REPASS_HORIZ):
        receipts, moved_h = refine_lines_horizontal(
            receipts,
            thr_k_h=THR_K_HORIZ,
        )
        if moved_h == 0:
            break

    for _ in range(MAX_REPASS_VERT):
        receipts, moved_v = refine_lines_vertical(
            receipts,
            thr_k_v=THR_K_VERT,
        )
        if moved_v == 0:
            break

    receipts = merge_receipt_pieces(receipts)
    receipts = cut_receipt_body(receipts)

    return [build_output_receipt(r) for r in receipts]


# ============================================================
# ✅ 앱용 진입 함수
# ============================================================
def parse_receipt_request(json_items):
    """
    json_items 예시:
    [
        {"file_name": "010_costco_a.json", "data": {...}},
        {"file_name": "010_costco_b.json", "data": {...}},
        {"file_name": "011_hanaro.json", "data": {...}}
    ]
    """
    receipts = []

    for item in json_items:
        file_name = item["file_name"]
        data = item["data"]
        receipts.append(extract_receipt_words_from_json(data, file_name=file_name))

    return run_parser_engine(receipts)


def parse_single_receipt_json(clova_json, file_name="receipt.json"):
    receipt = extract_receipt_words_from_json(clova_json, file_name=file_name)
    results = run_parser_engine([receipt])
    return results[0] if results else None


# ============================================================
# ✅ 폴더 로드 / 폴더 파싱 / 개별 저장
# ============================================================
def load_json_items_from_folder(folder_path):
    json_items = []

    if not os.path.isdir(folder_path):
        raise FileNotFoundError(f"폴더를 찾을 수 없습니다: {folder_path}")

    file_names = sorted(
        [f for f in os.listdir(folder_path) if f.lower().endswith(".json")]
    )

    for file_name in file_names:
        file_path = os.path.join(folder_path, file_name)

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        json_items.append({
            "file_name": file_name,
            "data": data
        })

    return json_items


def parse_receipts_from_folder(folder_path):
    json_items = load_json_items_from_folder(folder_path)
    return parse_receipt_request(json_items)


def save_each_receipt_result(results, output_folder):
    os.makedirs(output_folder, exist_ok=True)

    for item in results:
        source_name = item["source"].replace(".json", "")
        output_path = os.path.join(output_folder, f"{source_name}_parsed.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(item, f, ensure_ascii=False, indent=2)


# ============================================================
# ✅ 바로 실행
# ============================================================
if __name__ == "__main__":
    raw_json_folder = "./raw_json"
    output_folder = "./parsed_output"

    results = parse_receipts_from_folder(raw_json_folder)
    save_each_receipt_result(results, output_folder)

    print(f"완료: {output_folder}")
