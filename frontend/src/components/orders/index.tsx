"use client";

import { useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { DetailDialog } from "@/components/orders/DetailDialog";
import { EmptyState } from "@/components/orders/EmptyState";
import { List } from "@/components/orders/List";
import { OrderFormDialog } from "@/components/orders/OrderFormDialog";
import { Toolbar } from "@/components/orders/Toolbar";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useOrderMutations } from "@/hooks/useOrderMutations";
import { useOrdersQuery } from "@/hooks/useOrdersQuery";
import type { OrderCreateInput, OrderListResponse } from "@/types/api";
import { orderKeys } from "@/query-keys/orders";

type Props = {
  initialOrders: OrderListResponse;
};

export default function OrdersContainer({ initialOrders }: Props) {
  const queryClient = useQueryClient();
  const ordersQuery = useOrdersQuery({ initialData: initialOrders });
  const { verify, refresh, createOrder, updateOrder, removeOrder } = useOrderMutations();

  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);

  const [formOpen, setFormOpen] = useState(false);
  const [editingOrder, setEditingOrder] = useState<OrderListResponse["items"][number] | null>(null);

  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  const items = useMemo(
    () => ordersQuery.data?.items ?? [],
    [ordersQuery.data],
  );

  const selectedOrder = useMemo(
    () => items.find((item) => item.id === selectedOrderId) ?? null,
    [items, selectedOrderId],
  );

  const verifyingOrderId = verify.isPending ? verify.variables?.orderId ?? null : null;

  const isRefreshingDetail = refresh.isPending;
  const isRefreshingList = ordersQuery.isFetching && !ordersQuery.isPending;

  const formSaving = createOrder.isPending || updateOrder.isPending;

  const handleVerify = (orderId: string) => {
    verify.mutate(
      { orderId },
      {
        onSuccess: (response) => {
          toast.success("Verification call queued", {
            description: `Bolna execution: ${response.call_id}`,
          });
        },
        onError: (error) => {
          toast.error("Could not start verification call", {
            description: error.message,
          });
        },
      },
    );
  };

  const handleView = (orderId: string) => {
    setSelectedOrderId(orderId);
  };

  const handleEdit = (orderId: string) => {
    const row = items.find((o) => o.id === orderId);
    if (row) {
      setEditingOrder(row);
      setFormOpen(true);
    }
  };

  const handleNewOrder = () => {
    setEditingOrder(null);
    setFormOpen(true);
  };

  const handleDeleteRequest = (orderId: string) => {
    setPendingDeleteId(orderId);
  };

  const handleRefresh = () => {
    if (!selectedOrderId) return;
    refresh.mutate(
      { orderId: selectedOrderId },
      {
        onSuccess: () => {
          toast.success("Order refreshed from Bolna");
        },
        onError: (error) => {
          toast.error("Refresh failed", { description: error.message });
        },
      },
    );
  };

  const handleRefreshAll = () => {
    queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
  };

  const confirmDelete = () => {
    if (!pendingDeleteId) return;
    const oid = pendingDeleteId;
    removeOrder.mutate(oid, {
      onSuccess: () => {
        toast.success(`Order ${oid} deleted`);
        setPendingDeleteId(null);
        if (selectedOrderId === oid) setSelectedOrderId(null);
        setFormOpen(false);
      },
      onError: (error) => {
        toast.error("Delete failed", { description: error.message });
      },
    });
  };

  return (
    <main className="mx-auto w-full max-w-7xl space-y-6 px-4 pt-8 pb-12 sm:px-6 lg:px-8">
      <Toolbar
        totalCount={items.length}
        isRefreshing={isRefreshingList}
        onRefreshAll={handleRefreshAll}
        onNewOrder={handleNewOrder}
      />

      {items.length === 0 ? (
        <EmptyState />
      ) : (
        <List
          orders={items}
          verifyingOrderId={verifyingOrderId}
          onVerify={handleVerify}
          onView={handleView}
          onEdit={handleEdit}
          onDelete={handleDeleteRequest}
        />
      )}

      <OrderFormDialog
        open={formOpen}
        editing={editingOrder}
        isSubmitting={formSaving}
        onOpenChange={(open) => {
          setFormOpen(open);
          if (!open) setEditingOrder(null);
        }}
        onCreate={async (payload: OrderCreateInput) => {
          try {
            await createOrder.mutateAsync(payload);
            toast.success("Order created");
            setFormOpen(false);
            setEditingOrder(null);
          } catch (error) {
            const message = error instanceof Error ? error.message : "Unknown error";
            toast.error("Create failed", { description: message });
          }
        }}
        onUpdate={async (orderId, patch) => {
          try {
            await updateOrder.mutateAsync({ orderId, patch });
            toast.success("Order updated");
            setFormOpen(false);
            setEditingOrder(null);
          } catch (error) {
            const message = error instanceof Error ? error.message : "Unknown error";
            toast.error("Update failed", { description: message });
          }
        }}
      />

      <DetailDialog
        order={selectedOrder}
        open={Boolean(selectedOrderId)}
        isRefreshing={isRefreshingDetail}
        onOpenChange={(open) => {
          if (!open) setSelectedOrderId(null);
        }}
        onRefresh={handleRefresh}
      />

      <Dialog open={pendingDeleteId !== null} onOpenChange={(open) => !open && setPendingDeleteId(null)}>
        <DialogContent showCloseButton>
          <DialogHeader>
            <DialogTitle>Delete this order?</DialogTitle>
            <DialogDescription className="font-mono">{pendingDeleteId}</DialogDescription>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            This removes the order row and linked call artifacts from storage. Confirm to continue.
          </p>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setPendingDeleteId(null)}>
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={confirmDelete}
              disabled={removeOrder.isPending}
            >
              {removeOrder.isPending ? "Deleting…" : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}
