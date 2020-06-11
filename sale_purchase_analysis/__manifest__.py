# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Sales Purchase Analysis",
    "version": "13.0.1.0.0",
    "summary": "Compare day to day sales and purchases",
    "author": "Camptocamp, Odoo Community Association (OCA)",
    "category": "Purchase Management",
    "license": "AGPL-3",
    "depends": ["sale_stock", "purchase_stock"],
    "data": [
        "views/sale_purchase_report.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "auto_install": False,
}
