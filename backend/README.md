# Backend

Run locally with:

```bash
uvicorn app.main:app --app-dir backend --reload
```
Run smoke tests with:

```bash
python -m unittest backend.tests.test_api
```