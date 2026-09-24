import { useState } from "react";
import type { Listing } from "@lakasmarket/shared";
import { api } from "../api/client";

interface Props {
  listing: Listing;
  onClose: () => void;
  onStarted: () => void;
}

// Buyer-facing "message the seller" flow. First contact clears the same
// Product Knowledge Gateway quiz as making an offer, then sends an opening line.
export function MessageSellerForm({ listing, onClose, onStarted }: Props) {
  const questions = listing.knowledge_questions;
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const quizComplete = questions.every((q) => answers[q.id] !== undefined);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.startConversation(listing.id, {
        quiz_answers: answers,
        opening_message: message || undefined,
      });
      setDone(true);
      onStarted();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <div className="card" style={{ background: "#fbfdfc" }}>
        <p className="warn" style={{ color: "#0b6b4f" }}>
          Message sent — find the reply under the <strong>Messages</strong> tab.
        </p>
        <button className="secondary" onClick={onClose}>
          Close
        </button>
      </div>
    );
  }

  return (
    <form className="card" onSubmit={submit} style={{ background: "#fbfdfc" }}>
      <h4>Message the seller</h4>
      {questions.length > 0 && (
        <>
          <p className="warn" style={{ color: "#0b6b4f" }}>
            Answer these first — they confirm you read the description.
          </p>
          {questions.map((q) => (
            <fieldset key={q.id} style={{ border: 0, padding: 0, marginBottom: 8 }}>
              <legend style={{ fontWeight: 600, fontSize: 13 }}>{q.prompt}</legend>
              {q.options.map((opt, i) => (
                <label key={i} style={{ display: "block", fontWeight: 400 }}>
                  <input
                    type="radio"
                    name={`chatq-${q.id}`}
                    checked={answers[q.id] === i}
                    onChange={() => setAnswers((p) => ({ ...p, [q.id]: i }))}
                    style={{ width: "auto", marginRight: 6 }}
                  />
                  {opt}
                </label>
              ))}
            </fieldset>
          ))}
        </>
      )}
      <label>Your message</label>
      <textarea
        rows={2}
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Hi, is this still available?"
        required
      />
      {error && <div className="warn">{error}</div>}
      <div style={{ display: "flex", gap: 8 }}>
        <button disabled={busy || !quizComplete}>{busy ? "Sending…" : "Send"}</button>
        <button type="button" className="secondary" onClick={onClose}>
          Cancel
        </button>
      </div>
    </form>
  );
}
