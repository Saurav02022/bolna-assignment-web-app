"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { API_ROUTES } from "@/config/routes";
import { unwrap } from "@/lib/api-response";
import type { OrderCreateInput, OrderResponse, OrderUpdateInput, TriggerCallResponse } from "@/types/api";
import { orderKeys } from "@/query-keys/orders";

async function postVerify(orderId: string): Promise<TriggerCallResponse> {
  const response = await fetch(API_ROUTES.orderVerify(orderId), { method: "POST" });
  return unwrap<TriggerCallResponse>(response);
}

async function postRefresh(
  orderId: string,
  params?: { callId?: string; force?: boolean },
): Promise<OrderResponse> {
  const url = new URL(API_ROUTES.orderRefresh(orderId), window.location.origin);
  if (params?.callId) url.searchParams.set("call_id", params.callId);
  if (params?.force) url.searchParams.set("force", "true");

  const response = await fetch(url.toString().replace(window.location.origin, ""), {
    method: "POST",
  });
  return unwrap<OrderResponse>(response);
}

async function postCreate(payload: OrderCreateInput): Promise<OrderResponse> {
  const response = await fetch(API_ROUTES.orders, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return unwrap<OrderResponse>(response);
}

async function patchOrder(orderId: string, patch: OrderUpdateInput): Promise<OrderResponse> {
  const response = await fetch(API_ROUTES.orderDetail(orderId), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  return unwrap<OrderResponse>(response);
}

async function fetchDelete(orderId: string): Promise<void> {
  const response = await fetch(API_ROUTES.orderDetail(orderId), { method: "DELETE" });
  await unwrap<{ deleted: boolean }>(response);
}

export function useOrderMutations() {
  const queryClient = useQueryClient();

  const verify = useMutation<TriggerCallResponse, Error, { orderId: string }>({
    mutationFn: ({ orderId }) => postVerify(orderId),
    onSuccess: (response) => {
      queryClient.setQueryData(orderKeys.detail(response.order.id), response.order);
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
    },
  });

  const refresh = useMutation<
    OrderResponse,
    Error,
    { orderId: string; callId?: string; force?: boolean }
  >({
    mutationFn: ({ orderId, callId, force }) => postRefresh(orderId, { callId, force }),
    onSuccess: (order) => {
      queryClient.setQueryData(orderKeys.detail(order.id), order);
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
    },
  });

  const createOrder = useMutation<OrderResponse, Error, OrderCreateInput>({
    mutationFn: postCreate,
    onSuccess: (order) => {
      queryClient.setQueryData(orderKeys.detail(order.id), order);
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
    },
  });

  const updateOrder = useMutation<OrderResponse, Error, { orderId: string; patch: OrderUpdateInput }>({
    mutationFn: ({ orderId, patch }) => patchOrder(orderId, patch),
    onSuccess: (order) => {
      queryClient.setQueryData(orderKeys.detail(order.id), order);
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
    },
  });

  const removeOrder = useMutation<void, Error, string>({
    mutationFn: fetchDelete,
    onSuccess: (_void, deletedId) => {
      queryClient.removeQueries({ queryKey: orderKeys.detail(deletedId) });
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
    },
  });

  return { verify, refresh, createOrder, updateOrder, removeOrder };
}
