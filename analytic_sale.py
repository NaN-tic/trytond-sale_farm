
from trytond.model import fields
from trytond.pool import PoolMeta

class SaleLine(metaclass=PoolMeta):
    __name__ = 'sale.line'

    @fields.depends('analytic_accounts')
    def on_change_animal(self):
        super().on_change_animal()

    @fields.depends('analytic_accounts')
    def on_change_animal_location(self):
        super().on_change_animal_location()