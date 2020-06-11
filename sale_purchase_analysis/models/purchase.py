from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_cancel(self):
        report_lines = self.mapped("order_line.sale_purchase_report_line_ids")
        report_lines._action_cancel()
        super().button_cancel()


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    sale_purchase_report_line_ids = fields.One2many(
        "sale.purchase.report.line", "purchase_line_id"
    )

    @api.model_create_multi
    @api.returns("self", lambda value: value.id)
    def create(self, vals_list):
        recs = super().create(vals_list)
        for rec in recs:
            if not rec.sale_purchase_report_line_ids:
                self.env["sale.purchase.report.line"].create(
                    {
                        "purchase_line_id": rec.id,
                        "product_id": rec.product_id.id,
                        "uom_id": rec.product_uom.id,
                        "qty_scheduled": rec.product_uom_qty,
                        "state": "confirm",
                        "partner_id": rec.partner_id.id,
                        "type": "purch",
                    }
                )
        return recs
