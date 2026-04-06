def interpret_receipt(parsed_receipt, store: str):
    """
    store에 따라 적절한 interpreter로 라우팅

    Args:
        parsed_receipt (dict): parser output
        store (str): "costco" | "emart" | "hanaro"

    Returns:
        dict: semantic interpreted result
    """

    store = (store or "").lower()

    if store == "costco":
        from .costco_interpreter import interpret_receipt as interpret
    elif store == "emart":
        from .emart_interpreter import interpret_receipt as interpret
    elif store == "hanaro":
        from .hanaro_interpreter import interpret_receipt as interpret
    else:
        raise ValueError(f"[semantic_manager] Unsupported store: {store}")

    return interpret(parsed_receipt)