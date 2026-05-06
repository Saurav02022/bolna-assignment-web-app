/**
 * Server lib for orders. Called from Server Components (`page.tsx`) and from
 * the route handlers under `app/api/orders/*`. Throws `BackendError` on
 * non-2xx — callers handle or rethrow.
 */

import { backendFetch } from "@/lib/api";
import type {
  OrderCreateInput,
  OrderListResponse,
  OrderResponse,
  OrderUpdateInput,
  TriggerCallResponse,
} from "@/types/api";

export async function listOrders(): Promise<OrderListResponse> {
  return backendFetch<OrderListResponse>("/orders");
}

export async function createOrder(payload: OrderCreateInput): Promise<OrderResponse> {
  const body = { ...payload, brand_name: payload.brand_name ?? "RetailKart" };
  return backendFetch<OrderResponse>("/orders", { method: "POST", body });
}

export async function updateOrder(orderId: string, patch: OrderUpdateInput): Promise<OrderResponse> {
  return backendFetch<OrderResponse>(`/orders/${encodeURIComponent(orderId)}`, {
    method: "PATCH",
    body: patch,
  });
}

export async function deleteOrder(orderId: string): Promise<void> {
  await backendFetch<void>(`/orders/${encodeURIComponent(orderId)}`, {
    method: "DELETE",
  });
}

export async function getOrder(orderId: string): Promise<OrderResponse> {
  return backendFetch<OrderResponse>(`/orders/${encodeURIComponent(orderId)}`);
}

export async function triggerVerifyCall(orderId: string): Promise<TriggerCallResponse> {
  return backendFetch<TriggerCallResponse>(
    `/orders/${encodeURIComponent(orderId)}/verify`,
    { method: "POST" },
  );
}

export async function refreshOrderFromBolna(
  orderId: string,
  params?: { callId?: string; force?: boolean },
): Promise<OrderResponse> {
  return backendFetch<OrderResponse>(
    `/orders/${encodeURIComponent(orderId)}/refresh`,
    {
      method: "POST",
      searchParams: {
        ...(params?.callId && { call_id: params.callId }),
        ...(params?.force !== undefined && { force: String(params.force) }),
      },
    },
  );
}
