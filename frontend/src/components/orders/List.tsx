"use client";

import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow as UITableRow,
} from "@/components/ui/table";
import { Card } from "@/components/ui/card";
import { Row } from "@/components/orders/Row";
import type { OrderResponse } from "@/types/api";

type Props = {
  orders: OrderResponse[];
  verifyingOrderId: string | null;
  onVerify: (orderId: string) => void;
  onView: (orderId: string) => void;
  onEdit: (orderId: string) => void;
  onDelete: (orderId: string) => void;
};

export function List({ orders, verifyingOrderId, onVerify, onView, onEdit, onDelete }: Props) {
  return (
    <Card className="overflow-hidden overflow-x-auto p-0">
      <Table>
        <TableHeader>
          <UITableRow>
            <TableHead className="w-[110px]">Order</TableHead>
            <TableHead>Customer</TableHead>
            <TableHead>Product</TableHead>
            <TableHead className="text-right">Value</TableHead>
            <TableHead className="w-[180px]">Status</TableHead>
            <TableHead className="w-[300px] text-right">Actions</TableHead>
          </UITableRow>
        </TableHeader>
        <TableBody>
          {orders.map((order) => (
            <Row
              key={order.id}
              order={order}
              isVerifying={verifyingOrderId === order.id}
              onVerify={onVerify}
              onView={onView}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}
