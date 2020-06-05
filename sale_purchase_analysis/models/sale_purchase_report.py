from odoo import api, fields, models

STATES = {"confirm": [("readonly", True)], "done": [("readonly", True)]}


class SalePurchaseReportLine(models.Model):
    _name = "sale.purchase.report.line"
    _description = "Sale / Purchase report line"
    _order = "product_id, date, id"

    name = fields.Char(
        related="product_id.display_name", string="Name", states=STATES
    )
    sale_line_id = fields.Many2one(
        "sale.order.line",
        domain="[('product_id', '=', product_id)]",
        states=STATES,
    )
    purchase_line_id = fields.Many2one(
        "purchase.order.line",
        domain="[('product_id', '=', product_id)]",
        states=STATES,
    )
    product_id = fields.Many2one(
        "product.product", required=True, states=STATES
    )
    uom_id = fields.Many2one("uom.uom", states=STATES)
    type = fields.Selection(
        [("sale", "Sale"), ("purch", "Purchase")],
        required=True,
        default="sale",
        states=STATES,
    )
    date = fields.Datetime(default=fields.Datetime.now, states=STATES)
    qty_scheduled = fields.Float(states=STATES)
    qty_real = fields.Float(compute="_compute_qty_real", store=True)
    qty_scheduled_uom = fields.Float(compute="_compute_qty_uom", store=True)
    qty_real_uom = fields.Float(compute="_compute_qty_uom", store=True)
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda s: s.env.user.company_id.currency_id.id,
        states=STATES,
    )
    price = fields.Monetary(states=STATES)
    comment = fields.Char()
    previous_line_id = fields.Many2one("sale.purchase.report.line", index=True)
    partner_id = fields.Many2one("res.partner", required=True, states=STATES)
    qty_stock_uom = fields.Float(compute="_compute_qty_stock", store=True)
    state = fields.Selection(
        [("draft", "Planned"), ("confirm", "Confirmed"), ("done", "Done")],
        default="draft",
        readonly=True,
    )

    def _default_currency(self):
        return self.env.user.company_id.currency_id.id

    @api.depends(
        "sale_line_id",
        "sale_line_id.qty_delivered",
        "purchase_line_id",
        "purchase_line_id.qty_received",
        "type",
    )
    def _compute_qty_real(self):
        for rec in self:
            if rec.type == "sale":
                rec.qty_real = rec.sale_line_id.qty_delivered
            else:
                rec.qty_real = rec.purchase_line_id.qty_received

    @api.depends("product_id", "uom_id", "qty_real", "qty_scheduled")
    def _compute_qty_uom(self):
        for rec in self:
            rec.qty_real_uom = rec.uom_id._compute_quantity(
                rec.qty_real, rec.product_id.uom_id
            )
            rec.qty_scheduled_uom = rec.uom_id._compute_quantity(
                rec.qty_scheduled, rec.product_id.uom_id
            )

    @api.onchange("product_id")
    def onchange_product(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id

    @api.onchange("product_id", "type")
    def onchange_product_type(self):
        if self.product_id:
            if self.type == "sale":
                # FIXME : use pricelist of the partner
                self.price = self.product_id.list_price
            else:
                # FIXME : use product supplierinfo
                self.price = self.product_id.standard_price
        else:
            self.price = 0

    @api.depends(
        "previous_line_id.qty_stock_uom",
        "qty_real_uom",
        "qty_scheduled_uom",
        "type",
    )
    def _compute_qty_stock(self):
        for rec in self:
            sign = -1 if rec.type == "sale" else 1
            qty = self.qty_real_uom or self.qty_scheduled_uom
            rec.qty_stock_uom = rec.previous_line_id.qty_stock_uom + sign * qty

    def action_confirm(self):
        for rec in self:
            if rec.type == "sale":
                if not self.sale_line_id:
                    so = rec._create_sale()
                else:
                    so = rec.sale_line_id.order_id
                if so.state == "draft":
                    so.action_confirm()
            else:
                if not rec.purchase_line_id:
                    po = rec._create_purchase()
                else:
                    po = rec.purchase_line_id.order_id
                if po.state == "draft":
                    po.button_confirm()
            rec.state = "confirm"

    def _create_sale(self):
        self.ensure_one()
        values = self._prepare_sale_values()
        sale = self.env["sale.order"].create(values)
        sale.onchange_partner_id()
        line_values = self._prepare_sale_line_values()
        sale.write({"order_line": [(0, 0, line_values)]})
        return sale

    def _prepare_sale_values(self):
        return {"partner_id": self.partner_id.id, "date_order": self.date}

    def _prepare_sale_line_values(self):
        return {
            "name": self.product_id.display_name,
            "product_id": self.product_id.id,
            "product_uom": self.uom_id.id,
            "product_uom_qty": self.qty_scheduled,
            "price_unit": self.price,
            "sale_purchase_report_line_ids": [(4, self.id)],
        }

    def _create_purchase(self):
        self.ensure_one()
        values = self._prepare_purchase_values()
        purchase = self.env["purchase.order"].create(values)
        purchase.onchange_partner_id()
        line_values = self._prepare_purchase_line_values()
        purchase.write({"order_line": [(0, 0, line_values)]})
        return purchase

    def _prepare_purchase_values(self):
        return {"partner_id": self.partner_id.id, "date_order": self.date}

    def _prepare_purchase_line_values(self):
        return {
            "name": self.product_id.display_name,
            "product_id": self.product_id.id,
            "product_uom": self.uom_id.id,
            "product_qty": self.qty_scheduled,
            "price_unit": self.price,
            "date_planned": self.date,
            "sale_purchase_report_line_ids": [(4, self.id)],
        }

    @api.model_create_multi
    @api.returns("self", lambda value: value.id)
    def create(self, vals_list):
        recs = super().create(vals_list)
        recs._recompute_previous_line()
        return recs

    def write(self, values):
        res = super().write(values)
        if not self.env.context.get("_no_recompute_previous_line"):
            self._recompute_previous_line()
        return res

    def _recompute_previous_line(self):
        self = self.with_context(_no_recompute_previous_line=1)
        for rec in self:
            previous = self.search(
                [
                    ("product_id", "=", rec.product_id.id),
                    ("date", "<=", rec.date),
                    ("id", "!=", rec.id),
                ],
                order="date desc, id",
                limit=1,
            )
            following = self.search([("previous_line_id", "=", previous.id)])
            rec.previous_line_id = previous
            following.previous = rec
