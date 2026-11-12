"""Tests for the AI Receptionist Agent (Project 8).

Run:
    python test_receptionist.py

Each test checks one behaviour. CSV files written by the agent
(leads.csv, booking_requests.csv, handover.csv) are deleted first
so every run starts clean.
"""

import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from receptionist import answer, new_session  # noqa: E402

for name in ("leads.csv", "booking_requests.csv", "handover.csv"):
    p = os.path.join(HERE, name)
    if os.path.exists(p):
        os.remove(p)

passed = failed = 0


def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"PASS  {name}")
    else:
        failed += 1
        print(f"FAIL  {name}")


def rows(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return list(csv.DictReader(f))


# 1. greeting
r = answer("Hello", new_session())
check("greeting in English", r["action"] == "greeting" and "Receptionist" in r["reply"])

# 2. fees in English — real numbers from clinic info only
r = answer("What are your fees?", new_session())
check("fees list real prices", r["action"] == "fees" and "1500" in r["reply"] and "2500" in r["reply"])

# 3. fees in Roman Urdu — reply comes back in Roman Urdu
r = answer("fees kitni hai?", new_session())
check("fees in Roman Urdu", r["action"] == "fees" and "Rs" in r["reply"])

# 4. timings
r = answer("What are your timings?", new_session())
check("timings quoted", r["action"] == "timings" and "Mon–Sat" in r["reply"])

# 5. doctors
r = answer("Which doctors are available?", new_session())
check("doctors listed", r["action"] == "doctors" and "Dr. Ayesha Khan" in r["reply"])

# 6. location
r = answer("Where is the clinic?", new_session())
check("location quoted", r["action"] == "location" and "Main Street" in r["reply"])

# 7. full booking flow in English — ends as a REQUEST, never confirmed
s = new_session()
r = answer("I want to book an appointment", s)
check("booking starts by asking service", r["action"] == "booking_service")
r = answer("General checkup", r["session"])
check("booking asks day + names doctor", r["action"] == "booking_day" and "Ayesha Khan" in r["reply"])
r = answer("Saturday", r["session"])
check("booking asks time slot", r["action"] == "booking_time" and "10:00 AM" in r["reply"])
r = answer("10:00 AM", r["session"])
check("booking asks name", r["action"] == "booking_name")
r = answer("Ayesha", r["session"])
check("booking asks phone", r["action"] == "booking_phone")
r = answer("03001234567", r["session"])
check("booking saved as REQUEST not confirmed",
      r["action"] == "booking_saved"
      and r["record"]["status"] == "REQUESTED_NOT_CONFIRMED"
      and "NOT a confirmed appointment" in r["reply"])
saved = rows(os.path.join(HERE, "booking_requests.csv"))
check("booking row written to csv",
      len(saved) == 1 and saved[0]["name"] == "Ayesha"
      and saved[0]["status"] == "REQUESTED_NOT_CONFIRMED")
leads = rows(os.path.join(HERE, "leads.csv"))
check("booking lead saved as grade A",
      len(leads) == 1 and leads[0]["grade"] == "A")

# 8. invalid time slot is refused, flow asks again
s = new_session()
answer("book appointment", s)
answer("Dental checkup", s)
answer("Friday", s)
r = answer("3:00 AM", s)
check("invalid slot refused", r["action"] == "booking_time" and "not available" in r["reply"])

# 9. symptoms: no diagnosis, handover to a doctor
r = answer("I have fever and pain", new_session())
check("symptom goes to handover, no diagnosis",
      r["action"] == "handover_medical" and "consultation" in r["reply"].lower())

# 10. unknown question: handover, never a guess
r = answer("Do you sell vitamins?", new_session())
check("unknown question handed over",
      r["action"] == "handover_unknown" and "staff" in r["reply"].lower())
hand = rows(os.path.join(HERE, "handover.csv"))
check("handover rows saved", len(hand) >= 2)

# 11. cancel / reschedule is a request for the team
r = answer("I want to cancel my appointment", new_session())
check("cancel saved as request", r["action"] == "handover_cancel")

# 12. asking for a human hands over
r = answer("I want to speak to staff", new_session())
check("human request handed over", r["action"] == "handover_human")

# 13. Roman Urdu booking start
r = answer("appointment book karni hai", new_session())
check("booking starts in Roman Urdu",
      r["action"] == "booking_service" and "Konsi service" in r["reply"])

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
