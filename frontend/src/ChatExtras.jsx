import { useState } from "react";

// Languages offered in the selector. "auto" = detect from the message.
const LANGUAGES = [
  { code: "auto", label: "Auto" },
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "mr", label: "मराठी" },
  { code: "hinglish", label: "Hinglish" },
];

export function LanguageSelect({ value, onChange, disabled }) {
  return (
    <label className="lang-select">
      <span className="lang-select-label">Language</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        aria-label="Reply language"
      >
        {LANGUAGES.map((l) => (
          <option key={l.code} value={l.code}>
            {l.label}
          </option>
        ))}
      </select>
    </label>
  );
}

// Asks for a PIN code / area right under the assistant's question.
export function LocationPrompt({ onSubmit, disabled }) {
  const [value, setValue] = useState("");

  const submit = (e) => {
    e.preventDefault();
    const text = value.trim();
    if (!text || disabled) return;
    onSubmit(text);
    setValue("");
  };

  return (
    <form className="location-prompt" onSubmit={submit}>
      <label htmlFor="loc-input" className="location-prompt-label">
        PIN code or area
      </label>
      <div className="location-prompt-row">
        <input
          id="loc-input"
          type="text"
          inputMode="text"
          autoComplete="postal-code"
          placeholder="e.g. 400001 or Dadar, Mumbai"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={disabled}
        />
        <button type="submit" disabled={disabled || !value.trim()}>
          Find
        </button>
      </div>
    </form>
  );
}

function safeHttpUrl(url) {
  try {
    const u = new URL(url);
    return u.protocol === "http:" || u.protocol === "https:" ? u.href : null;
  } catch {
    return null;
  }
}

// One card per facility. Only facts that came from the server are shown;
// anything missing is labelled, never filled in.
export function FacilityCards({ facilities, onChoose, disabled }) {
  if (!facilities || facilities.length === 0) return null;

  return (
    <ol className="facility-list">
      {facilities.map((f) => {
        const website = safeHttpUrl(f.website);
        const directions = safeHttpUrl(f.directions_url) || safeHttpUrl(f.maps_url);
        const phoneLookup = safeHttpUrl(f.phone_lookup_url);
        const booking =
          f.booking && f.booking.status === "found"
            ? safeHttpUrl(f.booking.url)
            : null;

        return (
          <li key={f.n} className={`facility-card ${f.partner_demo ? "facility-card-demo" : ""}`}>
            <div className="facility-head">
              <span className="facility-number">{f.n}</span>
              <h4>{f.name}</h4>
            </div>

            {f.partner_demo && (
              <p className="facility-demo-badge">DEMO: sandbox hospital for this project</p>
            )}

            <p className="facility-line">
              <strong>Type:</strong> {f.specialty}
            </p>
            <p className="facility-line">
              <strong>Address:</strong> {f.address || "not listed"}
            </p>
            {f.distance_km != null && (
              <p className="facility-line">
                <strong>Distance:</strong> about {f.distance_km} km
              </p>
            )}
            {!f.partner_demo && (
              <p className="facility-line">
                <strong>Phone:</strong>{" "}
                {f.phone ? (
                  <a href={`tel:${f.phone.replace(/[^+\d]/g, "")}`}>{f.phone}</a>
                ) : (
                  "not listed"
                )}
              </p>
            )}

            <div className="facility-actions">
              {f.phone && (
                <a className="facility-btn" href={`tel:${f.phone.replace(/[^+\d]/g, "")}`}>
                  Call
                </a>
              )}
              {!f.phone && phoneLookup && (
                <a className="facility-btn" href={phoneLookup} target="_blank" rel="noopener noreferrer">
                  Find phone
                </a>
              )}
              {directions && (
                <a className="facility-btn" href={directions} target="_blank" rel="noopener noreferrer">
                  Directions
                </a>
              )}
              {website && (
                <a className="facility-btn" href={website} target="_blank" rel="noopener noreferrer">
                  Website
                </a>
              )}
              {booking && (
                <a className="facility-btn" href={booking} target="_blank" rel="noopener noreferrer">
                  Official booking page{f.booking.external_provider ? " (outside provider)" : ""}
                </a>
              )}
              <button
                type="button"
                className="facility-btn facility-btn-primary"
                onClick={() => onChoose(`Book an appointment at Hospital ${f.n}`)}
                disabled={disabled}
              >
                Select and book
              </button>
            </div>

            <p className="facility-source">Source: {f.source}</p>
          </li>
        );
      })}
    </ol>
  );
}

// Tap-to-answer buttons under the assistant's latest question (Yes / No / Cancel ...).
// Some labels are sent as a plain "yes" / "no" so the server understands them.
const QUICK_SEND = {
  "Yes, request appointment": "yes",
  "Yes, confirm": "yes",
  "Yes, cancel it": "yes",
  "No, keep it": "no",
  "Change something": "change",
};

export function QuickReplies({ options, onPick, disabled }) {
  if (!options || options.length === 0) return null;
  return (
    <div className="quick-replies" role="group" aria-label="Quick replies">
      {options.map((label) => (
        <button
          key={label}
          type="button"
          className="quick-reply"
          disabled={disabled}
          onClick={() => onPick(QUICK_SEND[label] || label)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

// Shown after a request is saved. Says plainly what the status means.
export function AppointmentCard({ appointment }) {
  if (!appointment) return null;
  const confirmed = appointment.status === "confirmed";
  const phone = appointment.facility_phone;
  return (
    <div className={`appointment-card ${confirmed ? "appointment-confirmed" : "appointment-requested"}`}>
      <div className="appointment-ref">Reference {appointment.ref}</div>
      <div className="appointment-status">
        {confirmed ? "CONFIRMED (demo hospital)" : "REQUESTED: not confirmed by the hospital yet"}
      </div>
      <p className="appointment-line">{appointment.facility_name}</p>
      <p className="appointment-line">
        {appointment.preferred_date}
        {appointment.preferred_slot ? `, ${appointment.preferred_slot}` : ""}
      </p>
      {!confirmed && phone && (
        <a className="facility-btn facility-btn-primary" href={`tel:${phone.replace(/[^+\d]/g, "")}`}>
          Call the hospital to confirm
        </a>
      )}
    </div>
  );
}

// A short, honest list of what the assistant did for this answer.
export function TracePanel({ trace }) {
  if (!trace || trace.length === 0) return null;
  return (
    <details className="trace-panel">
      <summary>How I handled this</summary>
      <ol>
        {trace.map((step, i) => (
          <li key={i}>{step}</li>
        ))}
      </ol>
    </details>
  );
}

// Big, clearly labelled button after the assistant shares a verified link.
// It only opens the page; it never claims a booking was made.
export function BookingButton({ url }) {
  const href = safeHttpUrl(url);
  if (!href) return null;
  return (
    <a
      className="facility-btn facility-btn-primary booking-open"
      href={href}
      target="_blank"
      rel="noopener noreferrer"
    >
      Open appointment page
    </a>
  );
}
