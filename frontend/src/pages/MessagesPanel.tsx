import { useCallback, useEffect, useRef, useState } from "react";
import type { ConversationDetail, ConversationSummary } from "@lakasmarket/shared";
import { ConversationStatus } from "@lakasmarket/shared";
import { api } from "../api/client";

export function MessagesPanel({ meId }: { meId: number }) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [active, setActive] = useState<ConversationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.myConversations().then(setConversations).catch((e) => setError(e.message));
  }, []);

  const openConversation = useCallback(async (id: number) => {
    try {
      setActive(await api.getConversation(id));
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  // Light polling so replies show up without a manual refresh.
  const activeId = active?.id;
  useEffect(() => {
    if (!activeId) return;
    const t = setInterval(() => {
      api.getConversation(activeId).then(setActive).catch(() => {});
    }, 5000);
    return () => clearInterval(t);
  }, [activeId]);

  return (
    <div className="container">
      <h2>Messages</h2>
      {error && <div className="warn">{error}</div>}
      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 16 }}>
        <div>
          {conversations.length === 0 && <p>No conversations yet.</p>}
          {conversations.map((c) => (
            <button
              key={c.id}
              className="secondary"
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                marginBottom: 6,
                fontWeight: active?.id === c.id ? 700 : 400,
              }}
              onClick={() => openConversation(c.id)}
            >
              Listing #{c.listing_id} · {c.buyer_id === meId ? "as buyer" : "as seller"}
              {c.status !== ConversationStatus.Open ? ` · ${c.status}` : ""}
            </button>
          ))}
        </div>
        <div>
          {active ? (
            <Thread conv={active} meId={meId} onChanged={() => openConversation(active.id)} />
          ) : (
            <p style={{ color: "#4a5568" }}>Select a conversation.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function Thread({
  conv,
  meId,
  onChanged,
}: {
  conv: ConversationDetail;
  meId: number;
  onChanged: () => void;
}) {
  const [body, setBody] = useState("");
  const [price, setPrice] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView();
  }, [conv.messages.length]);

  const isSeller = meId === conv.seller_id;
  const lastFromSeller =
    conv.messages.length > 0 && conv.messages[conv.messages.length - 1].sender_id === conv.seller_id;
  const canReportGhost = isSeller && conv.status === ConversationStatus.Open && lastFromSeller;

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.sendMessage(conv.id, body);
      setBody("");
      onChanged();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function reportGhost() {
    try {
      await api.reportGhostConversation(conv.id);
      onChanged();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function propose(e: React.FormEvent) {
    e.preventDefault();
    if (!price) return;
    setBusy(true);
    setError(null);
    try {
      await api.negotiate(conv.id, Number(price));
      setPrice("");
      onChanged();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const isBuyer = meId === conv.buyer_id;

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <strong>Listing #{conv.listing_id}</strong>
        {canReportGhost && (
          <button className="secondary" onClick={reportGhost}>
            Report ghosting
          </button>
        )}
      </div>
      {conv.status === ConversationStatus.Ghosted && (
        <div className="warn">Marked as ghosted. A reply from the buyer re-opens it.</div>
      )}
      <div style={{ maxHeight: 340, overflowY: "auto", margin: "12px 0" }}>
        {conv.messages.map((m) => {
          const mine = m.sender_id === meId;
          return (
            <div
              key={m.id}
              style={{ textAlign: mine ? "right" : "left", marginBottom: 8 }}
            >
              <span
                style={{
                  display: "inline-block",
                  background: mine ? "#0b6b4f" : "#eef1f4",
                  color: mine ? "#fff" : "#1a1a1a",
                  padding: "6px 10px",
                  borderRadius: 10,
                  maxWidth: "80%",
                }}
              >
                {m.body}
              </span>
            </div>
          );
        })}
        <div ref={endRef} />
      </div>
      {error && <div className="warn">{error}</div>}
      {conv.status !== ConversationStatus.Closed && (
        <>
          <form onSubmit={send} style={{ display: "flex", gap: 8 }}>
            <input
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Type a message…"
              style={{ margin: 0 }}
            />
            <button disabled={busy}>Send</button>
          </form>
          {isBuyer && (
            <form onSubmit={propose} style={{ display: "flex", gap: 8, marginTop: 8 }}>
              <input
                type="number"
                min="0"
                step="0.01"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                placeholder="Propose a price (B$) — AI bot replies"
                style={{ margin: 0 }}
              />
              <button className="secondary" disabled={busy}>
                Propose
              </button>
            </form>
          )}
        </>
      )}
    </div>
  );
}
