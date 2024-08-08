import unittest
from decimal import Decimal

from proteus import Model, Wizard
from trytond.modules.account.tests.tools import (create_chart,
                                                 create_fiscalyear,
                                                 get_accounts)
from trytond.modules.account_invoice.tests.tools import (
    create_payment_term, set_fiscalyear_invoice_sequences)
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.modules.farm.tests.tools import create_specie, create_users
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Install account_invoice
        config = activate_modules('sale_farm')

        # Create company
        _ = create_company()
        company = get_company()

        # Create fiscal year
        fiscalyear = set_fiscalyear_invoice_sequences(
            create_fiscalyear(company))
        fiscalyear.click('create_period')

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        expense = accounts['expense']
        account_cash = accounts['cash']
        Journal = Model.get('account.journal')

        # Create parties
        Party = Model.get('party.party')
        supplier = Party(name='Supplier')
        supplier.save()
        customer = Party(name='Customer')
        customer.save()

        # Create account category
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.save()

        # Create payment method
        Journal = Model.get('account.journal')
        PaymentMethod = Model.get('account.invoice.payment.method')
        journal_cash, = Journal.find([('type', '=', 'cash')])
        payment_method = PaymentMethod()
        payment_method.name = 'Cash'
        payment_method.journal = journal_cash
        payment_method.credit_account = account_cash
        payment_method.debit_account = account_cash
        payment_method.save()

        # Create products
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        kg, = ProductUom.find([('name', '=', 'Kilogram')])
        ProductTemplate = Model.get('product.template')
        Product = Model.get('product.product')
        meet_template = ProductTemplate()
        meet_template.name = 'Meet'
        meet_template.default_uom = unit
        meet_template.type = 'service'
        meet_template.salable = True
        meet_template.list_price = Decimal('3.0')
        meet_template.cost_price_method = 'fixed'
        meet_template.account_category = account_category
        meet_template.save()
        meet_product = Product()
        meet_product, = meet_template.products
        meet_product.cost_price = Decimal('0.5')
        meet_product.save()

        # Create payment term
        payment_term = create_payment_term()
        payment_term.save()

        # Create specie
        specie, breed, products = create_specie('Pig')

        # Create farm users
        users = create_users(company)
        group_user = users['group']

        # Create farm locations
        Location = Model.get('stock.location')
        warehouse, = Location.find([('type', '=', 'warehouse')])
        location = Location()
        location.name = 'Location 1'
        location.code = 'L1'
        location.type = 'storage'
        location.parent = warehouse.storage_location
        location.save()

        # Create sale user
        Group = Model.get('res.group')
        User = Model.get('res.user')
        sale_user = User()
        sale_user.name = 'Sale'
        sale_user.login = 'sale'

        for group in Group.find([('name', 'in', ['Sales', 'Farm'])]):
            sale_user.groups.append(group)

        sale_user.save()

        # Create account user
        account_user = User()
        account_user.name = 'Account'
        account_user.login = 'account'
        account_group, = Group.find([('name', '=', 'Account')])
        account_user.groups.append(account_group)
        account_user.save()

        # Create group
        AnimalGroup = Model.get('farm.animal.group')
        animal_group = AnimalGroup()
        animal_group.specie = specie
        animal_group.breed = breed
        animal_group.initial_location = location
        animal_group.initial_quantity = 40
        animal_group.save()
        config._context['locations'] = [location.id]
        animal_group = AnimalGroup(animal_group.id)
        self.assertEqual(animal_group.lot.quantity, 40.0)

        # Sale 15 animals
        config.user = sale_user.id
        Sale = Model.get('sale.sale')
        SaleLine = Model.get('sale.line')
        sale = Sale()
        sale.party = customer
        sale.payment_term = payment_term
        sale.invoice_method = 'order'
        sale_line = SaleLine()
        sale.lines.append(sale_line)
        sale_line.product = meet_product
        sale_line.quantity = 2250.0
        sale_line.animal = animal_group
        sale_line.animal_quantity = 15
        sale.save()
        sale.click('quote')
        sale.click('confirm')
        self.assertEqual(sale.state, 'processing')
        sale.reload()
        self.assertEqual(len(sale.lines[0].move_events), 1)

        self.assertEqual(len(sale.invoices), 1)
        invoice, = sale.invoices
        move_event, = sale.lines[0].move_events
        self.assertEqual(sale.shipment_state, 'waiting')

        # Send animals to customer (validate move events) and check Sale's shipment
        # state
        config.user = group_user.id
        MoveEvent = Model.get('farm.move.event')
        move_event = MoveEvent(move_event.id)
        move_event.weight = Decimal('2365.0')
        move_event.save()
        move_event.click('validate_event')
        move_event.reload()
        self.assertEqual(move_event.unit_price, Decimal('0.0'))
        config.user = sale_user.id
        sale.reload()
        self.assertEqual(sale.shipment_state, 'sent')
        invoice, = sale.invoices

        # Post invoice
        config.user = account_user.id
        Invoice = Model.get('account.invoice')
        invoice = Invoice(invoice.id)
        invoice.click('post')
        config.user = sale_user.id
        sale.reload()
        self.assertEqual(len(sale.shipments), 0)

        self.assertEqual(len(sale.shipment_returns), 0)

        self.assertEqual(len(sale.invoices), 1)

        # Pay invoice and check unit price of Move event and Lot cost price is updated
        config.user = account_user.id
        pay = Wizard('account.invoice.pay', [invoice])
        pay.form.payment_method = payment_method
        pay.execute('choice')
        invoice.reload()
        self.assertEqual(invoice.state, 'paid')
        config.user = group_user.id
        move_event = MoveEvent(move_event.id)
        self.assertEqual(move_event.unit_price, Decimal('450.00'))
        animal_group.reload()
        self.assertEqual(animal_group.lot.cost_price, Decimal('20.0000'))
        self.assertEqual(animal_group.lot.total_cost, Decimal('500.0000'))
