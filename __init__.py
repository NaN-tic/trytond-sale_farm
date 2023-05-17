# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import sale
from . import analytic_sale

def register():
    Pool.register(
        sale.MoveEvent,
        sale.Sale,
        sale.SaleLine,
        module='sale_farm', type_='model')

    Pool.register(
        analytic_sale.SaleLine,
        module='sale_farm', type_='model', depends=['analytic_sale'])