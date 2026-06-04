# Solutions Guide (Mentor Reference)

Use this to evaluate intern submissions. Each solution shows the minimal correct change.

---

## Module 1 — Add `priority` field to tasks

**File:** `app/app.py`

Change `create_task()` to accept and store a `priority` field:

```python
@app.route("/api/tasks", methods=["POST"])
def create_task():
    data = request.get_json()
    if not data or not data.get("title"):
        return jsonify({"error": "Title is required"}), 400

    # ✅ Accept priority, default to "medium" if not provided
    priority = data.get("priority", "medium")
    if priority not in ("low", "medium", "high"):
        return jsonify({"error": "priority must be low, medium, or high"}), 400

    tasks = load_tasks()
    task = {
        "id": len(tasks) + 1,
        "title": data["title"],
        "priority": priority,          # ← new field
        "done": False,
        "created_at": datetime.utcnow().isoformat(),
    }
    tasks.append(task)
    save_tasks(tasks)
    return jsonify(task), 201
```

**What to check in intern's solution:**
- [ ] Priority stored in the task dict
- [ ] Validation rejects invalid values (not just any string)
- [ ] Default value used when priority is absent
- [ ] A test was written for each priority value

---

## Module 2 — Change WORKDIR in Dockerfile

**What the intern should discover:** Changing `WORKDIR` alone works because paths inside the container are relative. The app still runs because `CMD` references `app:app` (Python module), not a hardcoded path.

**Correct answer explanation:**

```dockerfile
# Original
WORKDIR /app

# Changed to — app still works because gunicorn finds app.py via Python's import
WORKDIR /taskapp
```

Rebuild command:
```bash
docker build -t devops-task-app:workdir-test .
docker run -d -p 5000:5000 devops-task-app:workdir-test
curl http://localhost:5000/health   # should still return 200
```

**What to check:**
- [ ] Intern actually rebuilt the image (not just restarted old one)
- [ ] They verified with `curl` or browser, not just assumed it worked
- [ ] Bonus: they ran `docker exec -it <container> sh` and confirmed the path changed inside

---

## Module 3 — Add Redis to docker-compose.yml

**File:** `docker-compose.yml`

```yaml
services:
  app:
    # ... existing config ...
    environment:
      - REDIS_URL=redis://cache:6379/0    # ← tell app where Redis is
    depends_on:
      cache:                              # ← wait for redis too
        condition: service_started

  nginx:
    # ... unchanged ...

  # ✅ New service
  cache:
    image: redis:7-alpine
    container_name: redis-cache
    ports:
      - "6379:6379"                       # optional: expose for debugging
    networks:
      - app-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

volumes:
  task_data:

networks:
  app-network:
    driver: bridge
```

**What to check:**
- [ ] Redis is on the same `app-network` — without this, `app` can't reach it
- [ ] Service name used in URL is `cache` (matches service key), not `localhost`
- [ ] Healthcheck added (bonus — shows they read the existing compose file pattern)
- [ ] `depends_on` updated in `app` service

---

## Module 4 — Add APP_TITLE env variable

**File 1:** `.env.example`
```
APP_TITLE=My Task Manager
```

**File 2:** `app/app.py` — pass it to the template:
```python
APP_TITLE = os.getenv("APP_TITLE", "DevOps Task Manager")

@app.route("/")
def index():
    return render_template(
        "index.html",
        version=APP_VERSION,
        environment=ENVIRONMENT,
        app_title=APP_TITLE,            # ← pass to template
    )
```

**File 3:** `app/templates/index.html` — use the variable:
```html
<!-- Change the hardcoded title -->
<title>{{ app_title }}</title>

<!-- And in the header -->
<h1>{{ app_title }}</h1>
```

**What to check:**
- [ ] Variable read with `os.getenv()` with a sensible default (not hardcoded)
- [ ] Added to `.env.example` (not `.env` — that file is gitignored)
- [ ] Passed through `render_template()` to HTML
- [ ] Both `<title>` and visible header updated (not just one)

---

## Module 5 — Add /status location in nginx.conf

**File:** `nginx/nginx.conf`

```nginx
server {
    listen 80;
    server_name localhost;

    # ✅ New: Nginx responds directly — Flask never sees this request
    location /status {
        return 200 "nginx is up\n";
        add_header Content-Type text/plain;
    }

    location / {
        proxy_pass         http://flask_app;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;
    }

    location /health {
        proxy_pass http://flask_app/health;
        access_log off;
    }
}
```

Test it:
```bash
curl http://localhost/status        # should print: nginx is up
curl http://localhost:5000/status   # should return 404 (Flask doesn't know this route)
```

**What to check:**
- [ ] `return 200` used — not `proxy_pass` (that would defeat the purpose)
- [ ] `Content-Type` header set — otherwise browsers may misinterpret it
- [ ] Intern verified Flask returns 404 on port 5000 (proving nginx handles it)
- [ ] After editing, they restarted nginx: `docker compose restart nginx`

---

## Module 6 — Health check returns task count

**File:** `app/app.py`

```python
@app.route("/health")
def health():
    tasks = load_tasks()
    return jsonify({
        "status": "healthy",
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
        "task_count": len(tasks),                           # ← readiness data
        "completed_count": sum(1 for t in tasks if t["done"]),
    })
```

Test:
```bash
curl http://localhost:5000/health
# Expected:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "environment": "development",
#   "task_count": 3,
#   "completed_count": 1
# }
```

**What to check:**
- [ ] `task_count` is accurate (add a few tasks, re-check)
- [ ] No crash when no tasks exist yet (empty list = 0, not exception)
- [ ] Bonus: a test was updated to assert `task_count` is in the response

---

## Module 7 — Add notify job to CI/CD pipeline

**File:** `.github/workflows/ci-cd.yml`

```yaml
  # ── Job 4: Notify ────────────────────────────────────────────────────────────
  notify:
    name: Notify on Success
    runs-on: ubuntu-latest
    needs: deploy                        # ← runs only after deploy succeeds
    if: success()                        # ← skips if any earlier job failed

    steps:
      - name: Set version
        run: echo "VERSION=$(echo $GITHUB_SHA | cut -c1-7)" >> $GITHUB_ENV

      - name: Send success notification
        run: |
          echo "Deployment successful! Version: $VERSION"
          echo "Deployed by: $GITHUB_ACTOR"
          echo "Branch: $GITHUB_REF_NAME"
          echo "Commit: $GITHUB_SHA"
          # In a real project, replace the above with:
          # curl -X POST ${{ secrets.SLACK_WEBHOOK_URL }} \
          #   -H 'Content-type: application/json' \
          #   --data '{"text":"Deployed ${{ env.VERSION }} successfully!"}'
```

**What to check:**
- [ ] `needs: deploy` — not `needs: build` (must wait for full deploy)
- [ ] `if: success()` condition present
- [ ] VERSION env var set before use (not just referenced blind)
- [ ] Bonus: they added a Slack/email notification (shows initiative)

---

## Module 8 — Test for deleting nonexistent task

**File:** `app/tests/test_app.py`

```python
def test_cannot_delete_nonexistent_task(client):
    # Try to delete a task that was never created
    res = client.delete("/api/tasks/999")
    # ⚠️  The current app returns 200 even for missing tasks!
    # The intern must ALSO fix app.py to return 404.
    assert res.status_code == 404
```

**The intern must also fix the delete route in `app/app.py`:**

```python
@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    tasks = load_tasks()
    original_count = len(tasks)
    tasks = [t for t in tasks if t["id"] != task_id]

    # ✅ Return 404 if nothing was actually removed
    if len(tasks) == original_count:
        return jsonify({"error": "Task not found"}), 404

    save_tasks(tasks)
    return jsonify({"message": "Task deleted"})
```

**This is the most important challenge** — it requires the intern to:
1. Write a failing test first
2. Discover the bug in the app
3. Fix the app
4. Confirm the test now passes

**What to check:**
- [ ] Test written AND app.py fixed (test alone is not enough)
- [ ] Test actually runs: `pytest tests/ -v` passes
- [ ] They didn't just change the assert to `200` to make the test pass

---

## Evaluation Scorecard

Use this when reviewing intern submissions:

| Module | Max Score | Criteria |
|---|---|---|
| 1 — Priority field | 10 | Validation + default + test |
| 2 — WORKDIR change | 5 | Rebuilt + verified with curl |
| 3 — Redis service | 10 | Correct network + healthcheck |
| 4 — APP_TITLE | 10 | env var + template + .env.example |
| 5 — Nginx /status | 10 | return 200 + Content-Type + verification |
| 6 — Health task count | 10 | Correct count + no crash on empty |
| 7 — Notify job | 10 | needs + if:success() + VERSION set |
| 8 — Delete 404 test | 15 | Test + app fix + test passes |
| Git workflow | 10 | Feature branches used (not committing to main) |
| Code quality | 10 | Clean, no commented-out code, sensible names |
| **Total** | **100** | |

**Passing score: 70/100**
