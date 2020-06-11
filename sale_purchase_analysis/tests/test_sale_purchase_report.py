from odoo.tests import Form, common


class TestSalePurchaseReport(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {"name": "product A", "type": "product"}
        )
        cls.vendor = cls.env["res.partner"].create({"name": "vendor1"})
        cls.customer = cls.env["res.partner"].create({"name": "customer1"})
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.uom_dozen = cls.env.ref("uom.product_uom_dozen")

    def check_report_line(self, report_line, expected):
        data = report_line.read(expected, load="_classic_write")[0]
        data.pop("id")
        self.assertEqual(data, expected)

    def _create_sale(self):
        so = Form(self.env["sale.order"])
        so.partner_id = self.customer
        with so.order_line.new() as so_line:
            so_line.product_id = self.product
            so_line.product_uom_qty = 2
            so_line.price_unit = 100

        so = so.save()
        return so

    def _create_po(self):
        po = Form(self.env["purchase.order"])
        po.partner_id = self.vendor
        with po.order_line.new() as po_line:
            po_line.product_id = self.product
            po_line.product_qty = 11
            po_line.price_unit = 100

        po = po.save()
        return po

    def test_create_po_creates_report_line(self):
        po = self._create_po()
        # check creation of report line
        report_line = po.order_line.sale_purchase_report_line_ids
        self.assertEqual(len(report_line), 1)
        expected = {
            "partner_id": self.vendor.id,
            "type": "purch",
            "product_id": self.product.id,
            "qty_scheduled": 11,
            "qty_scheduled_uom": 11,
            "qty_real": 0,
            "qty_real_uom": 0,
            "state": "confirm",
        }
        self.check_report_line(report_line, expected)

    def test_create_so_creates_report_line(self):
        so = self._create_sale()
        # check creation of report line
        report_line = so.order_line.sale_purchase_report_line_ids
        self.assertEqual(len(report_line), 1)
        expected = {
            "partner_id": self.customer.id,
            "type": "sale",
            "product_id": self.product.id,
            "qty_scheduled": 2,
            "qty_scheduled_uom": 2,
            "qty_real": 0,
            "qty_real_uom": 0,
            "state": "confirm",
        }
        self.check_report_line(report_line, expected)

    def test_unit_conversions(self):
        line = Form(self.env["sale.purchase.report.line"])
        line.partner_id = self.vendor
        line.type = "purch"
        line.product_id = self.product
        line.uom_id = self.uom_dozen
        line.qty_scheduled = 10
        line.price = 80
        line = line.save()
        self.assertEqual(line.qty_scheduled_uom, 120)

    def test_confirm_purch_line_creates_po(self):
        line = Form(self.env["sale.purchase.report.line"])
        line.partner_id = self.vendor
        line.type = "purch"
        line.product_id = self.product
        line.qty_scheduled = 10
        line.price = 80
        line = line.save()
        self.assertFalse(line.sale_line_id)
        self.assertFalse(line.purchase_line_id)
        line.action_confirm()
        self.assertTrue(line.purchase_line_id)
        self.assertFalse(line.sale_line_id)
        self.assertEqual(line.purchase_line_id.order_id.state, "purchase")

    def test_confirm_sale_line_creates_so(self):
        line = Form(self.env["sale.purchase.report.line"])
        line.partner_id = self.customer
        line.type = "sale"
        line.product_id = self.product
        line.qty_scheduled = 10
        line.price = 80
        line = line.save()
        self.assertFalse(line.sale_line_id)
        self.assertFalse(line.purchase_line_id)
        line.action_confirm()
        self.assertTrue(line.sale_line_id)
        self.assertFalse(line.purchase_line_id)
        self.assertEqual(line.sale_line_id.order_id.state, "sale")

    def test_shipping(self):
        pass
