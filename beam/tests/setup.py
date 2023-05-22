import datetime
import types

import frappe
from frappe.desk.page.setup_wizard.setup_wizard import setup_complete
from erpnext.setup.utils import enable_all_roles_and_domains, set_defaults_for_tests
from erpnext.accounts.doctype.account.account import update_account_number


def before_test():
	frappe.clear_cache()
	today = frappe.utils.getdate()
	setup_complete(
		{
			"currency": "USD",
			"full_name": "Administrator",
			"company_name": "Ambrosia Pie Company",
			"timezone": "America/New_York",
			"company_abbr": "APC",
			"domains": ["Distribution"],
			"country": "United States",
			"fy_start_date": today.replace(month=1, day=1).isoformat(),
			"fy_end_date": today.replace(month=12, day=31).isoformat(),
			"language": "english",
			"company_tagline": "Ambrosia Pie Company",
			"email": "support@agritheory.dev",
			"password": "admin",
			"chart_of_accounts": "Standard with Numbers",
			"bank_account": "Primary Checking",
		}
	)
	enable_all_roles_and_domains()
	set_defaults_for_tests()
	frappe.db.commit()
	create_test_data()
	for modu in frappe.get_all("Module Onboarding"):
		frappe.db.set_value("Module Onboarding", modu, "is_complete", 1)
	frappe.set_value("Website Settings", "Website Settings", "home_page", "login")
	frappe.db.commit()


def create_test_data():
	settings = frappe._dict(
		{
			"day": datetime.date(int(frappe.defaults.get_defaults().get("fiscal_year")), 1, 1),
			"company": frappe.defaults.get_defaults().get("company"),
			"company_account": frappe.get_value(
				"Account",
				{
					"account_type": "Bank",
					"company": frappe.defaults.get_defaults().get("company"),
					"is_group": 0,
				},
			),
		}
	)
	company_address = frappe.new_doc("Address")
	company_address.title = settings.company
	company_address.address_type = "Office"
	company_address.address_line1 = "67C Sweeny Street"
	company_address.city = "Chelsea"
	company_address.state = "MA"
	company_address.pincode = "89077"
	company_address.is_your_company_address = 1
	company_address.append("links", {"link_doctype": "Company", "link_name": settings.company})
	company_address.save()
	frappe.set_value("Company", settings.company, "tax_id", "04-1871930")
	create_warehouses(settings)
	create_workstations()
	create_operations()
	create_item_groups(settings)
	create_suppliers(settings)
	create_items(settings)
	create_boms(settings)


def create_suppliers(settings):
	if not frappe.db.exists("Supplier Group", "Bakery"):
		bsg = frappe.new_doc("Supplier Group")
		bsg.supplier_group_name = "Bakery"
		bsg.parent_supplier_group = "All Supplier Groups"
		bsg.save()

	addresses = frappe._dict({})
	for supplier in suppliers:
		biz = frappe.new_doc("Supplier")
		biz.supplier_name = supplier[0]
		biz.supplier_group = "Bakery"
		biz.country = "United States"
		biz.supplier_default_mode_of_payment = supplier[2]
		if biz.supplier_default_mode_of_payment == "ACH/EFT":
			biz.bank = "Local Bank"
			biz.bank_account = "123456789"
		biz.currency = "USD"
		biz.default_price_list = "Standard Buying"
		biz.save()

		existing_address = frappe.get_value("Address", {"address_line1": supplier[5]["address_line1"]})
		if not existing_address:
			addr = frappe.new_doc("Address")
			addr.address_title = f"{supplier[0]} - {supplier[5]['city']}"
			addr.address_type = "Billing"
			addr.address_line1 = supplier[5]["address_line1"]
			addr.city = supplier[5]["city"]
			addr.state = supplier[5]["state"]
			addr.country = supplier[5]["country"]
			addr.pincode = supplier[5]["pincode"]
		else:
			addr = frappe.get_doc("Address", existing_address)
		addr.append("links", {"link_doctype": "Supplier", "link_name": supplier[0]})
		addr.save()


def create_workstations():
	for ws in workstations:
		if frappe.db.exists("Workstation", ws[0]):
			continue
		work = frappe.new_doc("Workstation")
		work.workstation_name = ws[0]
		work.production_capacity = ws[1]
		work.save()


def create_operations():
	for op in operations:
		if frappe.db.exists("Operation", op[0]):
			continue
		oper = frappe.new_doc("Operation")
		oper.name = op[0]
		oper.workstation = op[1]
		oper.batch_size = op[2]
		oper.description = op[3]
		oper.save()


def create_item_groups(settings):
	for ig_name in (
		"Baked Goods",
		"Bakery Supplies",
		"Ingredients",
		"Bakery Equipment",
		"Sub Assemblies",
	):
		if frappe.db.exists("Item Group", ig_name):
			continue
		ig = frappe.new_doc("Item Group")
		ig.item_group_name = ig_name
		ig.parent_item_group = "All Item Groups"
		ig.save()


def create_items(settings):
	if not frappe.db.exists("Price List", "Bakery Buying"):
		pl = frappe.new_doc("Price List")
		pl.price_list_name = "Bakery Buying"
		pl.buying = 1
		pl.append("countries", {"country": "United States"})
		pl.save()

	if not frappe.db.exists("Price List", "Bakery Wholesale"):
		pl = frappe.new_doc("Price List")
		pl.price_list_name = "Bakery Wholesale"
		pl.selling = 1
		pl.append("countries", {"country": "United States"})
		pl.save()

	if not frappe.db.exists("Pricing Rule", "Bakery Retail"):
		pr = frappe.new_doc("Pricing Rule")
		pr.title = "Bakery Retail"
		pr.selling = 1
		pr.apply_on = "Item Group"
		pr.company = settings.company
		pr.margin_type = "Percentage"
		pr.margin_rate_or_amount = 2.00
		pr.valid_from = settings.day
		pr.for_price_list = "Bakery Wholesale"
		pr.append("item_groups", {"item_group": "Baked Goods"})
		pr.save()

	for item in items:
		if frappe.db.exists("Item", item.get("item_code")):
			continue
		i = frappe.new_doc("Item")
		i.item_code = item.get("item_code")
		i.item_group = item.get("item_group")
		i.stock_uom = item.get("uom")
		i.description = item.get("description")
		i.maintain_stock = 1
		i.include_item_in_manufacturing = 1
		i.default_warehouse = settings.get("warehouse")
		i.default_material_request_type = (
			"Purchase" if item.get("item_group") in ("Bakery Supplies", "Ingredients") else "Manufacture"
		)
		i.valuation_method = "FIFO"
		i.is_purchase_item = 1 if item.get("item_group") in ("Bakery Supplies", "Ingredients") else 0
		i.is_sales_item = 1 if item.get("item_group") == "Baked Goods" else 0
		i.append(
			"item_defaults",
			{"company": settings.company, "default_warehouse": item.get("default_warehouse")},
		)
		if i.is_purchase_item and item.get("supplier"):
			i.append("supplier_items", {"supplier": item.get("supplier")})
		i.save()
		if item.get("item_price"):
			ip = frappe.new_doc("Item Price")
			ip.item_code = i.item_code
			ip.uom = i.stock_uom
			ip.price_list = "Bakery Wholesale" if i.is_sales_item else "Bakery Buying"
			ip.buying = 1
			ip.valid_from = "2018-1-1"
			ip.price_list_rate = item.get("item_price")
			ip.save()


def create_warehouses(settings):
	warehouses = [item.get("default_warehouse") for item in items]
	root_wh = frappe.get_value("Warehouse", {"company": settings.company, "is_group": 1})
	if frappe.db.exists("Warehouse", "Stores - APC"):
		frappe.rename_doc("Warehouse", "Stores - APC", "Storeroom - APC", force=True)
	for wh in frappe.get_all("Warehouse", {"company": settings.company}, ["name", "is_group"]):
		if wh.name not in warehouses and not wh.is_group:
			frappe.delete_doc("Warehouse", wh.name)
	for item in items:
		if frappe.db.exists("Warehouse", item.get("default_warehouse")):
			continue
		wh = frappe.new_doc("Warehouse")
		wh.warehouse_name = item.get("default_warehouse").split(" - ")[0]
		wh.parent_warehouse = root_wh
		wh.company = settings.company
		wh.save()


def create_boms(settings):
	has_bom = [b.get("item") for b in boms]
	for bom in boms:
		if frappe.db.exists("BOM", {"item": bom.get("item")}):
			continue
		b = frappe.new_doc("BOM")
		b.item = bom.get("item")
		b.quantity = bom.get("quantity")
		b.uom = bom.get("uom")
		b.company = settings.company
		b.rm_cost_as_per = "Price List"
		b.buying_price_list = "Bakery Buying"
		b.currency = "USD"
		b.with_operations = 1
		for item in bom.get("items"):
			b.append("items", {**item, "stock_uom": item.get("uom"), "do_not_explode": 1})
		for operation in bom.get("operations"):
			b.append("operations", {**operation})
		b.save()
		b.submit()


suppliers = [
	(
		"Freedom Provisions",
		None,
		None,
		None,
		"Net 30",
		{
			"address_line1": "16 Margrave",
			"city": "Carlisle",
			"state": "NH",
			"country": "United States",
			"pincode": "57173",
		},
	),
	(
		"Unity Bakery Supply",
		None,
		None,
		None,
		"Net 30",
		{
			"address_line1": "34 Pinar St",  # TODO: randomize this address
			"city": "Unity",
			"state": "RI",
			"country": "United States",
			"pincode": "34291",
		},
	),
	(
		"Chelsea Fruit Co",
		None,
		None,
		None,
		"Net 30",
		{
			"address_line1": "67C Sweeny Street",
			"city": "Chelsea",
			"state": "MA",
			"country": "United States",
			"pincode": "89077",
		},
	),
]

workstations = [
	("Mix Pie Crust Station", "20"),
	("Roll Pie Crust Station", "20"),
	("Make Pie Filling Station", "20"),
	("Cooling Station", "100"),
	("Box Pie Station", "100"),
	("Baking Station", "20"),
	("Assemble Pie Station", "20"),
	("Mix Pie Filling Station", "20"),
	("Packaging Station", "2"),
	("Food Prep Table 2", "10"),
	("Food Prep Table 1", "5"),
	("Range Station", "20"),
	("Cooling Racks Station", "80"),
	("Refrigerator Station", "200"),
	("Oven Station", "20"),
	("Mixer Station", "10"),
]

operations = [
	(
		"Gather Pie Crust Ingredients",
		"Food Prep Table 2",
		"5",
		"""- Remove flour, salt, and a pie tins from store room
	- Remove butter and ice water from refrigerator
	- Place ingredients at workstation
	- Measure amounts for batch size into mixing bowl""",
	),
	(
		"Gather Pie Filling Ingredients",
		"Food Prep Table 1",
		"5",
		"""- Remove fruit and butter from refrigerator
	- Remove sugar and cornstarch
	- Get water from sink
	- Measure ingredients and place in pot, excluding 1/4 of fruit and butter""",
	),
	(
		"Assemble Pie Op",
		"Food Prep Table 2",
		"5",
		"""- Use fresh pie filling or remove from refrigerator
	- Remove rolled pie crusts from refrigerator
	- Fill bottom crust with filling
	- Create decorative cut out for top crust
	- Layer top crust over bottom crust / filling and create a crimped seal""",
	),
	(
		"Cook Pie Filling Operation",
		"Range Station",
		"5",
		"""- Bring ingredients to simmer and cook for 15 minutes
	- Remove from heat and mix in remaining 1/4 berries and butter
	- Store in refrigerator if not using immediately""",
	),
	(
		"Mix Pie Crust Op",
		"Mixer Station",
		"5",
		"""- Combine flour, butter, salt, and ice water in mixer
	- Pulse for 30 seconds
	- Divide into equal-sized portions, one portion for each pie crust being made
	- Put in refrigerator""",
	),
	("Box Pie Op", "Packaging Station", "5", "- Place pie into box for sale"),
	(
		"Roll Pie Crust Op",
		"Food Prep Table 2",
		"5",
		"""- Remove chilled pie crust portions from refrigerator
	- Separate each portion into two (one for bottom crust, one for top)
	- Flour board and roll out each portion into a circle
	- Place bottom crust into pie tin, then layer a piece of parchment paper, followed by the top crust""",
	),
	("Divide Dough Op", "Food Prep Table 2", "1", "Divide Dough Op"),
	(
		"Bake Op",
		"Oven Station",
		"1",
		"""- Place assembled pies into oven
	- Bake at 375F for 50 minutes
	- Remove from oven""",
	),
	("Chill Pie Crust Op", "Refrigerator Station", "1", "- Chill pie crust for at least 30 minutes"),
	(
		"Cool Pie Op",
		"Cooling Racks Station",
		"1",
		"Cool baked pies for at least 30 minutes before boxing",
	),
]

items = [
	{
		"item_code": "Ambrosia Pie",
		"item_group": "Sub Assemblies",
		"uom": "Nos",
		"item_price": 10.00,
		"default_warehouse": "Storeroom - APC",
		"description": "<div><p>Ambrosia Pie is the marquee product of Ambrosia Pie Company. A filling of heavenly cloudberries pair perfectly with the tart hairless rambutan, finished with drizzles of tayberry nectar. It's a feast fit for Mt Olympus!</p></div>",
	},
	{
		"item_code": "Double Plum Pie",
		"uom": "Nos",
		"item_group": "Baked Goods",
		"default_warehouse": "Finished Goods - APC",
		"item_price": 9.00,
		"description": "<div><p>Double the fun and double the flavor with our Double Plum Pie! We combine damson and cocoplums in a daring tropical-meets-temperate filling. Forbidden fruit never tasted this good.</p></div>",
	},
	{
		"item_code": "Gooseberry Pie",
		"uom": "Nos",
		"item_group": "Baked Goods",
		"item_price": 12.00,
		"default_warehouse": "Finished Goods - APC",
		"description": "<div><p>Our delicious take on the traditional gooseberry pie that tastes like the holidays. This classic pie is best shared with the ones you love.</p></div>",
	},
	{
		"item_code": "Kaduka Key Lime Pie",
		"item_group": "Baked Goods",
		"uom": "Nos",
		"item_price": 9.00,
		"default_warehouse": "Finished Goods - APC",
		"description": "<div><p>Take your tastebuds on an adventure with this whimsical twist on the classic Key Lime pie. Made with kaduka limes and the exotic limequat, this seasonal pie is sure to satisfy even the most weary culinary explorer. Grab it when you can - it's only available April through September.</p></div>",
	},
	{
		"item_code": "Ambrosia Pie Filling",
		"uom": "Cup",
		"item_group": "Sub Assemblies",
		"default_warehouse": "Refrigerator - APC",
		"description": "Ambrosia Pie Filling",
	},
	{
		"item_code": "Double Plum Pie Filling",
		"uom": "Cup",
		"item_group": "Sub Assemblies",
		"default_warehouse": "Refrigerator - APC",
		"description": "Double Plum Pie Filling",
	},
	{
		"item_code": "Gooseberry Pie Filling",
		"uom": "Cup",
		"description": "Gooseberry Pie Filling",
		"item_group": "Sub Assemblies",
		"default_warehouse": "Refrigerator - APC",
	},
	{
		"item_code": "Kaduka Key Lime Pie Filling",
		"item_group": "Sub Assemblies",
		"default_warehouse": "Refrigerator - APC",
		"uom": "Cup",
		"description": "Kaduka Key Lime Pie Filling",
	},
	{
		"item_code": "Pie Crust",
		"uom": "Nos",
		"description": "Pie Crust",
		"item_group": "Sub Assemblies",
		"default_warehouse": "Refrigerator - APC",
	},
	{
		"item_code": "Cloudberry",
		"uom": "Pound",
		"description": "Our Own Cloudberry",
		"item_group": "Ingredients",
		"item_price": 10.00,
		"default_warehouse": "Refrigerator - APC",
		"supplier": "Chelsea Fruit Co",
	},
	{
		"item_code": "Cocoplum",
		"uom": "Pound",
		"description": "Cocoplum",
		"item_group": "Ingredients",
		"item_price": 5.57,
		"default_warehouse": "Refrigerator - APC",
		"supplier": "Chelsea Fruit Co",
	},
	{
		"item_code": "Damson Plum",
		"uom": "Pound",
		"description": "Damson Plum",
		"item_group": "Ingredients",
		"item_price": 13.30,
		"default_warehouse": "Refrigerator - APC",
		"supplier": "Chelsea Fruit Co",
	},
	{
		"item_code": "Gooseberry",
		"uom": "Pound",
		"description": "Gooseberry",
		"item_group": "Ingredients",
		"item_price": 14.84,
		"default_warehouse": "Refrigerator - APC",
		"supplier": "Chelsea Fruit Co",
	},
	{
		"item_code": "Hairless Rambutan",
		"uom": "Pound",
		"description": "Hairless Rambutan",
		"item_price": 7.64,
		"item_group": "Ingredients",
		"default_warehouse": "Storeroom - APC",
		"supplier": "Chelsea Fruit Co",
	},
	{
		"item_code": "Kakadu Lime",
		"uom": "Pound",
		"description": "Kakadu Lime",
		"item_group": "Ingredients",
		"item_price": 13.38,
		"default_warehouse": "Storeroom - APC",
		"supplier": "Chelsea Fruit Co",
	},
	{
		"item_code": "Limequat",
		"uom": "Pound",
		"description": "Limequat",
		"item_group": "Ingredients",
		"item_price": 11.04,
		"default_warehouse": "Refrigerator - APC",
		"supplier": "Chelsea Fruit Co",
	},
	{
		"item_code": "Tayberry",
		"uom": "Pound",
		"description": "Tayberry - Box",
		"item_group": "Ingredients",
		"item_price": 12.79,
		"default_warehouse": "Refrigerator - APC",
		"supplier": "Chelsea Fruit Co",
	},
	{
		"item_code": "Butter",
		"uom": "Pound",
		"description": "Butter",
		"item_group": "Ingredients",
		"item_price": 4.5,
		"default_warehouse": "Refrigerator - APC",
		"supplier": "Freedom Provisions",
	},
	{
		"item_code": "Cornstarch",
		"uom": "Pound",
		"description": "Cornstarch",
		"item_group": "Ingredients",
		"item_price": 0.52,
		"default_warehouse": "Storeroom - APC",
		"supplier": "Freedom Provisions",
	},
	{
		"item_code": "Ice Water",
		"uom": "Cup",
		"item_price": 0.01,
		"description": "Ice Water - necessary for pie crusts",
		"item_group": "Ingredients",
		"default_warehouse": "Refrigerator - APC",
	},
	{
		"item_code": "Flour",
		"uom": "Pound",
		"description": "Flour",
		"item_group": "Ingredients",
		"item_price": 0.66,
		"default_warehouse": "Storeroom - APC",
		"supplier": "Freedom Provisions",
	},
	{
		"item_code": "Pie Box",
		"uom": "Nos",
		"description": "Pie Box",
		"item_group": "Bakery Supplies",
		"item_price": 0.4,
		"default_warehouse": "Storeroom - APC",
		"supplier": "Unity Bakery Supply",
	},
	{
		"item_code": "Pie Tin",
		"uom": "Nos",
		"description": "Pie Tin",
		"item_price": 0.18,
		"item_group": "Bakery Supplies",
		"default_warehouse": "Storeroom - APC",
		"supplier": "Unity Bakery Supply",
	},
	{
		"item_code": "Parchment Paper",
		"uom": "Nos",
		"description": "Parchment Paper",
		"item_group": "Bakery Supplies",
		"item_price": 0.02,
		"default_warehouse": "Storeroom - APC",
		"supplier": "Unity Bakery Supply",
	},
	{
		"item_code": "Salt",
		"uom": "Pound",
		"description": "Salt",
		"item_group": "Ingredients",
		"item_price": 0.36,
		"default_warehouse": "Storeroom - APC",
		"supplier": "Freedom Provisions",
	},
	{
		"item_code": "Sugar",
		"uom": "Pound",
		"description": "Sugar",
		"item_group": "Ingredients",
		"item_price": 0.60,
		"default_warehouse": "Storeroom - APC",
		"supplier": "Freedom Provisions",
	},
	{
		"item_code": "Water",
		"uom": "Cup",
		"item_price": 0.05,
		"description": "Water",
		"item_group": "Ingredients",
		"default_warehouse": "Kitchen - APC",
	},
]

boms = [
	{
		"item": "Double Plum Pie",
		"quantity": 5.0,
		"uom": "Nos",
		"items": [
			{"item_code": "Pie Crust", "qty": 5.0, "qty_consumed_per_unit": 1.0, "uom": "Nos"},
			{
				"item_code": "Double Plum Pie Filling",
				"qty": 20.0,
				"qty_consumed_per_unit": 4.0,
				"uom": "Cup",
			},
			{"item_code": "Pie Box", "qty": 5.0, "qty_consumed_per_unit": 1.0, "uom": "Nos"},
		],
		"operations": [
			{
				"batch_size": 5,
				"operation": "Assemble Pie Op",
				"time_in_mins": 10.0,
				"workstation": "Food Prep Table 2",
			},
			{"batch_size": 1, "operation": "Bake Op", "time_in_mins": 50.0, "workstation": "Oven Station"},
			{
				"batch_size": 1,
				"operation": "Cool Pie Op",
				"time_in_mins": 30.0,
				"workstation": "Cooling Racks Station",
			},
			{
				"batch_size": 5,
				"operation": "Box Pie Op",
				"time_in_mins": 5.0,
				"workstation": "Packaging Station",
			},
		],
	},
	{
		"item": "Kaduka Key Lime Pie",
		"quantity": 5.0,
		"uom": "Nos",
		"items": [
			{"item_code": "Pie Crust", "qty": 5.0, "qty_consumed_per_unit": 1.0, "uom": "Nos"},
			{
				"item_code": "Kaduka Key Lime Pie Filling",
				"qty": 20.0,
				"qty_consumed_per_unit": 4.0,
				"uom": "Cup",
			},
			{"item_code": "Pie Box", "qty": 5.0, "qty_consumed_per_unit": 1.0, "uom": "Nos"},
		],
		"operations": [
			{
				"batch_size": 5,
				"operation": "Assemble Pie Op",
				"time_in_mins": 10.0,
				"workstation": "Food Prep Table 2",
			},
			{"batch_size": 1, "operation": "Bake Op", "time_in_mins": 50.0, "workstation": "Oven Station"},
			{
				"batch_size": 1,
				"operation": "Cool Pie Op",
				"time_in_mins": 30.0,
				"workstation": "Cooling Racks Station",
			},
			{
				"batch_size": 5,
				"operation": "Box Pie Op",
				"time_in_mins": 5.0,
				"workstation": "Packaging Station",
			},
		],
	},
	{
		"item": "Gooseberry Pie",
		"quantity": 5.0,
		"uom": "Nos",
		"items": [
			{"item_code": "Pie Crust", "qty": 5.0, "qty_consumed_per_unit": 1.0, "uom": "Nos"},
			{
				"item_code": "Gooseberry Pie Filling",
				"qty": 20.0,
				"qty_consumed_per_unit": 4.0,
				"uom": "Cup",
			},
			{"item_code": "Pie Box", "qty": 5.0, "qty_consumed_per_unit": 1.0, "uom": "Nos"},
		],
		"operations": [
			{
				"batch_size": 5,
				"operation": "Assemble Pie Op",
				"time_in_mins": 10.0,
				"workstation": "Food Prep Table 2",
			},
			{"batch_size": 1, "operation": "Bake Op", "time_in_mins": 50.0, "workstation": "Oven Station"},
			{
				"batch_size": 1,
				"operation": "Cool Pie Op",
				"time_in_mins": 30.0,
				"workstation": "Cooling Racks Station",
			},
			{
				"batch_size": 5,
				"operation": "Box Pie Op",
				"time_in_mins": 5.0,
				"workstation": "Packaging Station",
			},
		],
	},
	{
		"item": "Ambrosia Pie",
		"quantity": 5.0,
		"uom": "Nos",
		"items": [
			{"item_code": "Pie Crust", "qty": 5.0, "qty_consumed_per_unit": 1.0, "uom": "Nos"},
			{"item_code": "Ambrosia Pie Filling", "qty": 20.0, "qty_consumed_per_unit": 4.0, "uom": "Cup"},
			{"item_code": "Pie Box", "qty": 5.0, "qty_consumed_per_unit": 1.0, "uom": "Nos"},
		],
		"operations": [
			{
				"batch_size": 5,
				"operation": "Assemble Pie Op",
				"time_in_mins": 10.0,
				"workstation": "Food Prep Table 2",
			},
			{"batch_size": 1, "operation": "Bake Op", "time_in_mins": 50.0, "workstation": "Oven Station"},
			{
				"batch_size": 1,
				"operation": "Cool Pie Op",
				"time_in_mins": 30.0,
				"workstation": "Cooling Racks Station",
			},
			{
				"batch_size": 5,
				"operation": "Box Pie Op",
				"time_in_mins": 5.0,
				"workstation": "Packaging Station",
			},
		],
	},
	{
		"item": "Double Plum Pie Filling",
		"quantity": 20.0,
		"uom": "Cup",
		"items": [
			{"item_code": "Sugar", "qty": 0.5, "qty_consumed_per_unit": 0.025, "uom": "Pound"},
			{"item_code": "Cornstarch", "qty": 0.1, "qty_consumed_per_unit": 0.005, "uom": "Pound"},
			{"item_code": "Water", "qty": 1.25, "qty_consumed_per_unit": 0.0625, "uom": "Cup"},
			{"item_code": "Butter", "qty": 0.313, "qty_consumed_per_unit": 0.01565, "uom": "Pound"},
			{"item_code": "Cocoplum", "qty": 7.5, "qty_consumed_per_unit": 0.02515, "uom": "Pound"},
			{"item_code": "Damson Plum", "qty": 7.5, "qty_consumed_per_unit": 0.02515, "uom": "Pound"},
		],
		"operations": [
			{
				"batch_size": 5,
				"operation": "Gather Pie Filling Ingredients",
				"time_in_mins": 5.0,
				"workstation": "Food Prep Table 1",
			},
			{
				"batch_size": 5,
				"operation": "Cook Pie Filling Operation",
				"time_in_mins": 15.0,
				"workstation": "Range Station",
			},
		],
	},
	{
		"item": "Kaduka Key Lime Pie Filling",
		"quantity": 20.0,
		"uom": "Cup",
		"items": [
			{"item_code": "Sugar", "qty": 0.5, "qty_consumed_per_unit": 0.025, "uom": "Pound"},
			{"item_code": "Cornstarch", "qty": 0.1, "qty_consumed_per_unit": 0.005, "uom": "Pound"},
			{"item_code": "Water", "qty": 1.25, "qty_consumed_per_unit": 0.0625, "uom": "Cup"},
			{"item_code": "Butter", "qty": 0.313, "qty_consumed_per_unit": 0.01565, "uom": "Pound"},
			{"item_code": "Kakadu Lime", "qty": 10.0, "qty_consumed_per_unit": 0.0335, "uom": "Pound"},
			{"item_code": "Limequat", "qty": 5.0, "qty_consumed_per_unit": 0.01675, "uom": "Pound"},
		],
		"operations": [
			{
				"batch_size": 5,
				"operation": "Gather Pie Filling Ingredients",
				"time_in_mins": 5.0,
				"workstation": "Food Prep Table 1",
			},
			{
				"batch_size": 5,
				"operation": "Cook Pie Filling Operation",
				"time_in_mins": 15.0,
				"workstation": "Range Station",
			},
		],
	},
	{
		"item": "Gooseberry Pie Filling",
		"quantity": 20.0,
		"uom": "Cup",
		"items": [
			{"item_code": "Sugar", "qty": 0.5, "qty_consumed_per_unit": 0.025, "uom": "Pound"},
			{"item_code": "Cornstarch", "qty": 0.1, "qty_consumed_per_unit": 0.005, "uom": "Pound"},
			{"item_code": "Water", "qty": 1.25, "qty_consumed_per_unit": 0.0625, "uom": "Cup"},
			{"item_code": "Butter", "qty": 0.313, "qty_consumed_per_unit": 0.01565, "uom": "Pound"},
			{"item_code": "Gooseberry", "qty": 15.0, "qty_consumed_per_unit": 0.05025, "uom": "Pound"},
		],
		"operations": [
			{
				"batch_size": 5,
				"operation": "Gather Pie Filling Ingredients",
				"time_in_mins": 5.0,
				"workstation": "Food Prep Table 1",
			},
			{
				"batch_size": 5,
				"operation": "Cook Pie Filling Operation",
				"time_in_mins": 15.0,
				"workstation": "Range Station",
			},
		],
	},
	{
		"item": "Ambrosia Pie Filling",
		"quantity": 20.0,
		"uom": "Cup",
		"items": [
			{"item_code": "Sugar", "qty": 0.5, "qty_consumed_per_unit": 0.025, "uom": "Pound"},
			{"item_code": "Cornstarch", "qty": 0.1, "qty_consumed_per_unit": 0.005, "uom": "Pound"},
			{"item_code": "Butter", "qty": 0.313, "qty_consumed_per_unit": 0.01565, "uom": "Pound"},
			{
				"item_code": "Hairless Rambutan",
				"qty": 5.0,
				"qty_consumed_per_unit": 0.01675,
				"uom": "Pound",
			},
			{"item_code": "Tayberry", "qty": 2.5, "qty_consumed_per_unit": 0.0084, "uom": "Pound"},
			{"item_code": "Cloudberry", "qty": 7.5, "qty_consumed_per_unit": 0.02515, "uom": "Pound"},
			{"item_code": "Water", "qty": 1.25, "qty_consumed_per_unit": 0.0625, "uom": "Cup"},
		],
		"operations": [
			{
				"batch_size": 5,
				"operation": "Gather Pie Filling Ingredients",
				"time_in_mins": 5.0,
				"workstation": "Food Prep Table 1",
			},
			{
				"batch_size": 5,
				"operation": "Cook Pie Filling Operation",
				"time_in_mins": 15.0,
				"workstation": "Range Station",
			},
		],
	},
	{
		"item": "Pie Crust",
		"quantity": 5.0,
		"uom": "Nos",
		"items": [
			{"item_code": "Flour", "qty": 3.75, "qty_consumed_per_unit": 0.75, "uom": "Pound"},
			{"item_code": "Butter", "qty": 2.5, "qty_consumed_per_unit": 0.5, "uom": "Pound"},
			{"item_code": "Ice Water", "qty": 2.5, "qty_consumed_per_unit": 0.5, "uom": "Cup"},
			{"item_code": "Salt", "qty": 0.05, "qty_consumed_per_unit": 0.01, "uom": "Pound"},
			{"item_code": "Parchment Paper", "qty": 5.0, "qty_consumed_per_unit": 1.0, "uom": "Nos"},
			{"item_code": "Flour", "qty": 0.5, "qty_consumed_per_unit": 0.1, "uom": "Pound"},
			{"item_code": "Pie Tin", "qty": 5.0, "qty_consumed_per_unit": 1.0, "uom": "Nos"},
		],
		"operations": [
			{
				"batch_size": 5,
				"operation": "Gather Pie Crust Ingredients",
				"time_in_mins": 5.0,
				"workstation": "Food Prep Table 2",
			},
			{
				"batch_size": 5,
				"operation": "Mix Pie Crust Op",
				"time_in_mins": 5.0,
				"workstation": "Mixer Station",
			},
			{
				"batch_size": 1,
				"operation": "Divide Dough Op",
				"time_in_mins": 10.0,
				"workstation": "Food Prep Table 2",
			},
			{
				"batch_size": 1,
				"operation": "Chill Pie Crust Op",
				"time_in_mins": 30.0,
				"workstation": "Refrigerator Station",
			},
			{
				"batch_size": 5,
				"operation": "Roll Pie Crust Op",
				"time_in_mins": 30.0,
				"workstation": "Food Prep Table 2",
			},
		],
	},
]
