import { useEffect, useState } from "react";

const API_BASE = "http://127.0.0.1:8000/api";

function getToken() {
  return localStorage.getItem("authToken");
}

async function fetchProfile() {
  const response = await fetch(`${API_BASE}/profile/me`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.detail || "Failed to load profile.");
  return data;
}

async function saveProfile(fields) {
  const response = await fetch(`${API_BASE}/profile/me`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify(fields),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.detail || "Failed to update profile.");
  return data;
}

const EDITABLE_FIELDS = [
  { key: "name", label: "Name", type: "text" },
  { key: "age", label: "Age", type: "number" },
  { key: "gender", label: "Gender", type: "text" },
  { key: "date_of_birth", label: "Date of Birth", type: "text" },
  { key: "phone", label: "Phone", type: "text" },
  { key: "blood_group", label: "Blood Group", type: "text" },
  { key: "height_cm", label: "Height (cm)", type: "number" },
  { key: "weight_kg", label: "Weight (kg)", type: "number" },
  { key: "allergies", label: "Allergies", type: "text" },
  { key: "chronic_conditions", label: "Chronic Conditions", type: "text" },
  { key: "emergency_contact_name", label: "Emergency Contact Name", type: "text" },
  { key: "emergency_contact_phone", label: "Emergency Contact Phone", type: "text" },
];

function ProfilePage({ onBack }) {
  const [profile, setProfile] = useState(null);
  const [formValues, setFormValues] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saveMessage, setSaveMessage] = useState("");

  const loadProfile = async () => {
    setLoading(true);
    setError("");

    try {
      const data = await fetchProfile();
      setProfile(data);
      setFormValues(data);
    } catch (err) {
      setError(err.message || "Failed to load profile.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  const handleChange = (key, value) => {
    setFormValues((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSaveMessage("");
    setError("");

    try {
      const updated = await saveProfile(formValues);
      setProfile(updated);
      setFormValues(updated);
      setSaveMessage("Profile updated successfully.");
    } catch (err) {
      setError(err.message || "Failed to update profile.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="profile-page">
      <div className="profile-page-header">
        <button className="back-button" onClick={onBack}>← Back</button>
        <h1>Profile</h1>
      </div>

      {loading && <div className="summary-loading">Loading profile...</div>}

      {!loading && error && (
        <div className="summary-error">
          <p>{error}</p>
          <button onClick={loadProfile}>Retry</button>
        </div>
      )}

      {!loading && profile && (
        <form className="profile-form" onSubmit={handleSave}>
          <div className="profile-account-info">
            <p><strong>Email:</strong> {profile.email}</p>
            <p><strong>Member Since:</strong> {profile.created_at}</p>
          </div>

          {EDITABLE_FIELDS.map((field) => (
            <label key={field.key} className="profile-field">
              <span>{field.label}</span>
              <input
                type={field.type}
                value={formValues[field.key] ?? ""}
                onChange={(e) => handleChange(field.key, e.target.value)}
              />
            </label>
          ))}

          {saveMessage && <p className="profile-save-message">{saveMessage}</p>}

          <button type="submit" className="save-button" disabled={saving}>
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </form>
      )}
    </div>
  );
}

export default ProfilePage;