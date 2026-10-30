import base64, json, os, subprocess, sys, tempfile, urllib.request, urllib.error
from datetime import date
from pathlib import Path

OWNER = "eDDie-05"
API = "https://api.github.com"
PROJECTS = [
    ("budget-buddy", "Budget Buddy", "Budget calculations and remaining-balance checks.",
     "def total_spending(items):\n    if any(v < 0 for v in items.values()): raise ValueError('Negative amount')\n    return round(sum(items.values()), 2)\n\ndef remaining_budget(budget, items):\n    if budget < 0: raise ValueError('Negative budget')\n    return round(budget - total_spending(items), 2)\n",
     "from app import total_spending, remaining_budget\nassert total_spending({'food': 12.5, 'bus': 7.5}) == 20.0\nassert remaining_budget(100, {'food': 25}) == 75\n"),
    ("study-flashcards", "Study Flashcards", "Answer checking and revision-session accuracy.",
     "def check_answer(expected, submitted):\n    return expected.strip().casefold() == submitted.strip().casefold()\n\ndef accuracy(correct, attempted):\n    if attempted < 0 or correct < 0 or correct > attempted: raise ValueError('Invalid counts')\n    return 0.0 if attempted == 0 else round(correct / attempted * 100, 1)\n",
     "from app import check_answer, accuracy\nassert check_answer('CPU', ' cpu ')\nassert accuracy(3, 4) == 75.0\nassert accuracy(0, 0) == 0.0\n"),
    ("stockroom-lite", "Stockroom Lite", "Inventory balances and reorder-level warnings.",
     "def stock_balance(opening, received, issued):\n    if min(opening, received, issued) < 0: raise ValueError('Negative quantity')\n    balance = opening + received - issued\n    if balance < 0: raise ValueError('Insufficient stock')\n    return balance\n\ndef needs_reorder(balance, reorder_level):\n    if min(balance, reorder_level) < 0: raise ValueError('Negative quantity')\n    return balance <= reorder_level\n",
     "from app import stock_balance, needs_reorder\nassert stock_balance(20, 8, 17) == 11\nassert needs_reorder(10, 10)\ntry: stock_balance(2, 0, 3)\nexcept ValueError: pass\nelse: raise AssertionError('Negative stock was accepted')\n"),
    ("quiz-score-engine", "Quiz Score Engine", "Quiz answer scoring and percentage results.",
     "def score_quiz(correct, submitted):\n    if len(correct) != len(submitted): raise ValueError('Answer lengths differ')\n    return sum(a.strip().casefold() == b.strip().casefold() for a, b in zip(correct, submitted))\n\ndef percentage(score, total):\n    if total < 0 or score < 0 or score > total: raise ValueError('Invalid score')\n    return 0.0 if total == 0 else round(score / total * 100, 1)\n",
     "from app import score_quiz, percentage\nassert score_quiz(['A','B'], ['a','c']) == 1\nassert percentage(2, 4) == 50.0\n"),
    ("unit-converter-kit", "Unit Converter Kit", "Metric and imperial temperature, distance, and weight conversions.",
     "def celsius_to_fahrenheit(value): return round(value * 9 / 5 + 32, 2)\ndef kilometres_to_miles(value): return round(value * 0.621371, 3)\ndef kilograms_to_pounds(value): return round(value * 2.204623, 3)\n",
     "from app import celsius_to_fahrenheit, kilometres_to_miles, kilograms_to_pounds\nassert celsius_to_fahrenheit(0) == 32\nassert kilometres_to_miles(1) == 0.621\nassert kilograms_to_pounds(1) == 2.205\n"),
    ("habit-streak-tracker", "Habit Streak Tracker", "Current and longest completion streak calculations.",
     "def current_streak(history):\n    count = 0\n    for done in reversed(history):\n        if not isinstance(done, bool): raise ValueError('Entries must be boolean')\n        if not done: break\n        count += 1\n    return count\n\ndef longest_streak(history):\n    best = run = 0\n    for done in history:\n        if not isinstance(done, bool): raise ValueError('Entries must be boolean')\n        run = run + 1 if done else 0\n        best = max(best, run)\n    return best\n",
     "from app import current_streak, longest_streak\nassert current_streak([True, False, True, True]) == 2\nassert longest_streak([True, True, False, True, True, True]) == 3\n"),
    ("contact-search-book", "Contact Search Book", "Case-insensitive contact search by name or email.",
     "def make_contact(name, email):\n    name, email = name.strip(), email.strip()\n    if not name or '@' not in email: raise ValueError('Name and valid-looking email required')\n    return {'name': name, 'email': email}\n\ndef search_contacts(contacts, query):\n    term = query.strip().casefold()\n    if not term: return []\n    return [c for c in contacts if term in c.get('name', '').casefold() or term in c.get('email', '').casefold()]\n",
     "from app import make_contact, search_contacts\npeople = [make_contact('Amina', 'amina@example.com')]\nassert len(search_contacts(people, 'AMIN')) == 1\nassert len(search_contacts(people, 'example.com')) == 1\n"),
]

def api(method, url, token, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Accept": "application/vnd.github+json", "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "eDDie-Daily-Project-Factory",
        "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            return r.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError("GitHub API " + str(e.code) + ": " + e.read().decode()) from e

def main():
    today = date.today()
    slug, title, summary, app, tests = PROJECTS[(today - date(2026, 10, 30)).days % len(PROJECTS)]
    repo = "daily-" + today.strftime("%Y%m%d") + "-" + slug
    readme = "# " + title + "\n\n" + summary + "\n\n## Features\n- Distinct project functionality\n- Input validation where applicable\n- Automated tests\n\n## Run\n\n    python app.py\n\n## Test\n\n    python -m unittest discover -s tests -v\n\nRequires Python 3.10+. Uses only the standard library.\n\nGenerated for " + today.isoformat() + ". Starter project; extend it with persistence and a UI.\n"
    files = {"README.md": readme, "app.py": app, "tests/test_app.py": tests,
             ".gitignore": "__pycache__/\n*.py[cod]\n.venv/\n.env\n"}
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        for name, content in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                                cwd=root, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError("Generated project tests failed: " + result.stdout + result.stderr)
    if os.getenv("DRY_RUN") == "1":
        print("DRY RUN PASSED: " + repo)
        return
    token = os.getenv("GH_TOKEN")
    if not token:
        raise RuntimeError("Missing GH_TOKEN Actions secret.")
    status, _ = api("GET", API + "/repos/" + OWNER + "/" + repo, token)
    if status == 200:
        print("Today's repository already exists; skipping: https://github.com/" + OWNER + "/" + repo)
        return
    _, created = api("POST", API + "/user/repos", token, {
        "name": repo, "description": summary, "private": False, "auto_init": True,
        "has_issues": True, "has_projects": False, "has_wiki": False})
    for path, content in files.items():
        payload = {"message": "Add " + path + " for " + title,
                   "content": base64.b64encode(content.encode()).decode(), "branch": "main"}
        api("PUT", API + "/repos/" + OWNER + "/" + repo + "/contents/" + path, token, payload)
    print("Published " + created.get("html_url", "https://github.com/" + OWNER + "/" + repo))
    print("Project tests passed before publishing.")

if __name__ == "__main__":
    main()
