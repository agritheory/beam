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

export type WorkOrderMobileContext = {
	predecessors: WorkOrderPredecessor[]
	predecessors_block: boolean
	overproduction_percentage: number
	pick_list?: string | null
}

const stageDetails: Record<WorkOrderStage, { label?: string; stockEntryPurpose?: string }> = {
	draft: { label: 'Draft' },
	stopped: { label: 'Stopped' },
	terminal: {},
	ready_to_transfer: {
		label: 'Ready to transfer materials',
		stockEntryPurpose: 'Material Transfer for Manufacture',
	},
	in_operations: { label: 'Operations in progress' },
	ready_to_manufacture: { label: 'Ready to manufacture', stockEntryPurpose: 'Manufacture' },
}

/** Lowest quantity that counts as done and highest allowed, given Manufacturing Settings' overproduction %. */
export function productionQtyLimits(qty: number, overproductionPercentage: number): { min: number; max: number } {
	return {
		min: qty * (1 - overproductionPercentage / 100),
		max: qty * (1 + overproductionPercentage / 100),
	}
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

	const limits = productionQtyLimits(Number(workOrder.qty || 0), overproductionPercentage)
	const operations = workOrder.operations || []
	const hasOperations = operations.length > 0
	const operationsComplete =
		!hasOperations || operations.every(operation => Number(operation.completed_qty || 0) >= limits.min)

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

	const producedTotal = Number(workOrder.produced_qty || 0) + Number(workOrder.process_loss_qty || 0)
	if (producedTotal < limits.max) {
		return 'ready_to_manufacture'
	}

	return 'terminal'
}

export function stageLabel(stage: WorkOrderStage): string | undefined {
	return stageDetails[stage].label
}

export function stockEntryPurposeForStage(stage: WorkOrderStage): string | null {
	return stageDetails[stage].stockEntryPurpose ?? null
}
