import { useState } from "react";
import type { Listing } from "@lakasmarket/shared";
import { SaleMode } from "@lakasmarket/shared";
import { api } from "../api/client";
import { OfferForm } from "./OfferForm";
import { MessageSellerForm } from "./MessageSellerForm";

export function ListingCard({ listing }: { listing: Listing }) {
  const [offering, setOffering] = useState(false);
  const [messaging, setMessaging] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);

  async function ask(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setAsking(true);
    setAnswer(null);
    try {
      const res = await api.askSpecsGuard(listing.id, question);
      setAnswer(res.answer);
    } catch (err) {
      setAnswer((err as Error).message);
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="card">
      <h3>{listing.title}</h3>
      <div style={{ fontSize: 13, color: "#4a5568", marginBottom: 6 }}>
        Seller: <strong>{listing.seller.display_name}</strong>{" "}
        <span title="Adab (courtesy) score">
          · Adab {listing.seller.adab_score.toFixed(0)}/100
        </span>{" "}
        · {listing.seller.completed_deals} deals
      </div>
      <div>
        <span className="badge">{listing.district}</span>
        {listing.sale_mode === SaleMode.Fast && <span className="badge">Take Tonight</span>}
        {listing.knowledge_questions.length > 0 && (
          <span className="badge">Knowledge Gate</span>
        )}
      </div>
      <p>{listing.description}</p>
      <div className="price">B$ {Number(listing.list_price).toFixed(2)}</div>
      <div className="floor">
        Offers below B$ {listing.hard_floor_price.toFixed(2)} are auto-declined.
      </div>
      {listing.min_buyer_adab > 0 && (
        <div className="floor">Requires Adab score ≥ {listing.min_buyer_adab}</div>
      )}

      <form onSubmit={ask} style={{ marginTop: 12 }}>
        <label>Ask the Specs Guard (AI)</label>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            placeholder="e.g. Does it come with the box?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            style={{ margin: 0 }}
          />
          <button type="submit" className="secondary" disabled={asking}>
            {asking ? "…" : "Ask"}
          </button>
        </div>
      </form>
      {answer && (
        <div className="badge" style={{ display: "block", marginTop: 8, whiteSpace: "normal" }}>
          🤖 {answer}
        </div>
      )}

      {messaging && (
        <div style={{ marginTop: 12 }}>
          <MessageSellerForm
            listing={listing}
            onClose={() => setMessaging(false)}
            onStarted={() => {}}
          />
        </div>
      )}

      {offering ? (
        <div style={{ marginTop: 12 }}>
          <OfferForm listing={listing} onClose={() => setOffering(false)} />
        </div>
      ) : (
        <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
          <button onClick={() => setOffering(true)}>Make an offer</button>
          <button
            className="secondary"
            onClick={() => setMessaging((m) => !m)}
          >
            Message seller
          </button>
        </div>
      )}
    </div>
  );
}
