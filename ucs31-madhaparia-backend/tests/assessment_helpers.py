"""Complete the public bounded follow-up contract with explicit test answers.

The original text and confirmed symptoms are replayed unchanged on each turn.
These answers are synthetic software-test inputs, not clinical evidence.
"""
from copy import deepcopy


def finish_followups(client, payload, *, headers=None):
    request = deepcopy(payload)
    request.setdefault("follow_up_answers", [])
    for _ in range(4):
        response = client.post("/predict", json=request, headers=headers)
        if response.status_code != 200:
            return response
        result = response.json()
        if result["status"] != "needs_follow_up":
            return response
        question = result["follow_up_question"]
        assert question["id"] not in {a["question_id"] for a in request["follow_up_answers"]}
        answer = "unknown" if question["id"] == "symptom_duration" else "no"
        assert answer in {option["value"] for option in question["options"]}
        request["follow_up_answers"].append({"question_id": question["id"], "answer": answer})
    raise AssertionError("Assessment exceeded its three-question limit")
