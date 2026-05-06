/**
 * Public API contract between the Next.js frontend and the FastAPI backend.
 * Mirror of the Pydantic schemas defined in backend/app/domains/*. Update both
 * sides together when the contract evolves.
 */

export type OrderStatus =
  | "pending_verification"
  | "verifying"
  | "ship_approved"
  | "address_correction_requested"
  | "reschedule_requested"
  | "cancelled"
  | "needs_followup"
  | "unreachable"
  | "call_failed";

export type OutcomeTag =
  | "confirmed"
  | "address_correction"
  | "reschedule"
  | "cancel_requested"
  | "needs_followup"
  | "unreachable";

export type OrderResponse = {
  id: string;
  customer_name: string;
  phone: string;
  product_summary: string;
  order_value: number;
  address_short: string;
  scheduled_slot: string;
  brand_name: string;
  status: OrderStatus;
  last_call_id: string | null;
  last_call_outcome: OutcomeTag | string | null;
  captured_address_landmark: string | null;
  captured_new_slot: string | null;
  captured_cancel_reason: string | null;
  captured_followup_question: string | null;
  last_transcript_url: string | null;
  last_recording_url: string | null;
  last_summary: string | null;
  created_at: string;
  updated_at: string;
};

export type OrderCreateInput = {
  customer_name: string;
  phone: string;
  product_summary: string;
  order_value: number;
  address_short: string;
  scheduled_slot: string;
  brand_name?: string;
};

/** Fields allowed on PATCH `/orders/:id`. */
export type OrderUpdateInput = Partial<OrderCreateInput>;

export type OrderListResponse = {
  items: OrderResponse[];
  total: number;
};

export type CallStatus =
  | "queued"
  | "initiated"
  | "ringing"
  | "in_progress"
  | "completed"
  | "failed"
  | "no_answer"
  | "voicemail"
  | "call_disconnected";

export type CallRecord = {
  id: string;
  order_id: string;
  status: CallStatus;
  triggered_at: string;
  completed_at: string | null;
  outcome_tag: string | null;
  extractions: Record<string, unknown>;
  transcript_url: string | null;
  recording_url: string | null;
  summary: string | null;
  duration_sec: number | null;
  language_detected: string | null;
  sentiment: string | null;
};

export type TriggerCallResponse = {
  order: OrderResponse;
  call_id: string;
  bolna_status: string;
};
