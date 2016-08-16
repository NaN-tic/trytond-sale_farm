==================
Sale Farm Scenario
==================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax, set_tax_code
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences, create_payment_term
    >>> today = datetime.date.today()

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install sale_farm::

    >>> Module = Model.get('ir.module')
    >>> sale_module, = Module.find([('name', '=', 'sale_farm')])
    >>> Module.install([sale_module.id], config.context)
    >>> Wizard('ir.module.install_upgrade').execute('upgrade')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Reload the context::

    >>> User = Model.get('res.user')
    >>> Group = Model.get('res.group')
    >>> config._context = User.get_preferences(True, config.context)

Create sale user::

    >>> sale_user = User()
    >>> sale_user.name = 'Sale'
    >>> sale_user.login = 'sale'
    >>> sale_user.main_company = company
    >>> for group in Group.find([('name', 'in', ['Sales', 'Farm'])]):
    ...     sale_user.groups.append(group)
    >>> sale_user.save()

Create stock user::

    >>> farm_user = User()
    >>> farm_user.name = 'Stock'
    >>> farm_user.login = 'stock'
    >>> farm_user.main_company = company
    >>> for group in Group.find([('name', 'in', ['Farm', 'Farm / Groups'])]):
    ...     farm_user.groups.append(group)
    >>> farm_user.save()

Create account user::

    >>> account_user = User()
    >>> account_user.name = 'Account'
    >>> account_user.login = 'account'
    >>> account_user.main_company = company
    >>> account_group, = Group.find([('name', '=', 'Account')])
    >>> account_user.groups.append(account_group)
    >>> account_user.save()

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')
    >>> period = fiscalyear.periods[0]

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> payable = accounts['payable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> account_tax = accounts['tax']
    >>> account_cash = accounts['cash']
    >>> Journal = Model.get('account.journal')
    >>> cash_journal, = Journal.find([('type', '=', 'cash')])
    >>> cash_journal.credit_account = account_cash
    >>> cash_journal.debit_account = account_cash
    >>> cash_journal.save()

Create parties::

    >>> Party = Model.get('party.party')
    >>> supplier = Party(name='Supplier')
    >>> supplier.save()
    >>> customer = Party(name='Customer')
    >>> customer.save()

Create products::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> kg, = ProductUom.find([('name', '=', 'Kilogram')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> group_template = ProductTemplate(
    ...     name='Group of Pig',
    ...     default_uom=unit,
    ...     type='goods',
    ...     list_price=Decimal('100'),
    ...     cost_price=Decimal('30'))
    >>> group_template.save()
    >>> group_product = Product(template=group_template)
    >>> group_product.save()
    >>> meet_template = ProductTemplate()
    >>> meet_template.name = 'Meet'
    >>> meet_template.default_uom = unit
    >>> meet_template.type = 'service'
    >>> meet_template.salable = True
    >>> meet_template.list_price = Decimal('3.0')
    >>> meet_template.cost_price = Decimal('0.5')
    >>> meet_template.cost_price_method = 'fixed'
    >>> meet_template.account_expense = expense
    >>> meet_template.account_revenue = revenue
    >>> meet_template.save()
    >>> meet_product = Product()
    >>> meet_product.template = meet_template
    >>> meet_product.save()

Create payment term::

    >>> payment_term = create_payment_term()
    >>> payment_term.save()

Create sequence::

    >>> Sequence = Model.get('ir.sequence')
    >>> event_order_sequence = Sequence(
    ...     name='Event Order Pig Warehouse 1',
    ...     code='farm.event.order',
    ...     padding=4)
    >>> event_order_sequence.save()
    >>> group_sequence = Sequence(
    ...     name='Groups Pig Warehouse 1',
    ...     code='farm.animal.group',
    ...     padding=4)
    >>> group_sequence.save()

Create specie::

    >>> Location = Model.get('stock.location')
    >>> lost_found_location, = Location.find([('type', '=', 'lost_found')])
    >>> warehouse, = Location.find([('type', '=', 'warehouse')])
    >>> Specie = Model.get('farm.specie')
    >>> SpecieBreed = Model.get('farm.specie.breed')
    >>> SpecieFarmLine = Model.get('farm.specie.farm_line')
    >>> pigs_specie = Specie(
    ...     name='Pigs',
    ...     male_enabled=False,
    ...     female_enabled=False,
    ...     individual_enabled=False,
    ...     group_enabled=True,
    ...     group_product=group_product,
    ...     removed_location=lost_found_location,
    ...     foster_location=lost_found_location,
    ...     lost_found_location=lost_found_location,
    ...     feed_lost_found_location=lost_found_location)
    >>> pigs_specie.save()
    >>> pigs_breed = SpecieBreed(
    ...     specie=pigs_specie,
    ...     name='Holland')
    >>> pigs_breed.save()
    >>> pigs_farm_line = SpecieFarmLine(
    ...     specie=pigs_specie,
    ...     farm=warehouse,
    ...     event_order_sequence=event_order_sequence,
    ...     has_group=True,
    ...     group_sequence=group_sequence)
    >>> pigs_farm_line.save()

Create farm locations::

    >>> location_id, = Location.create([{
    ...         'name': 'Location 1',
    ...         'code': 'L1',
    ...         'type': 'storage',
    ...         'parent': warehouse.storage_location.id,
    ...         }], config.context)


Create group::

    >>> AnimalGroup = Model.get('farm.animal.group')
    >>> animal_group = AnimalGroup(
    ...     specie=pigs_specie,
    ...     breed=pigs_breed,
    ...     initial_location=location_id,
    ...     initial_quantity=40)
    >>> animal_group.save()
    >>> unused = config.set_context({
    ...         'locations': [location_id]})
    >>> animal_group.reload()
    >>> animal_group.lot.quantity
    40.0

Sale 15 animals::

    >>> config.user = sale_user.id
    >>> Sale = Model.get('sale.sale')
    >>> SaleLine = Model.get('sale.line')
    >>> sale = Sale()
    >>> sale.party = customer
    >>> sale.payment_term = payment_term
    >>> sale.invoice_method = 'order'
    >>> sale_line = SaleLine()
    >>> sale.lines.append(sale_line)
    >>> sale_line.product = meet_product
    >>> sale_line.quantity = 2250.0
    >>> sale_line.animal = animal_group
    >>> sale_line.animal_quantity = 15
    >>> sale.click('quote')
    >>> sale.click('confirm')
    >>> sale.click('process')
    >>> sale.state
    u'processing'
    >>> sale.reload()
    >>> len(sale.lines[0].move_events), len(sale.invoices)
    (1, 1)
    >>> invoice, = sale.invoices
    >>> move_event, = sale.lines[0].move_events
    >>> sale.shipment_state
    u'waiting'


Send animals to customer (validate move events) and check Sale's shipment
state::

    >>> config.user = farm_user.id
    >>> MoveEvent = Model.get('farm.move.event')
    >>> move_event = MoveEvent(move_event.id)
    >>> move_event.weight = Decimal('2365.0')
    >>> move_event.save()
    >>> MoveEvent.validate_event([move_event.id], config.context)
    >>> move_event.reload()
    >>> move_event.unit_price
    Decimal('0.0')
    >>> config.user = sale_user.id
    >>> sale.reload()
    >>> sale.shipment_state
    u'sent'
    >>> invoice, = sale.invoices

Post invoice::

    >>> config.user = account_user.id
    >>> Invoice = Model.get('account.invoice')
    >>> invoice = Invoice(invoice.id)
    >>> invoice.click('post')
    >>> Invoice.post([invoice.id], config.context)
    >>> config.user = sale_user.id
    >>> sale.reload()
    >>> len(sale.shipments), len(sale.shipment_returns), len(sale.invoices)
    (0, 0, 1)

Pay invoice and check unit price of Move event and Lot cost price is updated::

    >>> config.user = account_user.id
    >>> pay = Wizard('account.invoice.pay', [invoice])
    >>> pay.form.journal = cash_journal
    >>> pay.execute('choice')
    >>> invoice.reload()
    >>> invoice.state
    u'paid'
    >>> config.user = farm_user.id
    >>> move_event = MoveEvent(move_event.id)
    >>> move_event.unit_price
    Decimal('450.00')
    >>> animal_group.reload()
    >>> animal_group.lot.cost_price
    Decimal('450.00')
