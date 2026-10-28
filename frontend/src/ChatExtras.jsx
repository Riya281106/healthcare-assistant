import { useState } from "react";

// Languages offered in the selector. "auto" = detect from the message.
export const LANGUAGES = [
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
        const maps = safeHttpUrl(f.maps_url);
        const booking =
          f.booking && f.booking.status === "found"
            ? safeHttpUrl(f.booking.url)
            : null;

        return (
          <li key={f.n} className="facility-card">
            <div className="facility-head">
              <span className="facility-number">{f.n}</span>
              <h4>{f.name}</h4>
            </div>

            <p className="facility-line">
              <strong>Specialty:</strong> {f.specialty}
            </p>
            <p className="facility-line">
              <strong>Address:</strong> {f.address || "not listed"}
            </p>
            {f.distance_km != null && (
              <p className="facility-line">
                <strong>Distance:</strong> about {f.distance_km} km from your location
              </p>
            )}
            {f.phone && (
              <p className="facility-line">
                <strong>Phone:</strong>{" "}
                <a href={`tel:${f.phone.replace(/[^+\d]/g, "")}`}>{f.phone}</a>
              </p>
            )}

            <div className="facility-actions">
              {website && (
                <a
                  className="facility-btn"
                  href={website}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Official website
                </a>
              )}
              {maps && (
                <a
                  className="facility-btn"
                  href={maps}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Directions
                </a>
              )}
              {booking ? (
                <a
                  className="facility-btn facility-btn-primary"
                  href={booking}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Book appointment
                  {f.booking.external_provider ? " (outside provider)" : ""}
                </a>
              ) : (
                <button
                  type="button"
                  className="facility-btn facility-btn-muted"
                  onClick={() => onChoose(`Book an appointment at Hospital ${f.n}`)}
                  disabled={disabled}
                  title="No verified online booking link found. Tap for phone or website options."
                >
                  Booking help
                </button>
              )}
            </div>

            {!booking && (
              <p className="facility-note">
                Online booking link not verified.
              </p>
            )}
            <p className="facility-source">Source: {f.source}</p>
          </li>
        );
      })}
    </ol>
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
