==================
Sale Farm Scenario
==================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> today = datetime.date.today()

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install sale::

    >>> Module = Model.get('ir.module.module')
    >>> sale_module, = Module.find([('name', '=', 'sale_farm')])
    >>> Module.install([sale_module.id], config.context)
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')

Create company::

    >>> Currency = Model.get('currency.currency')
    >>> CurrencyRate = Model.get('currency.currency.rate')
    >>> currencies = Currency.find([('code', '=', 'EUR')])
    >>> if not currencies:
    ...     currency = Currency(name='Euro', symbol=u'€', code='EUR',
    ...         rounding=Decimal('0.01'), mon_grouping='[3, 3, 0]',
    ...         mon_decimal_point=',')
    ...     currency.save()
    ...     CurrencyRate(date=today + relativedelta(month=1, day=1),
    ...         rate=Decimal('1.0'), currency=currency).save()
    ... else:
    ...     currency, = currencies
    >>> Company = Model.get('company.company')
    >>> Party = Model.get('party.party')
    >>> company_config = Wizard('company.company.config')
    >>> company_config.execute('company')
    >>> company = company_config.form
    >>> party = Party(name='B2CK')
    >>> party.save()
    >>> company.party = party
    >>> company.currency = currency
    >>> company_config.execute('add')
    >>> company, = Company.find([])

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

    >>> FiscalYear = Model.get('account.fiscalyear')
    >>> Sequence = Model.get('ir.sequence')
    >>> SequenceStrict = Model.get('ir.sequence.strict')
    >>> fiscalyear = FiscalYear(name=str(today.year))
    >>> fiscalyear.start_date = today + relativedelta(month=1, day=1)
    >>> fiscalyear.end_date = today + relativedelta(month=12, day=31)
    >>> fiscalyear.company = company
    >>> post_move_seq = Sequence(name=str(today.year), code='account.move',
    ...     company=company)
    >>> post_move_seq.save()
    >>> fiscalyear.post_move_sequence = post_move_seq
    >>> invoice_seq = SequenceStrict(name=str(today.year),
    ...     code='account.invoice', company=company)
    >>> invoice_seq.save()
    >>> fiscalyear.out_invoice_sequence = invoice_seq
    >>> fiscalyear.in_invoice_sequence = invoice_seq
    >>> fiscalyear.out_credit_note_sequence = invoice_seq
    >>> fiscalyear.in_credit_note_sequence = invoice_seq
    >>> fiscalyear.save()
    >>> FiscalYear.create_period([fiscalyear.id], config.context)

Create chart of accounts::

    >>> AccountTemplate = Model.get('account.account.template')
    >>> Account = Model.get('account.account')
    >>> account_template, = AccountTemplate.find([('parent', '=', None)])
    >>> create_chart = Wizard('account.create_chart')
    >>> create_chart.execute('account')
    >>> create_chart.form.account_template = account_template
    >>> create_chart.form.company = company
    >>> create_chart.execute('create_account')
    >>> receivable, = Account.find([
    ...         ('kind', '=', 'receivable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> payable, = Account.find([
    ...         ('kind', '=', 'payable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> revenue, = Account.find([
    ...         ('kind', '=', 'revenue'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> expense, = Account.find([
    ...         ('kind', '=', 'expense'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> create_chart.form.account_receivable = receivable
    >>> create_chart.form.account_payable = payable
    >>> create_chart.execute('create_properties')

Create parties::

    >>> Party = Model.get('party.party')
    >>> supplier = Party(name='Supplier')
    >>> supplier.save()
    >>> customer = Party(name='Customer')
    >>> customer.save()

Create category::

    >>> ProductCategory = Model.get('product.category')
    >>> category = ProductCategory(name='Category')
    >>> category.save()

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
    >>> meet_template.category = category
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

    >>> PaymentTerm = Model.get('account.invoice.payment_term')
    >>> PaymentTermLine = Model.get('account.invoice.payment_term.line')
    >>> payment_term = PaymentTerm(name='Direct')
    >>> payment_term_line = PaymentTermLine(type='remainder', days=0)
    >>> payment_term.lines.append(payment_term_line)
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
    >>> sale.save()
    >>> Sale.quote([sale.id], config.context)
    >>> Sale.confirm([sale.id], config.context)
    >>> Sale.process([sale.id], config.context)
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


Post invoice::

    >>> config.user = account_user.id
    >>> Invoice = Model.get('account.invoice')
    >>> Invoice.post([i.id for i in sale.invoices], config.context)
    >>> config.user = sale_user.id
    >>> sale.reload()
    >>> len(sale.shipments), len(sale.shipment_returns), len(sale.invoices)
    (1, 0, 1)

Pay invoice (TODO) and check unit price of Move event and Lot cost price is
updated::
