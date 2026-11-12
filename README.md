# AI Receptionist Agent — Project 8

A 24-hour receptionist for a clinic or small business. It answers
callers/messages in English or Roman Urdu, using **only** the clinic
info in `clinic_info.json`. It never invents a fee, timing, doctor
or address, never diagnoses symptoms, and never confirms a booking.

## What it does

1. **Greeting** — introduces itself and what it can do.
2. **Fees, timings, doctors, location** — quoted from clinic info only.
3. **Booking flow** — service → doctor → day → time slot → name →
   phone. Saved to `booking_requests.csv` as
   `REQUESTED_NOT_CONFIRMED`. A real booking needs the clinic's
   real calendar, which is not connected here.
4. **Cancel / reschedule** — saved as a request for the team.
5. **Message taking** — "speak to staff" saves a message for a callback.
6. **Lead capture** — every caller is saved to `leads.csv` with a
   grade: **A** = booking requested, **B** = asked about
   fees/timings/doctors, **C** = general question only.
7. **Human handover** — medical questions, or anything it cannot
   answer, go to `handover.csv` and the caller is told staff will
   call back. No guessing.

## Honest limits (demo only)

- **Rule-based, Python standard library only. No LLM** — answers
  are matched from fed clinic info, not generated text.
- **No phone or WhatsApp connection.** A real clinic would connect
  its own phone line / WhatsApp Business number.
- **Bookings are requests, not confirmed appointments.**
- The clinic in `clinic_info.json` (City Care Clinic) is a
  **sample / fictional clinic** — fees, doctors and timings are
  sample data, not a real client.

## Run

```bash
pip install -r requirements.txt
python test_receptionist.py   # runs the test scenarios
uvicorn app:app --reload      # POST /message {"message": "...", "session_id": "..."}
```

## Files

- `receptionist.py` — the agent (intent routing + booking flow)
- `clinic_info.json` — sample clinic data (fictional)
- `app.py` — FastAPI demo
- `test_receptionist.py` — test scenarios
- `requirements.txt` — fastapi, uvicorn

MIT License.
