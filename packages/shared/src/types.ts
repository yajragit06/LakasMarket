// Domain types shared across web (React) and mobile (React Native).

export enum SubscriptionTier {
  Basic = "basic",
  Pro = "pro",
  Business = "business",
}

export enum District {
  Bandar = "bandar",
  BruneiMuara = "brunei_muara",
  Tutong = "tutong",
  Seria = "seria",
  KualaBelait = "kuala_belait",
  Temburong = "temburong",
}

export enum SaleMode {
  Firm = "firm",
  Fast = "fast",
}

export enum ListingStatus {
  Active = "active",
  Reserved = "reserved",
  Sold = "sold",
  Archived = "archived",
}

export interface KnowledgeQuestion {
  id: number;
  prompt: string;
  options: string[];
  ai_generated: boolean;
}

export interface SellerSummary {
  id: number;
  display_name: string;
  adab_score: number;
  completed_deals: number;
}

export interface Listing {
  id: number;
  seller_id: number;
  seller: SellerSummary;
  title: string;
  description: string;
  category: string | null;
  list_price: string;
  floor_percent: number;
  hard_floor_price: number;
  sale_mode: SaleMode;
  speed_discount_percent: number;
  district: District;
  delivery_available: boolean;
  min_buyer_adab: number;
  status: ListingStatus;
  created_at: string;
  knowledge_questions: KnowledgeQuestion[];
}

export interface UserPublic {
  id: number;
  display_name: string;
  home_district: District;
  reliability_score: number;
  communication_score: number;
  adab_score: number;
  completed_deals: number;
  created_at: string;
}

export enum PaymentStatus {
  None = "none",
  Pending = "pending",
  Verified = "verified",
  Released = "released",
  Refunded = "refunded",
}

export interface Offer {
  id: number;
  listing_id: number;
  buyer_id: number;
  amount: string;
  is_take_tonight: boolean;
  status: string;
  delivery_fee: string;
  passed_knowledge_gate: boolean;
  created_at: string;
  payment_status: PaymentStatus;
  payment_reference: string | null;
}

export interface Subscription {
  tier: SubscriptionTier;
  listing_limit: number | null;
  has_specs_guard: boolean;
  started_at: string;
  renews_at: string | null;
}

export type OfferAction = "accept" | "decline" | "complete" | "report-ghost";

export enum ConversationStatus {
  Open = "open",
  Ghosted = "ghosted",
  Closed = "closed",
}

export interface Message {
  id: number;
  sender_id: number;
  body: string;
  read_at: string | null;
  created_at: string;
}

export interface ConversationSummary {
  id: number;
  listing_id: number;
  buyer_id: number;
  seller_id: number;
  status: ConversationStatus;
  created_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: Message[];
}

export interface SellerAnalytics {
  active_listings: number;
  reserved_listings: number;
  sold_listings: number;
  lowballs_blocked: number;
  pending_offers: number;
  accepted_offers: number;
  expired_take_tonight_offers: number;
  avg_offer_percent_of_list: number | null;
  conversations: number;
  ghosted_conversations: number;
  funds_verified_deals: number;
}
