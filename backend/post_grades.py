import requests
import json
import time
import os
from pathlib import Path
from bs4 import BeautifulSoup

COURSE_ID = 1288622
SESSION_COOKIE = ""  # set GRADESCOPE_SESSION_COOKIE env var

session = requests.Session()

cookie_header = os.environ.get("GRADESCOPE_SESSION_COOKIE", SESSION_COOKIE)
for cookie in cookie_header.split('; '):
    name, _, value = cookie.partition('=')
    session.cookies.set(name.strip(), value.strip(), domain='www.gradescope.com')

def get_question_page(question_id):
    url = f"https://www.gradescope.com/courses/{COURSE_ID}/questions/{question_id}/answer_groups"
    resp = session.get(url)
    resp.raise_for_status()
    return resp

def get_csrf_token_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    token = soup.find("meta", {"name": "csrf-token"})
    if token is None:
        raise RuntimeError("Could not find CSRF token; session may be expired")
    return token["content"]

def get_csrf_token(question_id):
    resp = get_question_page(question_id)
    return get_csrf_token_from_html(resp.text)

def memberships_url(question_id):
    return f"https://www.gradescope.com/courses/{COURSE_ID}/questions/{question_id}/answer_group_memberships/many"

def memberships_headers(csrf_token):
    return {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrf_token,
        "X-Requested-With": "XMLHttpRequest",
    }

def clear_answer_group_memberships(question_id, submission_ids):
    if not submission_ids:
        return None

    csrf_token = get_csrf_token(question_id)
    data = {"answer_group_id": None, "submission_ids": submission_ids}
    return session.post(
        memberships_url(question_id),
        headers=memberships_headers(csrf_token),
        json=data,
    )

def submit_grades(question_id, answer_group_id, submission_ids):
    csrf_token = get_csrf_token(question_id)
    data = {"answer_group_id": answer_group_id, "submission_ids": submission_ids}
    return session.post(
        memberships_url(question_id),
        headers=memberships_headers(csrf_token),
        json=data,
    )

def submission_ids_by_question_for_file(requests_file, requests_data):
    requests_path = Path(requests_file)
    stem = requests_path.stem.removesuffix("_requests")
    submissions_path = requests_path.with_name(f"{stem}.json")

    by_question = {}
    if submissions_path.exists():
        with submissions_path.open() as f:
            submissions = json.load(f)
        for submission in submissions:
            by_question.setdefault(submission["question_id"], []).append(submission["id"])
        return by_question

    for request in requests_data:
        ids = by_question.setdefault(request["question_id"], set())
        ids.update(request.get("submission_ids", []))
    return {question_id: sorted(ids) for question_id, ids in by_question.items()}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Path to requests JSON file")
    args = parser.parse_args()

    with open(args.file, "r") as f:
        requests_data = json.load(f)

    submission_ids_by_question = submission_ids_by_question_for_file(args.file, requests_data)
    for question_id, submission_ids in sorted(submission_ids_by_question.items()):
        response = clear_answer_group_memberships(question_id, submission_ids)
        if response is None:
            print(f"clear {question_id}: no submissions")
        else:
            print(f"clear {question_id}: {response.status_code}")
            response.raise_for_status()
        time.sleep(1)

    for request in requests_data:
        response = submit_grades(**request)
        print(response.status_code)
        response.raise_for_status()
        time.sleep(1)
