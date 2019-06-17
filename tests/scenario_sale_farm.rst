==================
Sale Farm Scenario
==================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax, create_tax_code
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences, create_payment_term
    >>> from trytond.modules.farm.tests.tools import create_specie, create_users
    >>> today = datetime.date.today()

Install account_invoice::

    >>> config = activate_modules('sale_farm')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

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

Create account category::

    >>> ProductCategory = Model.get('product.category')
    >>> account_category = ProductCategory(name="Account Category")
    >>> account_category.accounting = True
    >>> account_category.account_expense = expense
    >>> account_category.account_revenue = revenue
    >>> account_category.save()

Create payment method::

    >>> Journal = Model.get('account.journal')
    >>> PaymentMethod = Model.get('account.invoice.payment.method')
    >>> Sequence = Model.get('ir.sequence')
    >>> journal_cash, = Journal.find([('type', '=', 'cash')])
    >>> payment_method = PaymentMethod()
    >>> payment_method.name = 'Cash'
    >>> payment_method.journal = journal_cash
    >>> payment_method.credit_account = account_cash
    >>> payment_method.debit_account = account_cash
    >>> payment_method.save()

Create products::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> kg, = ProductUom.find([('name', '=', 'Kilogram')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> meet_template = ProductTemplate()
    >>> meet_template.name = 'Meet'
    >>> meet_template.default_uom = unit
    >>> meet_template.type = 'service'
    >>> meet_template.salable = True
    >>> meet_template.list_price = Decimal('3.0')
    >>> meet_template.cost_price_method = 'fixed'
    >>> meet_template.account_category = account_category
    >>> meet_template.save()
    >>> meet_product = Product()
    >>> meet_product, = meet_template.products
    >>> meet_product.cost_price = Decimal('0.5')
    >>> meet_product.save()

Create payment term::

    >>> payment_term = create_payment_term()
    >>> payment_term.save()

Create specie::

    >>> specie, breed, products = create_specie('Pig')
    >>> individual_product = products['individual']
    >>> group_product = products['group']
    >>> female_product = products['female']
    >>> male_product = products['male']
    >>> semen_product = products['semen']

Create farm users::

    >>> users = create_users(company)
    >>> individual_user = users['individual']
    >>> group_user = users['group']
    >>> female_user = users['female']
    >>> male_user = users['male']

Create farm locations::

    >>> Location = Model.get('stock.location')
    >>> warehouse, = Location.find([('type', '=', 'warehouse')])
    >>> location = Location()
    >>> location.name = 'Location 1'
    >>> location.code = 'L1'
    >>> location.type = 'storage'
    >>> location.parent = warehouse.storage_location
    >>> location.save()

Create sale user::

    >>> Group = Model.get('res.group')
    >>> User = Model.get('res.user')
    >>> sale_user = User()
    >>> sale_user.name = 'Sale'
    >>> sale_user.login = 'sale'
    >>> sale_user.main_company = company
    >>> for group in Group.find([('name', 'in', ['Sales', 'Farm'])]):
    ...     sale_user.groups.append(group)
    >>> sale_user.save()

Create account user::

    >>> account_user = User()
    >>> account_user.name = 'Account'
    >>> account_user.login = 'account'
    >>> account_user.main_company = company
    >>> account_group, = Group.find([('name', '=', 'Account')])
    >>> account_user.groups.append(account_group)
    >>> account_user.save()

Create group::

    >>> AnimalGroup = Model.get('farm.animal.group')
    >>> animal_group = AnimalGroup()
    >>> animal_group.specie = specie
    >>> animal_group.breed = breed
    >>> animal_group.initial_location = location
    >>> animal_group.initial_quantity = 40
    >>> animal_group.save()
    >>> config._context['locations'] = [location.id]
    >>> animal_group = AnimalGroup(animal_group.id)
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
    >>> sale.click('quote')
    >>> sale.click('confirm')
    >>> sale.state
    'processing'
    >>> sale.reload()
    >>> len(sale.lines[0].move_events), len(sale.invoices)
    (1, 1)
    >>> invoice, = sale.invoices
    >>> move_event, = sale.lines[0].move_events
    >>> sale.shipment_state
    'waiting'


Send animals to customer (validate move events) and check Sale's shipment
state::

    >>> config.user = group_user.id
    >>> MoveEvent = Model.get('farm.move.event')
    >>> move_event = MoveEvent(move_event.id)
    >>> move_event.weight = Decimal('2365.0')
    >>> move_event.save()
    >>> move_event.click('validate_event')
    >>> move_event.reload()
    >>> move_event.unit_price
    Decimal('0.0')
    >>> config.user = sale_user.id
    >>> sale.reload()
    >>> sale.shipment_state
    'sent'
    >>> invoice, = sale.invoices

Post invoice::

    >>> config.user = account_user.id
    >>> Invoice = Model.get('account.invoice')
    >>> invoice = Invoice(invoice.id)
    >>> invoice.click('post')
    >>> config.user = sale_user.id
    >>> sale.reload()
    >>> len(sale.shipments), len(sale.shipment_returns), len(sale.invoices)
    (0, 0, 1)

Pay invoice and check unit price of Move event and Lot cost price is updated::

    >>> config.user = account_user.id
    >>> pay = Wizard('account.invoice.pay', [invoice])
    >>> pay.form.payment_method = payment_method
    >>> pay.execute('choice')
    >>> invoice.reload()
    >>> invoice.state
    'paid'
    >>> config.user = group_user.id
    >>> move_event = MoveEvent(move_event.id)
    >>> move_event.unit_price
    Decimal('450.00')
    >>> animal_group.reload()
    >>> animal_group.lot.cost_price
    Decimal('450.00')
