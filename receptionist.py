"""AI Receptionist Agent — Project 8 (rule-based demo).

A 24-hour receptionist for a clinic or small business. It answers
calls/messages in English or Roman Urdu, using ONLY the clinic info
in clinic_info.json. It never invents a fee, timing, doctor or
address, never diagnoses symptoms, and never confirms a booking:
a booking is always saved as a REQUEST for the clinic team to
confirm.

What it does:
1. Greeting + menu of what it can do.
2. Fees, timings, doctors and location — quoted from clinic info.
3. Booking flow: service -> doctor -> day -> time slot -> name ->
   phone -> saved as REQUESTED_NOT_CONFIRMED.
4. Cancel / reschedule: saved as a request for the team.
5. Message taking: after-hours or "speak to staff" saves a message
   for a callback.
6. Lead capture: every caller is saved to leads.csv with a grade
   (A = booking requested, B = asked about fees/timings/doctors,
   C = general question only).
7. Human handover: anything medical, or anything it cannot answer,
   is saved to handover.csv and the caller is told staff will call
   back. No guessing.

Rule-based, Python standard library only. No LLM, no phone or
WhatsApp connection — a real clinic would connect its own phone
line / WhatsApp Business number. The clinic in clinic_info.json
is a SAMPLE / FICTIONAL clinic for demo only.

Run the tests:
    python test_receptionist.py
"""

import csv
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "clinic_info.json")) as f:
    CLINIC = json.load(f)

TIME_SLOTS = CLINIC["time_slots"]
DOCTORS = CLINIC["doctors"]
SERVICES = CLINIC["services"]

LEADS_FILE = os.path.join(HERE, "leads.csv")
BOOKINGS_FILE = os.path.join(HERE, "booking_requests.csv")
HANDOVER_FILE = os.path.join(HERE, "handover.csv")

URDU_MARKERS = ["kitne", "kitna", "kab", "kahan", "kaisa", "kaisi", "chahiye",
                "batao", "bataein", "shukriya", "meherbani", "aap", "mujhe",
                "hai?", "hain?", "ka", "ki ", "ko ", "se ", "pe ", "mein",
                "nahi", "nahin", "zaroor", "theek", "acha", "acha,"]

GREETING = re.compile(r"\b(hi|hello|hey|salam|assalam|aoa|good morning|good afternoon|good evening)\b", re.I)
FEES = re.compile(r"\b(fee|fees|price|prices|pricing|cost|charge|charges|rate|kitne|kitna|paisa)\b", re.I)
TIMINGS = re.compile(r"\b(timing|timings|hours|open|close|closed|kab|khula|khulta|time table|schedule)\b", re.I)
DOCTOR_RE = re.compile(r"\b(doctor|doctors|dr\.?|physician|dentist|dental|skin|specialist|consultant)\b", re.I)
LOCATION = re.compile(r"\b(location|address|kahan|direction|directions|map|reach|pohanch|raasta|where|located|situated)\b", re.I)
BOOK = re.compile(r"\b(book|booking|appointment|slot|reserve|time lena|lena hai|book kar)\b", re.I)
CANCEL = re.compile(r"\b(cancel|reschedule|change|postpone|shift|move my)\b", re.I)
HUMAN = re.compile(r"\b(human|staff|receptionist|manager|someone real|call back|callback|baat karni|insan)\b", re.I)
SYMPTOM = re.compile(r"\b(fever|pain|hurt|hurts|ache|dizzy|vomit|bleed|rash|infection|cough|cold|flu|bp|diabetes|sugar|treatment|medicine|dawa|bukhar|dard)\b", re.I)
YES = re.compile(r"^\s*(yes|yeah|yep|ji|han|haan|ha|ok|okay|theek hai|sure)\b", re.I)
NO = re.compile(r"^\s*(no|nahi|nahin|nope|not now)\b", re.I)


def is_urdu(text):
    t = " " + text.lower() + " "
    return any(m in t for m in URDU_MARKERS)


def _save_row(path, fieldnames, row):
    exists = os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            w.writeheader()
        w.writerow(row)


def save_lead(name, phone, concern, grade):
    _save_row(LEADS_FILE, ["name", "phone", "concern", "grade"],
              {"name": name or "", "phone": phone or "",
               "concern": concern or "", "grade": grade})


def save_booking(booking):
    _save_row(BOOKINGS_FILE,
              ["name", "phone", "service", "doctor", "day", "time", "status"],
              {**booking, "status": "REQUESTED_NOT_CONFIRMED"})


def save_handover(name, phone, reason, message):
    _save_row(HANDOVER_FILE, ["name", "phone", "reason", "message"],
              {"name": name or "", "phone": phone or "",
               "reason": reason, "message": message})


def _find_service(text):
    t = text.lower()
    for s in SERVICES:
        name = s["name"].lower()
        key = name.split("(")[0].strip()
        if key in t or name in t:
            return s["name"]
    if "general" in t or "checkup" in t or "check up" in t:
        return "General checkup"
    if "dental" in t or "teeth" in t or "daant" in t:
        return "Dental checkup"
    if "skin" in t:
        return "Skin consultation"
    if "blood" in t or "cbc" in t:
        return "Blood test (CBC)"
    if "ecg" in t:
        return "ECG"
    return None


def _find_doctor(text, service=None):
    t = text.lower()
    for d in DOCTORS:
        if d["name"].lower() in t:
            return d
        if service and d["service"].lower() == service.lower():
            return d
    if "ayesha" in t:
        return DOCTORS[0]
    if "bilal" in t:
        return DOCTORS[1]
    if "sara" in t:
        return DOCTORS[2]
    return None


def _find_slot(text):
    t = text.lower()
    for slot in TIME_SLOTS:
        if slot.lower() in t:
            return slot
    m = re.search(r"\b(10|11|1|4|5|7)\s*(?::00)?\s*(am|pm)?\b", t)
    if m:
        hour, ap = int(m.group(1)), (m.group(2) or ("am" if m.group(1) in ("10", "11") else "pm"))
        cand = f"{hour}:00 {ap.upper()}"
        if cand in TIME_SLOTS:
            return cand
        if hour == 1 and ap == "pm":
            return "1:00 PM"
        if hour == 11 and ap == "am":
            return "11:30 AM"
    return None


def _fees_text(urdu):
    lines = [f"{s['name']}: Rs {s['fee']}" for s in SERVICES]
    if urdu:
        return ("City Care Clinic ki fees:\n" + "\n".join(lines) +
                "\nYe starting fees hain — final fee consultation par confirm hoti hai.")
    return ("City Care Clinic fees:\n" + "\n".join(lines) +
            "\nThese are starting fees — the final fee is confirmed at consultation.")


def _timings_text(urdu):
    if urdu:
        return (f"Clinic {CLINIC['hours']}\n"
                "Doctor ke timings alag hain — kis doctor ka time chahiye?")
    return (f"Clinic hours: {CLINIC['hours']}\n"
            "Doctors keep their own timings — which doctor's time do you need?")


def _doctors_text(urdu):
    lines = [f"{d['name']} ({d['role']}) — {d['service']}, {d['days']}, {d['time']}, Rs {d['fee']}"
             for d in DOCTORS]
    if urdu:
        return "Hamare doctors:\n" + "\n".join(lines)
    return "Our doctors:\n" + "\n".join(lines)


def _location_text(urdu):
    if urdu:
        return (f"Clinic ka address: {CLINIC['address']}\n"
                f"WhatsApp: {CLINIC['phone']}")
    return (f"Clinic address: {CLINIC['address']}\n"
            f"WhatsApp: {CLINIC['phone']}")


def _greeting_text(urdu):
    if urdu:
        return ("Assalam-o-Alaikum! City Care Clinic ki AI Receptionist bol rahi hai. "
                "Main aapki madad kar sakti hoon: fees, timings, doctors, address, "
                "ya appointment ki request. Aapko kis cheez me madad chahiye?")
    return ("Hello! This is the City Care Clinic AI Receptionist. "
            "I can help with fees, timings, doctors, location, "
            "or a booking request. What do you need help with?")


def new_session():
    return {"step": None, "service": None, "doctor": None,
            "day": None, "time": None, "name": None, "phone": None,
            "grade": "C", "concern": ""}


def answer(message, session=None):
    """Answer one caller message. Returns a dict:
    action, reply, and (when something was saved) the saved record."""
    session = session if session is not None else new_session()
    text = (message or "").strip()
    urdu = is_urdu(text)
    low = text.lower()

    # --- booking flow in progress: fill the next missing slot ---
    step = session.get("step")
    if step:
        if step == "service":
            service = _find_service(text)
            if service:
                session["service"] = service
                session["doctor"] = _find_doctor(text, service)
                session["step"] = "day"
                d = session["doctor"]
                extra = (f" {d['name']} ({d['role']}) {d['days']}, {d['time']} par hote hain."
                         if urdu and d else
                         f" {d['name']} ({d['role']}) is available {d['days']}, {d['time']}."
                         if d else "")
                q = ("Kis din aana chahenge?" if urdu else "Which day would you like to come?")
                return {"action": "booking_day", "reply": q + extra, "session": session}
            return {"action": "booking_service",
                    "reply": ("Samajh nahi aaya — General checkup, Dental checkup, Skin consultation, "
                              "Blood test ya ECG? (Konsi service chahiye?)"
                              if urdu else
                              "I didn't catch that — General checkup, Dental checkup, Skin consultation, "
                              "Blood test or ECG? Which service do you need?"),
                    "session": session}
        if step == "day":
            session["day"] = text
            session["step"] = "time"
            slots = ", ".join(TIME_SLOTS)
            q = ("Kis time aana chahenge? Time slots: " if urdu else
                 "What time would you like? Time slots: ")
            return {"action": "booking_time", "reply": q + slots, "session": session}
        if step == "time":
            slot = _find_slot(text)
            if slot:
                session["time"] = slot
                session["step"] = "name"
                q = "Aapka naam kya hai?" if urdu else "What is your name?"
                return {"action": "booking_name", "reply": q, "session": session}
            return {"action": "booking_time",
                    "reply": ("Wo slot available nahi hai. Time slots: " if urdu else
                              "That slot is not available. Time slots: ") + ", ".join(TIME_SLOTS),
                    "session": session}
        if step == "name":
            session["name"] = text
            session["step"] = "phone"
            q = "Aapka phone / WhatsApp number kya hai?" if urdu else "What is your phone / WhatsApp number?"
            return {"action": "booking_phone", "reply": q, "session": session}
        if step == "phone":
            session["phone"] = text
            booking = {"name": session["name"], "phone": session["phone"],
                       "service": session["service"],
                       "doctor": (session["doctor"] or {}).get("name", "Any available doctor"),
                       "day": session["day"], "time": session["time"]}
            save_booking(booking)
            save_lead(session["name"], session["phone"],
                      f"Booking request: {booking['service']} with {booking['doctor']}", "A")
            session["step"] = None
            if urdu:
                reply = (f"Shukriya {booking['name']}! Aapki booking REQUEST note kar li gayi hai:\n"
                         f"{booking['service']} — {booking['doctor']}\n"
                         f"{booking['day']}, {booking['time']}\n"
                         "Ye confirmed appointment NAHI hai — clinic team aapko WhatsApp/call par confirm karegi.")
            else:
                reply = (f"Thank you {booking['name']}! Your booking REQUEST has been noted:\n"
                         f"{booking['service']} — {booking['doctor']}\n"
                         f"{booking['day']}, {booking['time']}\n"
                         "This is NOT a confirmed appointment — the clinic team will confirm it with you on WhatsApp/call.")
            return {"action": "booking_saved", "reply": reply,
                    "record": {**booking, "status": "REQUESTED_NOT_CONFIRMED"},
                    "session": session}

    # --- fresh intents ---
    if not text:
        return {"action": "greeting", "reply": _greeting_text(urdu), "session": session}

    if GREETING.search(text) and len(text) < 30:
        return {"action": "greeting", "reply": _greeting_text(urdu), "session": session}

    if SYMPTOM.search(text):
        save_handover(session.get("name"), session.get("phone"),
                      "medical_question", text)
        session["grade"] = "B"
        return {"action": "handover_medical",
                "reply": ("Main symptoms par mashwara nahi de sakti — iske liye doctor se consultation zaroori hai. "
                          "Kya main aapki consultation ki request book kar dun? Ya clinic team aapko call back kare?"
                          if urdu else
                          "I can't judge symptoms or suggest treatment here — a doctor should look at this. "
                          "Shall I book a consultation request for you, or should the clinic team call you back?"),
                "session": session}

    if CANCEL.search(text):
        save_handover(session.get("name"), session.get("phone"),
                      "cancel_or_reschedule", text)
        return {"action": "handover_cancel",
                "reply": ("Theek hai — aapki cancel/reschedule ki request note kar li gayi hai, clinic team aapko confirm karegi. "
                          "Apna naam aur phone number bhej dein taake team aapko call back kar sake."
                          if urdu else
                          "Noted — your cancel/reschedule request is saved and the clinic team will confirm it. "
                          "Please share your name and phone number so the team can call you back."),
                "session": session}

    if HUMAN.search(text):
        save_handover(session.get("name"), session.get("phone"),
                      "asked_for_human", text)
        return {"action": "handover_human",
                "reply": ("Zaroor — maine aapka message staff ke liye save kar diya hai, team aapko call back karegi. "
                          "Apna naam aur phone number bhej dein."
                          if urdu else
                          "Of course — I've saved your message for the staff and the team will call you back. "
                          "Please share your name and phone number."),
                "session": session}

    if FEES.search(text):
        session["grade"] = "B"
        session["concern"] = "fees"
        return {"action": "fees", "reply": _fees_text(urdu), "session": session}

    if TIMINGS.search(text):
        session["grade"] = "B"
        session["concern"] = "timings"
        return {"action": "timings", "reply": _timings_text(urdu), "session": session}

    if DOCTOR_RE.search(text):
        session["grade"] = "B"
        session["concern"] = "doctors"
        return {"action": "doctors", "reply": _doctors_text(urdu), "session": session}

    if LOCATION.search(text):
        session["grade"] = "B"
        session["concern"] = "location"
        return {"action": "location", "reply": _location_text(urdu), "session": session}

    if BOOK.search(text):
        session["step"] = "service"
        session["grade"] = "A"
        return {"action": "booking_service",
                "reply": ("Zaroor! Konsi service chahiye — General checkup, Dental checkup, Skin consultation, "
                          "Blood test ya ECG?"
                          if urdu else
                          "Of course! Which service do you need — General checkup, Dental checkup, Skin consultation, "
                          "Blood test or ECG?"),
                "session": session}

    # unknown: hand over, never guess
    save_handover(session.get("name"), session.get("phone"), "unknown_question", text)
    return {"action": "handover_unknown",
            "reply": ("Maaf kijiye, is sawal ka jawab mere paas nahi hai. Maine aapka message staff ke liye save kar diya hai — "
                      "clinic team aapko call back karegi. Apna naam aur number bhej dein."
                      if urdu else
                      "Sorry, I don't have an answer for that. I've saved your message for the staff — "
                      "the clinic team will call you back. Please share your name and number."),
            "session": session}
