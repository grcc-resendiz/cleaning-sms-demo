# Cleaning SMS Demo (Codespaces-only)

This project is designed to run **only in GitHub Codespaces**.

## What it does

- `POST /sms` for simulated SMS requests (via `/docs`)
- `GET /demo` for quick browser testing
- OpenAI-based intent extraction (required)
- SQLite-backed demo reservations
- Twilio support is optional
- Safe demo behavior when Twilio is not configured

## Exact GitHub Codespaces steps

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Create `.env` from the example:

   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and set `OPENAI_API_KEY` (required). Keep `DEMO_MODE=true` for demos.

4. Seed demo data:

   ```bash
   python seed.py
   ```

5. Run the API on host `0.0.0.0` port `8000`:

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. In Codespaces, open the forwarded port `8000` in the browser.

7. Test endpoints:

   - `/docs` (use `POST /sms` with JSON body)
   - `/demo?phone=%2B15551234567&message=I%20want%20to%20book%20a%20cleaning%20for%20Friday%20morning`

## Notes

- `OPENAI_API_KEY` is required.
- Twilio is optional.
- If `DEMO_MODE=true`, the app does not use Twilio at all.
- If Twilio credentials are missing, app still runs in demo-safe mode.
- In demo mode, outgoing replies are logged to terminal and returned in JSON.
