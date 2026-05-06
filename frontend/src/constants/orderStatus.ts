/**
 * Display metadata for order and outcome states. Centralising avoids the
 * Badge variant + label drift that happens when components hardcode strings.
 */

import type { OrderStatus, OutcomeTag } from "@/types/api";

export type StatusVariant =
  | "default"
  | "secondary"
  | "destructive"
  | "outline"
  | "success"
  | "warning";

export const ORDER_STATUS_LABEL: Record<OrderStatus, string> = {
  pending_verification: "Pending verification",
  verifying: "Verifying",
  ship_approved: "Ship approved",
  address_correction_requested: "Address correction",
  reschedule_requested: "Reschedule requested",
  cancelled: "Cancelled",
  needs_followup: "Needs followup",
  unreachable: "Unreachable",
  call_failed: "Call failed",
};

export const ORDER_STATUS_VARIANT: Record<OrderStatus, StatusVariant> = {
  pending_verification: "secondary",
  verifying: "default",
  ship_approved: "success",
  address_correction_requested: "warning",
  reschedule_requested: "warning",
  cancelled: "destructive",
  needs_followup: "warning",
  unreachable: "secondary",
  call_failed: "destructive",
};

export const OUTCOME_TAG_LABEL: Record<OutcomeTag, string> = {
  confirmed: "Confirmed",
  address_correction: "Address correction",
  reschedule: "Reschedule",
  cancel_requested: "Cancel requested",
  needs_followup: "Needs followup",
  unreachable: "Unreachable",
};

export const OUTCOME_TAG_VARIANT: Record<OutcomeTag, StatusVariant> = {
  confirmed: "success",
  address_correction: "warning",
  reschedule: "warning",
  cancel_requested: "destructive",
  needs_followup: "warning",
  unreachable: "secondary",
};

export function getOrderStatusLabel(status: OrderStatus | string): string {
  return ORDER_STATUS_LABEL[status as OrderStatus] ?? status;
}

export function getOrderStatusVariant(status: OrderStatus | string): StatusVariant {
  return ORDER_STATUS_VARIANT[status as OrderStatus] ?? "secondary";
}

export function getOutcomeTagLabel(outcome: string | null | undefined): string | null {
  if (!outcome) return null;
  return OUTCOME_TAG_LABEL[outcome as OutcomeTag] ?? outcome;
}

export function getOutcomeTagVariant(outcome: string | null | undefined): StatusVariant {
  if (!outcome) return "secondary";
  return OUTCOME_TAG_VARIANT[outcome as OutcomeTag] ?? "secondary";
}
