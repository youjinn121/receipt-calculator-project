import math
import re
from difflib import SequenceMatcher
from typing import Any, Dict, List


THR_K = 0.5485481857974387
THR_K_HORIZ = 0.47
THR_K_VERT = 0.5

ATTEN_S = 215.55
W_MIN = 9.796612347833586
AGG = "min"

MAX_REPASS_HORIZ = 20
MAX_REPASS_VERT = 20

LOCK_AFTER_CONSEC_DOWN = 1

NOISE_TEXTS = {">", ">>", "<<<", ">>>", "<", "<<", ".", "·", "◆", "=", "eve", "****", "***"}

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


def normalize_text(text: Any) -> str:
    if text is None:
        return ""
    text = str(text)
    text = text.replace(" ", "")
    text = re.sub(r"[^0-9A-Za-z가-힣]", "", text)
    return text


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def fuzzy_contains(line_text: str, keyword: str, sim_threshold: float = 0.82) -> bool:
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


def token_match_count(line_text: str, token_group: List[str], sim_threshold: float = 0.82) -> int:
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


def line_to_plain_text(line: List[Dict[str, Any]]) -> str:
    return " ".join([w["text"] for w in sorted(line, key=lambda x: x["xmin"])])

def line_tokens_to_text(line: List[Dict[str, Any]]) -> str:
    if not line:
        return ""

    return line_to_plain_text(line).strip()


def convert_lines_to_plain_text(lines: List[List[Dict[str, Any]]]) -> List[str]:
    result: List[str] = []

    for line in lines:
        text = line_tokens_to_text(line)
        if text:
            result.append(text)

    return result

def point_line_distance(point: Dict[str, Any], slope: float, intercept: float) -> float:
    denom = math.sqrt(slope ** 2 + 1)
    return abs((slope * point["x"]) - point["y"] + intercept) / denom


def is_tail_section_start_line(line: List[Dict[str, Any]]) -> bool:
    line_text = line_to_plain_text(line)
    return any(
        fuzzy_contains(line_text, kw, END_SIM_THRESHOLD)
        for kw in TAIL_SECTION_START_KEYWORDS
    )


def is_protected_line(line: List[Dict[str, Any]]) -> bool:
    return any(w.get("protected_line", False) for w in line)


def mark_line_as_protected(line: List[Dict[str, Any]]) -> None:
    for w in line:
        w["protected_line"] = True


def is_start_protected_candidate(line_text: str):
    single_hit = any(
        fuzzy_contains(line_text, kw, START_SIM_THRESHOLD)
        for kw in START_SINGLE_KEYWORDS
    )

    group_hit = False
    best_count = 0

    for group in START_TOKEN_GROUPS:
        cnt = token_match_count(line_text, group, START_SIM_THRESHOLD)
        best_count = max(best_count, cnt)
        if cnt >= max(1, len(group) - 1):
            group_hit = True

    return single_hit or group_hit, best_count


def is_protected_header_word(word: Dict[str, Any]) -> bool:
    text = normalize_text(word.get("text", ""))
    if not text:
        return False

    for kw in PROTECTED_HEADER_WORDS_EXACT:
        if text == normalize_text(kw):
            return True
    return False


def apply_protected_line_flags(receipts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for receipt in receipts:
        lines = receipt.get("lines", [])
        protected_indices = []

        for i, line in enumerate(lines):
            plain = line_to_plain_text(line)
            protect, _ = is_start_protected_candidate(plain)
            if protect:
                mark_line_as_protected(line)
                protected_indices.append(i)

        receipt["protected_line_indices"] = protected_indices

    return receipts


def canonical_start_token(text: str):
    if not text:
        return None

    for kw in START_SINGLE_KEYWORDS:
        if fuzzy_contains(text, kw, START_SIM_THRESHOLD):
            return kw
    return None


def extract_start_tokens_from_line(line: List[Dict[str, Any]]) -> List[str]:
    tokens = []
    for w in sorted(line, key=lambda x: x["xmin"]):
        ct = canonical_start_token(w.get("text", ""))
        if ct is not None:
            tokens.append(ct)
    return tokens


def is_header_fragment_line(line: List[Dict[str, Any]]) -> bool:
    if not line:
        return False

    words_sorted = sorted(line, key=lambda x: x["xmin"])
    matched = 0

    for w in words_sorted:
        if canonical_start_token(w.get("text", "")) is not None:
            matched += 1

    if matched == 0:
        return False

    return matched >= max(1, len(words_sorted) - 1)


def header_token_group_score(token_list: List[str]) -> int:
    token_set = set(token_list)
    best = 0

    for group in START_TOKEN_GROUPS:
        cnt = 0
        for g in group:
            if g in token_set:
                cnt += 1
        best = max(best, cnt)

    return best


def line_vertical_gap(line_a: List[Dict[str, Any]], line_b: List[Dict[str, Any]]) -> float:
    if not line_a or not line_b:
        return float("inf")

    a_bottom = max(w["v2"]["y"] for w in line_a)
    b_top = min(w["v0"]["y"] for w in line_b)
    return b_top - a_bottom


def avg_line_height(line: List[Dict[str, Any]]) -> float:
    if not line:
        return 0.0
    return sum(abs(w["height"]) for w in line) / len(line)


def calculate_primary_line_error(anchor: Dict[str, Any], curr: Dict[str, Any], k_value: float):
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


def calculate_horizontal_relation(anchor: Dict[str, Any], curr: Dict[str, Any], k_value: float):
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

    return {
        "is_same_line": pass_anchor_to_curr or pass_curr_to_anchor,
        "threshold": threshold,
        "anchor_to_curr": {
            "err": err_anchor_to_curr,
            "pass": pass_anchor_to_curr,
        },
        "curr_to_anchor": {
            "err": err_curr_to_anchor,
            "pass": pass_curr_to_anchor,
        }
    }


def calculate_horizontal_chain_relation(anchor: Dict[str, Any], curr: Dict[str, Any], k_value: float):
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

    return {
        "is_same_line": pass_anchor_to_curr or pass_curr_to_anchor,
        "threshold": threshold,
        "anchor_to_curr": {
            "err": err_anchor_to_curr,
            "pass": pass_anchor_to_curr,
        },
        "curr_to_anchor": {
            "err": err_curr_to_anchor,
            "pass": pass_curr_to_anchor,
        }
    }


def calculate_vertical_relation(anchor: Dict[str, Any], curr: Dict[str, Any], k_value: float, use_attenuation: bool = False):
    dx = anchor["v1"]["x"] - anchor["v0"]["x"]
    dy = anchor["v1"]["y"] - anchor["v0"]["y"]
    raw_slope = dy / dx if (dx != 0 and anchor["width"] > W_MIN) else 0.0

    anchor_points = [anchor["v0"], anchor["v1"], anchor["v2"], anchor["v3"]]
    target_top_points = [curr["v0"], curr["v1"]]

    min_x_dist = float("inf")
    chosen_target = None

    for ap in anchor_points:
        for tp in target_top_points:
            x_dist = abs(ap["x"] - tp["x"])
            if x_dist < min_x_dist:
                min_x_dist = x_dist
                chosen_target = tp

    if chosen_target is None:
        chosen_target = curr["v0"]

    if use_attenuation:
        attenuation = 1.0 / (1.0 + (min_x_dist / ATTEN_S))
        slope = raw_slope * attenuation
    else:
        slope = raw_slope

    intercept = anchor["v0"]["y"] - (slope * anchor["v0"]["x"])
    denom = math.sqrt(slope ** 2 + 1)
    err = abs((slope * chosen_target["x"]) - chosen_target["y"] + intercept) / denom

    ref_height = max(abs(anchor["height"]), abs(curr["height"]))
    threshold = ref_height * k_value

    return err, threshold


def apply_move_and_lock(word: Dict[str, Any]) -> bool:
    word["total_down_moves"] = word.get("total_down_moves", 0) + 1
    if (not word.get("locked", False)) and (word["total_down_moves"] >= LOCK_AFTER_CONSEC_DOWN):
        word["locked"] = True
        return True
    return False


def _build_words_from_clova_fields(raw_fields: List[Dict[str, Any]], file_name: str) -> List[Dict[str, Any]]:
    words = []
    word_idx = 0

    for field in raw_fields:
        text = field.get("inferText", "")
        if text is None or text.strip() in NOISE_TEXTS:
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

        words.append({
            "uid": f"{file_name}::w{word_idx:06d}",
            "text": text,
            "v0": v[0],
            "v1": v[1],
            "v2": v[2],
            "v3": v[3],
            "xmin": xmin,
            "xmax": xmax,
            "width": width,
            "height": height,
            "locked": False,
            "total_down_moves": 0,
            "protected_line": False,
        })
        word_idx += 1

    return words


def load_clova_receipt_from_json_data(data: Dict[str, Any], file_name: str = "receipt.json") -> Dict[str, Any]:
    if "images" not in data or not data["images"]:
        return {
            "file_name": file_name,
            "words": [],
        }

    raw_fields = data["images"][0].get("fields", [])

    return {
        "file_name": file_name,
        "words": _build_words_from_clova_fields(raw_fields, file_name),
    }


def sort_words_by_y(receipts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for receipt in receipts:
        receipt["words"].sort(key=lambda x: x["v0"]["y"])
    return receipts


def group_words_into_lines(receipts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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


def sort_words_in_each_line_by_x(receipts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for receipt in receipts:
        for line in receipt["lines"]:
            line.sort(key=lambda x: x["xmin"])
    return receipts


def merge_adjacent_start_header_lines(receipts: List[Dict[str, Any]], max_gap_ratio: float = 2.5) -> List[Dict[str, Any]]:
    for receipt in receipts:
        lines = receipt.get("lines", [])
        if len(lines) < 2:
            continue

        idx = 0
        while idx < len(lines) - 1:
            upper = lines[idx]
            lower = lines[idx + 1]

            upper.sort(key=lambda x: x["xmin"])
            lower.sort(key=lambda x: x["xmin"])

            upper_tokens = extract_start_tokens_from_line(upper)
            lower_tokens = extract_start_tokens_from_line(lower)

            upper_is_fragment = is_header_fragment_line(upper)
            lower_is_fragment = is_header_fragment_line(lower)

            combined_tokens = upper_tokens + lower_tokens
            combined_score = header_token_group_score(combined_tokens)

            gap = line_vertical_gap(upper, lower)
            ref_h = max(avg_line_height(upper), avg_line_height(lower), 1.0)

            should_merge = (
                upper_is_fragment and
                lower_is_fragment and
                gap <= ref_h * max_gap_ratio and
                combined_score >= 3
            )

            if should_merge:
                merged_line = upper + lower
                merged_line.sort(key=lambda x: x["xmin"])
                mark_line_as_protected(merged_line)
                lines[idx] = merged_line
                del lines[idx + 1]
            else:
                idx += 1

        receipt["lines"] = lines

    return receipts


def horizontal_refinement_pass(receipts: List[Dict[str, Any]]):
    move_count_total = 0

    def nearest_upper_by_x(target_word, upper_line, exclude_word=None):
        candidates = [w for w in upper_line if w is not exclude_word]
        if not candidates:
            return None
        return min(candidates, key=lambda w: abs(w["xmin"] - target_word["xmin"]))

    def move_word_to_prev_line(lines, li, src_line, word):
        nonlocal move_count_total

        if li - 1 < 0:
            return False

        target_line = lines[li - 1]

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

    def try_rescue_to_upper_line(lines, li, src_line, move_target):
        if li - 1 < 0:
            return False

        upper_line = lines[li - 1]
        upper_line.sort(key=lambda x: x["xmin"])

        if not upper_line:
            return False
        if is_protected_line(upper_line):
            return False

        nearest_upper = nearest_upper_by_x(move_target, upper_line)
        if nearest_upper is None:
            return False

        rescue_result = calculate_horizontal_relation(nearest_upper, move_target, THR_K_HORIZ)
        if not rescue_result["is_same_line"]:
            return False

        return move_word_to_prev_line(lines, li, src_line, move_target)

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

                if len(line) < 2 or i >= len(line) - 1:
                    break

                left = line[i]
                curr = line[i + 1]

                left_protected = is_protected_header_word(left)
                curr_protected = is_protected_header_word(curr)

                result = calculate_horizontal_relation(left, curr, THR_K_HORIZ)
                if result["is_same_line"]:
                    i += 1
                    continue

                move_target = None

                if left_protected and curr_protected:
                    move_target = None
                elif curr_protected and not left_protected:
                    move_target = left
                else:
                    move_target = curr

                if move_target is None:
                    i += 1
                    continue

                rescued_up = try_rescue_to_upper_line(lines, li, line, move_target)
                if rescued_up:
                    if len(line) < 2:
                        break
                    continue

                moved = move_word_to_next_line(lines, li, line, move_target)
                if not moved:
                    i += 1
                    continue

                moves_in_this_line += 1

                if moves_in_this_line >= 200:
                    break

                if len(line) < 2:
                    break

                if curr_protected and not left_protected:
                    continue

                chain_anchor = move_target

                while i + 1 < len(line):
                    next_word = line[i + 1]

                    next_word_protected = is_protected_header_word(next_word)
                    chain_anchor_protected = is_protected_header_word(chain_anchor)

                    chain_result = calculate_horizontal_chain_relation(chain_anchor, next_word, THR_K_HORIZ)
                    if not chain_result["is_same_line"]:
                        break

                    chain_move_target = None

                    if chain_anchor_protected and next_word_protected:
                        chain_move_target = None
                    elif next_word_protected and not chain_anchor_protected:
                        chain_move_target = chain_anchor
                    else:
                        chain_move_target = next_word

                    if chain_move_target is None:
                        break

                    rescued_up_chain = try_rescue_to_upper_line(lines, li, line, chain_move_target)
                    if rescued_up_chain:
                        break

                    moved_chain = move_word_to_next_line(lines, li, line, chain_move_target)
                    if not moved_chain:
                        break

                    moves_in_this_line += 1

                    if moves_in_this_line >= 200:
                        break

                    if len(line) < 2:
                        break

                    if next_word_protected and not chain_anchor_protected:
                        break

                    chain_anchor = chain_move_target

            li += 1

        receipt["lines"] = [l for l in lines if l]

    return receipts, move_count_total


def vertical_refinement_pass(receipts: List[Dict[str, Any]]):
    move_count_total = 0

    def x_overlap(a, b):
        return (b["xmin"] <= a["xmax"]) and (b["xmax"] >= a["xmin"])

    def nearest_lower_by_x(anchor_word, lower_line):
        if not lower_line:
            return None
        return min(lower_line, key=lambda w: abs(w["xmin"] - anchor_word["xmin"]))

    for receipt in receipts:
        lines = receipt["lines"]
        idx = 0
        tail_section_started = False

        while idx < len(lines) - 1:
            upper_line = lines[idx]
            lower_line = lines[idx + 1]

            upper_line.sort(key=lambda x: x["xmin"])
            lower_line.sort(key=lambda x: x["xmin"])

            if not tail_section_started:
                if is_tail_section_start_line(upper_line) or is_tail_section_start_line(lower_line):
                    tail_section_started = True

            if not upper_line or not lower_line:
                idx += 1
                continue

            any_candidate_exists = False

            for uw in upper_line:
                cands = [lw for lw in lower_line if x_overlap(uw, lw)]
                if cands:
                    any_candidate_exists = True
                    break

            if not any_candidate_exists:
                if tail_section_started:
                    movable_words = []

                    for uw in list(upper_line):
                        if is_protected_header_word(uw):
                            continue
                        if uw.get("locked", False):
                            continue
                        movable_words.append(uw)

                    if is_protected_line(lower_line):
                        movable_words = []

                    if movable_words:
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

                else:
                    if is_protected_line(lower_line):
                        idx += 1
                        continue

                    upper_words_copy = list(upper_line)

                    for anchor_word in upper_words_copy:
                        if anchor_word not in upper_line:
                            continue
                        if is_protected_header_word(anchor_word):
                            continue
                        if anchor_word.get("locked", False):
                            continue

                        nearest_lower = nearest_lower_by_x(anchor_word, lower_line)
                        if nearest_lower is None:
                            continue

                        err, thr = calculate_vertical_relation(
                            anchor_word, nearest_lower, THR_K_VERT, True
                        )
                        if err > thr:
                            continue

                        upper_line.remove(anchor_word)
                        lower_line.append(anchor_word)
                        lower_line.sort(key=lambda x: x["xmin"])
                        move_count_total += 1
                        apply_move_and_lock(anchor_word)

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
                    err, thr = calculate_vertical_relation(
                        anchor_word, target_word, THR_K_VERT, True
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


def merge_receipts_by_page_order(
    receipts: List[Dict[str, Any]],
    merged_file_name: str = "receipt.json",
) -> Dict[str, Any]:
    merged_lines = []
    merged_from = []

    for receipt in receipts:
        merged_lines.extend(receipt.get("lines", []))
        merged_from.append(receipt.get("file_name"))

    return {
        "file_name": merged_file_name,
        "file_meta": {
            "merge_type": "page_no_merged",
            "is_merged_output": len(receipts) > 1,
            "merged_from": merged_from,
            "page_count": len(receipts),
        },
        "lines": merged_lines,
        "cut_meta": {},
    }


def get_end_section_priority(text):
    text = normalize_text(text)
    
    if text.startswith(normalize_text("결제대상금액")):
        return 1
    if text.startswith(normalize_text("제대상금액")):
        return 1
    if text.startswith(normalize_text("합계")):
        return 2
    if text.startswith(normalize_text("부가세")):
        return 3
    if text.startswith(normalize_text("과세")):
        return 4
    if text.startswith(normalize_text("면세")):
        return 5

    return None


def trim_receipt_body(receipts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:

    for receipt in receipts:
        lines = receipt.get("lines", [])

        if not lines:
            receipt["cut_meta"] = {
                "start_idx": None,
                "end_idx": None,
                "cut_applied": False,
            }
            continue

        line_texts = [line_to_plain_text(line) for line in lines]
        protected_idxs = [i for i, line in enumerate(lines) if is_protected_line(line)]

        start_idx = protected_idxs[0] if protected_idxs else 0

        end_idx = len(lines) - 1
        best_priority = None

        for i in range(start_idx, len(line_texts)):
            text = line_texts[i]
            priority = get_end_section_priority(text)

            if priority is None:
                continue

            if best_priority is None or priority < best_priority:
                best_priority = priority
                end_idx = i

                if priority == 1:
                    break

        receipt["lines"] = lines[start_idx:end_idx + 1]

        receipt["cut_meta"] = {
            "start_idx": start_idx,
            "end_idx": end_idx,
            "cut_applied": True,
        }

    return receipts


def _run_common_line_sorting_steps(receipts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    receipts = sort_words_by_y(receipts)
    receipts = group_words_into_lines(receipts)
    receipts = sort_words_in_each_line_by_x(receipts)
    receipts = merge_adjacent_start_header_lines(receipts)
    receipts = apply_protected_line_flags(receipts)

    for _ in range(MAX_REPASS_HORIZ):
        receipts, moved_h = horizontal_refinement_pass(receipts)
        if moved_h == 0:
            break

    for _ in range(MAX_REPASS_VERT):
        receipts, moved_v = vertical_refinement_pass(receipts)
        if moved_v == 0:
            break

    return receipts


def run_line_sorting_for_single_receipt_pages(
    page_ocr_jsons: List[Dict[str, Any]],
    receipt_file_name: str = "receipt.json",
) -> Dict[str, Any]:

    if not page_ocr_jsons:
        return {
            "file_name": receipt_file_name,
            "file_meta": {
                "merge_type": "page_no_merged",
                "is_merged_output": False,
                "merged_from": [],
                "page_count": 0,
            },
            "lines": [],
            "cut_meta": {
                "start_idx": None,
                "end_idx": None,
                "cut_applied": False,
            },
        }

    page_receipts = []

    for page in sorted(page_ocr_jsons, key=lambda x: x["page_no"]):
        page_no = page["page_no"]
        ocr_data = page["ocr_data"]

        pseudo_file_name = f"{receipt_file_name.replace('.json', '')}_page_{page_no}.json"

        receipt = load_clova_receipt_from_json_data(
            data=ocr_data,
            file_name=pseudo_file_name,
        )
        receipt["page_no"] = page_no
        page_receipts.append(receipt)

    page_receipts = _run_common_line_sorting_steps(page_receipts)
    page_receipts = sorted(page_receipts, key=lambda x: x.get("page_no", 0))

    merged_receipt = merge_receipts_by_page_order(
        page_receipts,
        merged_file_name=receipt_file_name,
    )

    trimmed_list = trim_receipt_body([merged_receipt])
    result = trimmed_list[0]
    
    result["lines_raw_tokens"] = result.get("lines", [])
    
    result["lines"] = convert_lines_to_plain_text(result.get("lines", []))
    
    return result