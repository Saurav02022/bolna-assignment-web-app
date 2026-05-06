"use client";

import { type FormEvent, type ReactNode, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { OrderCreateInput, OrderResponse, OrderUpdateInput } from "@/types/api";

const EMPTY_FIELDS = {
  customer_name: "",
  phone: "",
  product_summary: "",
  order_value: "0",
  address_short: "",
  scheduled_slot: "",
  brand_name: "RetailKart",
} as const;

type FormFields = {
  customer_name: string;
  phone: string;
  product_summary: string;
  order_value: string;
  address_short: string;
  scheduled_slot: string;
  brand_name: string;
};

function fieldsFromOrder(editing: OrderResponse): FormFields {
  return {
    customer_name: editing.customer_name,
    phone: editing.phone,
    product_summary: editing.product_summary,
    order_value: String(editing.order_value),
    address_short: editing.address_short,
    scheduled_slot: editing.scheduled_slot,
    brand_name: editing.brand_name,
  };
}

type Props = {
  open: boolean;
  editing: OrderResponse | null;
  isSubmitting: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (payload: OrderCreateInput) => void | Promise<void>;
  onUpdate: (orderId: string, patch: OrderUpdateInput) => void | Promise<void>;
};

export function OrderFormDialog({
  open,
  editing,
  isSubmitting,
  onOpenChange,
  onCreate,
  onUpdate,
}: Props) {
  const isEdit = editing !== null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg overflow-y-auto sm:max-w-lg">
        {open ? (
          <OrderFormInner
            key={editing?.id ?? "__create__"}
            editing={editing}
            isEdit={isEdit}
            isSubmitting={isSubmitting}
            onOpenChange={onOpenChange}
            onCreate={onCreate}
            onUpdate={onUpdate}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function OrderFormInner({
  editing,
  isEdit,
  isSubmitting,
  onOpenChange,
  onCreate,
  onUpdate,
}: {
  editing: OrderResponse | null;
  isEdit: boolean;
  isSubmitting: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (payload: OrderCreateInput) => void | Promise<void>;
  onUpdate: (orderId: string, patch: OrderUpdateInput) => void | Promise<void>;
}) {
  const [form, setForm] = useState<FormFields>(() =>
    editing ? fieldsFromOrder(editing) : { ...EMPTY_FIELDS },
  );

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const orderValue = Number.parseInt(form.order_value, 10);
    if (Number.isNaN(orderValue) || orderValue < 0) {
      return;
    }
    const base = {
      customer_name: form.customer_name.trim(),
      phone: form.phone.trim(),
      product_summary: form.product_summary.trim(),
      order_value: orderValue,
      address_short: form.address_short.trim(),
      scheduled_slot: form.scheduled_slot.trim(),
      brand_name: form.brand_name.trim() || "RetailKart",
    };
    if (isEdit && editing) {
      const patch: OrderUpdateInput = {
        customer_name: base.customer_name,
        phone: base.phone,
        product_summary: base.product_summary,
        order_value: base.order_value,
        address_short: base.address_short,
        scheduled_slot: base.scheduled_slot,
        brand_name: base.brand_name,
      };
      await onUpdate(editing.id, patch);
    } else {
      await onCreate({
        customer_name: base.customer_name,
        phone: base.phone,
        product_summary: base.product_summary,
        order_value: base.order_value,
        address_short: base.address_short,
        scheduled_slot: base.scheduled_slot,
        brand_name: base.brand_name,
      });
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <DialogHeader>
        <DialogTitle>{isEdit ? "Edit order" : "New order"}</DialogTitle>
        <DialogDescription>
          {isEdit
            ? "Changes apply immediately to the backed record."
            : "Adds a COD order awaiting verification."}
        </DialogDescription>
      </DialogHeader>

      <div className="grid gap-4 py-4">
        <Field label="Customer name">
          <Input
            required
            value={form.customer_name}
            onChange={(e) => setForm((f) => ({ ...f, customer_name: e.target.value }))}
            autoComplete="name"
          />
        </Field>
        <Field label="Phone (E.164)" hint="+91…">
          <Input
            required
            inputMode="tel"
            value={form.phone}
            onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
          />
        </Field>
        <Field label="Product">
          <Input
            required
            value={form.product_summary}
            onChange={(e) => setForm((f) => ({ ...f, product_summary: e.target.value }))}
          />
        </Field>
        <Field label="Order value (₹)">
          <Input
            required
            type="number"
            min={0}
            value={form.order_value}
            onChange={(e) => setForm((f) => ({ ...f, order_value: e.target.value }))}
          />
        </Field>
        <Field label="Address">
          <Textarea
            required
            rows={2}
            value={form.address_short}
            onChange={(e) => setForm((f) => ({ ...f, address_short: e.target.value }))}
          />
        </Field>
        <Field label="Scheduled slot">
          <Input
            required
            value={form.scheduled_slot}
            onChange={(e) => setForm((f) => ({ ...f, scheduled_slot: e.target.value }))}
          />
        </Field>
        <Field label="Brand">
          <Input
            required
            value={form.brand_name}
            onChange={(e) => setForm((f) => ({ ...f, brand_name: e.target.value }))}
          />
        </Field>
      </div>

      <DialogFooter className="gap-2 sm:justify-end">
        <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
          Cancel
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Saving…" : isEdit ? "Save changes" : "Create order"}
        </Button>
      </DialogFooter>
    </form>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div className="grid gap-1.5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</span>
        {hint ? <span className="text-xs text-muted-foreground">{hint}</span> : null}
      </div>
      {children}
    </div>
  );
}
