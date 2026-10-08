// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

import type { WorkOrder } from '@/types'

export type WorkOrderStage =
	| 'draft'
	| 'stopped'
	| 'terminal'
	| 'ready_to_transfer'
	| 'in_operations'
	| 'ready_to_manufacture'

export type WorkOrderPredecessor = {
	work_order: string
	item_code: string
	required_qty: number
	produced_qty: number
	status: string
	stock_uom?: string
}

export function computeWorkOrderStage(
	workOrder: Partial<WorkOrder>,
	overproductionPercentage: number
): WorkOrderStage {
	if (workOrder.docstatus === 0) {
		return 'draft'
	}
	if (workOrder.status === 'Stopped') {
		return 'stopped'
	}
	if (['Closed', 'Completed', 'Cancelled'].includes(workOrder.status || '')) {
		return 'terminal'
	}

	const targetQty = Number(workOrder.qty || 0)
	const minOpQty = targetQty * (1 - overproductionPercentage / 100)
	const maxProducedQty = targetQty * (1 + overproductionPercentage / 100)
	const operations = workOrder.operations || []
	const hasOperations = operations.length > 0
	const operationsComplete =
		!hasOperations ||
		operations.every(operation => Number(operation.completed_qty || 0) >= minOpQty)

	const pendingTransfer =
		!workOrder.skip_transfer &&
		(workOrder.required_items || []).some(
			item => Number(item.transferred_qty || 0) < Number(item.required_qty || 0)
		)

	if (pendingTransfer) {
		return 'ready_to_transfer'
	}
	if (hasOperations && !operationsComplete) {
		return 'in_operations'
	}

	const producedTotal =
		Number(workOrder.produced_qty || 0) + Number((workOrder as { process_loss_qty?: number }).process_loss_qty || 0)
	if (producedTotal < maxProducedQty) {
		return 'ready_to_manufacture'
	}

	return 'terminal'
}

export function stockEntryPurposeForStage(stage: WorkOrderStage): string | null {
	if (stage === 'ready_to_transfer') {
		return 'Material Transfer for Manufacture'
	}
	if (stage === 'ready_to_manufacture') {
		return 'Manufacture'
	}
	return null
}

export function predecessorsBlock(predecessors: WorkOrderPredecessor[]): boolean {
	return predecessors.some(
		row => Number(row.produced_qty || 0) < Number(row.required_qty || 0)
	)
}
