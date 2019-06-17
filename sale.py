# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from datetime import datetime
from decimal import Decimal

from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval, Id, Not, Or
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext

__all__ = ['MoveEvent', 'Sale', 'SaleLine']


class MoveEvent(metaclass=PoolMeta):
    __name__ = 'farm.move.event'

    origin = fields.Reference('Origin', selection='get_origin', readonly=True,
        select=True)

    @classmethod
    def _get_origin(cls):
        'Return list of Model names for origin Reference'
        return ['sale.line']

    @classmethod
    def get_origin(cls):
        pool = Pool()
        Model = pool.get('ir.model')
        models = cls._get_origin()
        models = Model.search([
                ('model', 'in', models),
                ])
        return [('', '')] + [(m.model, m.name) for m in models]

    @classmethod
    def validate_event(cls, events):
        pool = Pool()
        Sale = pool.get('sale.sale')

        sales_to_process = set()
        for event in events:
            if event.origin and isinstance(event.origin, SaleLine):
                if not event.weight:
                    raise UserError(gettext(
                            'sale_farm.msg_weight_required_in_sale_move_event',
                            event=event.rec_name))
                sales_to_process.add(event.origin.sale.id)
        user_farms = Transaction().context.get('farms')
        with Transaction().set_user(0, set_context=True), \
                Transaction().set_context(farms=user_farms):
            super(MoveEvent, cls).validate_event(events)
            if sales_to_process:
                    Sale.process(Sale.browse(list(sales_to_process)))


class Sale(metaclass=PoolMeta):
    __name__ = 'sale.sale'

    move_events = fields.Function(fields.Many2Many('farm.move.event', None,
            None, "Animal's Moves"), 'get_move_events')

    def get_move_events(self, name):
        return [m.id for l in self.lines for m in l.move_events]

    def get_shipment_state(self):
        state = super(Sale, self).get_shipment_state()
        if state in ('none', 'sent') and self.move_events:
            if all(l.move_event_done for l in self.lines):
                return 'sent'
            else:
                return 'waiting'
        return state

    @classmethod
    def process(cls, sales):
        super(Sale, cls).process(sales)
        for sale in sales:
            if sale.invoice_state != 'paid' or sale.shipment_state != 'sent':
                continue
            if not sale.move_events:
                continue
            for line in sale.lines:
                line.set_move_event_unit_price()

    def create_shipment(self, shipment_type):
        res = super(Sale, self).create_shipment(shipment_type)

        if self.shipment_method == 'manual':
            return res

        for line in self.lines:
            move_event = line.get_move_event(shipment_type)
            if move_event:
                move_event.save()
        return res


class SaleLine(metaclass=PoolMeta):
    __name__ = 'sale.line'

    animal = fields.Reference('Animal', selection='get_animal_models', states={
            'invisible': Or(Eval('type') != 'line',
                Not(Eval('context', {}).get('groups', []).contains(
                    Id('farm', 'group_farm')))),
            'readonly': ~Eval('_parent_sale', {}),
            }, depends=['type'])
    animal_type = fields.Function(fields.Selection([
            (None, ''),
            ('male', 'Male'),
            ('female', 'Female'),
            ('individual', 'Individual'),
            ('group', 'Group'),
            ], 'Animal Type'),
        'on_change_with_animal_type')
    animal_location = fields.Many2One('stock.location', 'Animal Location',
        domain=[
            ('type', '=', 'storage'),
            ], states={
            'invisible': ~Bool(Eval('animal_type')),
            'required': Bool(Eval('animal_type')),
            'readonly': Eval('animal_type', '') != 'group',
            }, depends=['animal_type'])
    animal_quantity = fields.Integer('Animal Quantity', states={
            'invisible': Eval('animal_type', '') != 'group',
            'required': Eval('animal_type', '') == 'group',
            }, depends=['animal_type'])
    move_events = fields.One2Many('farm.move.event', 'origin',
        "Animal's Moves", readonly=True)

    @classmethod
    def __setup__(cls):
        super(SaleLine, cls).__setup__()
        if hasattr(cls, 'analytic_accounts'):
            cls.animal.on_change.add('analytic_accounts')
            cls.animal_location.on_change.add('analytic_accounts')

    @classmethod
    def get_animal_models(cls):
        IrModel = Pool().get('ir.model')
        models = IrModel.search([
                ('model', 'in', [
                        'farm.animal',
                        'farm.animal.group',
                        ]),
                ])
        return [('', '')] + [(m.model, m.name) for m in models]

    @fields.depends('type', 'animal', 'sale', '_parent_sale.sale_date')
    def on_change_animal(self):
        Animal = Pool().get('farm.animal')

        self.animal_location = None
        self.animal_quantity = None
        if (not self.type or self.type != 'line' or not self.animal or
                self.animal.id < 0):
            return

        analytic_accounts = None
        if isinstance(self.animal, Animal):
            self.animal_location = (self.animal.location
                if self.animal.location else None)
            self.animal_quantity = 1
            if hasattr(self.animal.location, 'analytic_accounts'):
                analytic_accounts = self.animal.location.analytic_accounts
        elif len(self.animal.locations) == 1:
            group_location = self.animal.locations[0]
            with Transaction().set_context(
                    locations=[group_location.id],
                    stock_date_end=(self.sale.sale_date
                        if self.sale and self.sale.sale_date else None)):
                self.animal_location = group_location
                self.animal_quantity = self.animal.quantity or None
                if hasattr(group_location, 'analytic_accounts'):
                    analytic_accounts = group_location.analytic_accounts

        if (self.animal_location and hasattr(self, 'analytic_accounts') and
                analytic_accounts):
            for account in analytic_accounts.accounts:
                setattr(self, 'analytic_account_%s' % account.root.id,
                    account.id)

    @fields.depends('type', 'animal')
    def on_change_with_animal_type(self, name=None):
        Animal = Pool().get('farm.animal')
        if not self.type or not self.animal or self.animal.id < 0:
            return None
        if isinstance(self.animal, Animal):
            return self.animal.type
        return 'group'

    @fields.depends('animal', 'animal_location', 'sale',
        '_parent_sale.sale_date')
    def on_change_animal_location(self):
        if not self.animal or not self.animal_location:
            self.animal_quantity = None
            return
        with Transaction().set_context(
                locations=[self.animal_location.id],
                stock_date_end=(self.sale.sale_date
                    if self.sale and self.sale.sale_date else None)):
            self.animal_quantity = self.animal.lot.quantity or None
        if (hasattr(self, 'analytic_accounts') and
                self.animal_location.analytic_accounts):
            for account in self.animal_location.analytic_accounts.accounts:
                setattr(self, 'analytic_account_%s' % account.root.id,
                    account.id)

    @property
    def move_event_done(self):
        if not self.animal_type:
            return True

        quantity = self.animal_quantity
        for event in self.move_events:
            if event.state == 'draft':
                return False
            if event.state == 'validated':
                quantity -= event.quantity
        if (self.animal_quantity > 0 and quantity > 0 or
                self.animal_quantity < 0 and quantity < 0):
            return False
        return True

    def get_move_event(self, shipment_type):
        '''
        Return move event for the sale line according ot shipment_type
        '''
        pool = Pool()
        MoveEvent = pool.get('farm.move.event')

        if self.type != 'line':
            return
        if not self.animal_type:
            return
        if (shipment_type == 'out') != (self.animal_quantity >= 0):
            return

        quantity = self.animal_quantity
        for event in self.move_events:
            if event.state != 'cancel':
                quantity -= event.quantity
        if (self.animal_quantity > 0 and quantity <= 0 or
                self.animal_quantity < 0 and quantity >= 0):
            return

        if not self.sale.party.customer_location:
            raise UserError(gettext('sale.msg_sale_customer_location_required',
                    sale=self.sale.rec_name,
                    line=self.rec_name,
                    ))

        with Transaction().set_user(0, set_context=True):
            move_event = MoveEvent()
        move_event.animal_type = self.animal_type
        move_event.specie = self.animal.specie
        move_event.farm = self.animal_location.warehouse
        if self.animal_type == 'group':
            move_event.animal_group = self.animal
        else:
            move_event.animal = self.animal
        move_event.timestamp = datetime.combine(self.shipping_date,
            datetime.now().time()) if self.shipping_date else datetime.now()
        move_event.from_location = self.animal_location
        move_event.to_location = self.sale.party.customer_location
        move_event.quantity = self.animal_quantity
        move_event.unit_price = Decimal('0.0')
        move_event.origin = self
        return move_event

    def set_move_event_unit_price(self):
        pool = Pool()
        ModelData = pool.get('ir.model.data')
        LotCostLine = pool.get('stock.lot.cost_line')

        invoice_amount = sum(il.on_change_with_amount()
            for il in self.invoice_lines if il.invoice.paid)
        delivered_animals = sum(e.quantity for e in self.move_events
            if e.state == 'validated')
        unit_price = self.sale.currency.round(invoice_amount
            / delivered_animals)

        category_id = ModelData.get_id('sale_farm', 'cost_category_sale_price')
        lot = self.animal.lot
        for event in self.move_events:
            if event.state != 'validated':
                continue
            event.unit_price = unit_price
            event.save()

            if lot.cost_price != unit_price:
                cost_line = LotCostLine()
                cost_line.lot = lot
                cost_line.category = category_id
                cost_line.origin = str(event)
                cost_line.unit_price = self.sale.currency.round(
                    unit_price - lot.cost_price
                    if lot.cost_price else unit_price)
                cost_line.save()

    @classmethod
    def copy(cls, lines, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default.setdefault('move_events', None)
        return super(SaleLine, cls).copy(lines, default=default)
