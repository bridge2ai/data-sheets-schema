"""Complete fake direct-judge replies for acceptance and request-identity tests."""
from data_sheets_schema.judge_contract import VERSION


def judge_reply(contract, rubric, project="P", method="method", metadata=None):
    items = []
    for key, rule in contract["items"].items():
        score = 0 if rule["applicable"] else None
        item = {"id": key if rubric == "rubric10" else int(key[1:]),
                "name": rule["name"],
                "applicable": rule["applicable"], "score": score,
                "max_score": rule["max_score"], "evidence": "No relevant evidence.",
                "unit_scores": [{"path": unit["path"], "score": score,
                                 "evidence": "No relevant evidence."}
                                for unit in contract["scope"]["units"]]}
        if not rule["applicable"]:
            item["na_reason"] = rule["evidence"]
        items.append(item)
    groups = []
    if rubric == "rubric10":
        for number in sorted({int(item["id"].split(".")[0][1:]) for item in items}):
            subset = [item for item in items if item["id"].startswith(f"E{number}.")]
            groups.append({"id": number, "sub_elements": subset, "element_score": 0,
                           "element_max": sum(item["max_score"] for item in subset)})
    else:
        for number in sorted({(item["id"] - 1) // 5 for item in items}):
            subset = [item for item in items if (item["id"] - 1) // 5 == number]
            groups.append({"name": f"Category {number + 1}", "questions": subset,
                           "category_score": 0, "category_max": sum(item["max_score"] for item in subset)})
    maximum = sum(rule["max_score"] for rule in contract["items"].values())
    return {"rubric": rubric, "version": VERSION, "project": project, "method": method,
            "elements" if rubric == "rubric10" else "categories": groups,
            "overall_score": {"total_points": 0, "max_points": maximum,
                              "percentage": 0 if maximum else None},
            "metadata": metadata or {}}
