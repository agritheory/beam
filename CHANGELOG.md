# CHANGELOG



## v14.3.1 (2023-08-22)

### Chore

* chore: update test date for erpnext codebase changes ([`986e218`](https://github.com/agritheory/beam/commit/986e218aafbe9707c368f61ba072f84ab49d2e35))

### Ci

* ci: remove testing artifacts ([`900c33e`](https://github.com/agritheory/beam/commit/900c33e8c234b1433d791f444eecad1039ef62f8))

* ci: fix db logger for tests to run ([`89e5213`](https://github.com/agritheory/beam/commit/89e521308538aa3440c19aece12cafb9942351ec))

* ci: add pytest to dependencies ([`6312732`](https://github.com/agritheory/beam/commit/6312732e2c6d906381d152cfa02e4084f395c9bc))

* ci: add echos for version ([`25b39be`](https://github.com/agritheory/beam/commit/25b39be42b3fc5aabdacf6d58dee4b593e28f842))

* ci: test setup tweaks ([`37d3f39`](https://github.com/agritheory/beam/commit/37d3f3907317dbba32491d8972052d2b60de0a6b))

* ci: add pytest files ([`6e0d750`](https://github.com/agritheory/beam/commit/6e0d7504dfa4d816eb857a6fbe446cf4a95bd7b7))

* ci: migrate to python semantic release ([`f5fc8e9`](https://github.com/agritheory/beam/commit/f5fc8e9dba79ac0374694317f0cca5f0ec4b97ba))

### Fix

* fix: update overconsumption logic to be sensitive to inbound/ outbound transfers ([`8ea7b2a`](https://github.com/agritheory/beam/commit/8ea7b2a12c40ff7002b330a2a3f83788c5632852))

* fix: update overconsumption validation ([`f6d69c0`](https://github.com/agritheory/beam/commit/f6d69c0ad08f9743f6b3dcee0c35f43e56bed846))

### Unknown

* Merge pull request #56 from agritheory/fix_overconsumption

Fix overconsumption ([`1ff8d27`](https://github.com/agritheory/beam/commit/1ff8d27a7d22c7e17266abd9838b9647a7e3f502))

* Merge branch &#39;version-14&#39; into fix_overconsumption ([`fa586bd`](https://github.com/agritheory/beam/commit/fa586bd57027146968575bf25a95ed7352451aff))

* Merge pull request #55 from agritheory/py_sem_rel_14

ci: add test workflow, migrate to Python semantic release ([`52ed795`](https://github.com/agritheory/beam/commit/52ed795190ace79dee7e777f805025e1e8e50180))

* Merge pull request #54 from agritheory/test_data_fixes

chore: update test date for erpnext codebase changes ([`a5a7ede`](https://github.com/agritheory/beam/commit/a5a7ede47b63b19d5d36732337562dc488b1f2b7))


## v14.3.0 (2023-07-21)

### Documentation

* docs: move warehouse section, fix formatting and spelling ([`058ccba`](https://github.com/agritheory/beam/commit/058ccba8484caf8510274372d25c972840b013ef))

### Feature

* feat: rename function, add purchase return case ([`fbad47a`](https://github.com/agritheory/beam/commit/fbad47ab8dc6d724835bea2910489cb79dee92cd))

### Fix

* fix: wip use stock_qty and precision ([`d0799d5`](https://github.com/agritheory/beam/commit/d0799d5d5693a29c129619b46c76dae593461e46))

### Unknown

* Merge pull request #48 from agritheory/issue_42

Add validation to disallow overconsumption of qty in a handling unit ([`2130039`](https://github.com/agritheory/beam/commit/213003960382af4e7ffc980bc188db58db680755))

* Merge pull request #46 from agritheory/docs

docs: document features - first pass ([`fb5b7ac`](https://github.com/agritheory/beam/commit/fb5b7ac0a2cd270fedad2e6b52c4d45127d9ee35))


## v14.2.0 (2023-07-18)

### Documentation

* docs: add screen shots, update text ([`e032b11`](https://github.com/agritheory/beam/commit/e032b111bb5d1598fd97b7446c04fcece803c203))

* docs: text edits, add detail, link text more accessible ([`6c6f380`](https://github.com/agritheory/beam/commit/6c6f38072949c78b5a2749958ccf8d37628bf9b8))

### Feature

* feat: Validate handling unit overconsumption ([`bf34994`](https://github.com/agritheory/beam/commit/bf349947a39954388e2f513d898ef07dc58776a5))

* feat: update listview action ([`549810a`](https://github.com/agritheory/beam/commit/549810a74eb16ca97dd7ed941b194fef75a09729))

### Unknown

* Merge pull request #47 from agritheory/issue_41

Scanning Handling Unit in Listview should filter instead of route ([`2869963`](https://github.com/agritheory/beam/commit/286996364eed49542e2bc37aea6ca3770479854f))


## v14.1.3 (2023-07-12)

### Documentation

* docs: document features - first pass ([`960bf17`](https://github.com/agritheory/beam/commit/960bf1782d5a0afb6592eac7f152669c728c180b))

### Fix

* fix: ignore permissions on barcode creation ([`57586ed`](https://github.com/agritheory/beam/commit/57586ed95a32071471a7ba18aebd77a19372064b))

### Unknown

* Merge pull request #45 from agritheory/permissions_fix

fix: ignore permissions on barcode creation ([`57ce99d`](https://github.com/agritheory/beam/commit/57ce99da3a1fc18409944131a0b6aec28418d879))

* wip: more documentation and stubs ([`0834808`](https://github.com/agritheory/beam/commit/083480843fa639714b8ffb5fb115e96d97beb7f5))


## v14.1.2 (2023-07-11)

### Fix

* fix: net HU quantities in send to subcontractor should generate a new HU for the amount sent (#40) ([`5ee3c96`](https://github.com/agritheory/beam/commit/5ee3c965689d20eecafa7dde4146e45fc9317096))

### Unknown

* Generate matrix (#39)

* feat/docs: automated documentation of decision matrix

* ci: call generate matrix in CI ([`d3edd62`](https://github.com/agritheory/beam/commit/d3edd6242291087a9d92115197989f02ffbc1332))

* Refactor frappe.db.sql calls to query builder (#35)

* feat: Refactor frappe.db.sql calls to query builder

* feat: added missing return

* Multiple UOMs (#31)

* wip/test: scan tests

* tests: more compelte tests

* docs: handling unit

* wip: refactor to inventory dimension

* wip: refactor to inventory dimensions

* wip/test: scan tests

* test: test manufacture stock entry

* tests: more complete tests

* wip/test: scan tests

* fix: remove merge conflict

* test: add delivery note and sales invoice tests

* feat: integrate warranty calim and putaway rule

* feat: quality inspection

* test: add test for packing slip

* wip: get non-stock uom from source document

* fix: get_handling_unit

* fix: actual_qty renamed as stock_qty in handling_unit()

* fix: actual_qty renamed as stock_qty in handling_unit()

* feat: minor improvement

* fix: trailing comma, pre-commit

* fix: test, delete unused code

* feat: get_handling_unit should calculate stock_qty instead of qty

* fix: pop

---------

Co-authored-by: Francisco Roldán &lt;franciscoproldan@gmail.com&gt;

* chore: remove purchase invoice item customization

---------

Co-authored-by: Tyler Matteson &lt;tyler@agritheory.com&gt; ([`0e98e9d`](https://github.com/agritheory/beam/commit/0e98e9dd4546c2aff58d72058594a69f33728571))

* Multiple UOMs (#31)

* wip/test: scan tests

* tests: more compelte tests

* docs: handling unit

* wip: refactor to inventory dimension

* wip: refactor to inventory dimensions

* wip/test: scan tests

* test: test manufacture stock entry

* tests: more complete tests

* wip/test: scan tests

* fix: remove merge conflict

* test: add delivery note and sales invoice tests

* feat: integrate warranty calim and putaway rule

* feat: quality inspection

* test: add test for packing slip

* wip: get non-stock uom from source document

* fix: get_handling_unit

* fix: actual_qty renamed as stock_qty in handling_unit()

* fix: actual_qty renamed as stock_qty in handling_unit()

* feat: minor improvement

* fix: trailing comma, pre-commit

* fix: test, delete unused code

* feat: get_handling_unit should calculate stock_qty instead of qty

* fix: pop

---------

Co-authored-by: Francisco Roldán &lt;franciscoproldan@gmail.com&gt; ([`e39b2b1`](https://github.com/agritheory/beam/commit/e39b2b1bac1cb194a7dba850a0be456626a649ef))

* Make action configuration hookable (#33)

* wip: hooks override working

monkeypatch in test is not working correctly, needs docs

* docs: add hooks documentation

* feat/tests: override server side hooks for beam actions

* feat: move config object out of function, deserialize targets

* feat: custom client callbacks

* fix: docs, remove testing code ([`38c5aff`](https://github.com/agritheory/beam/commit/38c5aff7c99af0ac54f1a8aa6fb3b314f86c8765))

* Inventory dimension (#28)

* wip/test: scan tests

* tests: more compelte tests

* docs: handling unit

* wip: refactor to inventory dimension

* wip: refactor to inventory dimensions

* wip/test: scan tests

* test: test manufacture stock entry

* tests: more complete tests

* wip/test: scan tests

* fix: remove merge conflict

* test: add delivery note and sales invoice tests

* feat: integrate warranty calim and putaway rule

* feat: quality inspection

* test: add test for packing slip ([`1042dea`](https://github.com/agritheory/beam/commit/1042dea57148f6dba2025a5bb9075aa65bf6cb27))

* Draft: Print server integration (#14)

* feat: add print_server integration

* fix: remove bad default  in dialog

* feat: handle scanning of non-handling units

* fix: convert tuple to dict

* ci: fix json diff job

* fix: add stub for Stock Entry-Item barcode scans

* fix: setup stock entry scanning

* fix: set basic rate for item in Stock Entry

* fix: remove reference to client code

* fix: normalize return values for scanning

---------

Co-authored-by: Rohan Bansal &lt;rohan@parsimony.com&gt; ([`2323b82`](https://github.com/agritheory/beam/commit/2323b825d7e7e94d72be868861bc7d6c6e2b1910))


## v14.1.1 (2023-06-23)

### Fix

* fix: normalize return values for scanning ([`6ba7e00`](https://github.com/agritheory/beam/commit/6ba7e0063a25188eab86a79ddf6a57aa8d33366c))

### Unknown

* Merge pull request #27 from agritheory/fix-scan-return-value

fix: normalize return values for scanning ([`24adda3`](https://github.com/agritheory/beam/commit/24adda3830e21419c989dd4c382c8a87ecddde93))


## v14.1.0 (2023-06-15)

### Ci

* ci: fix json diff job ([`54f6766`](https://github.com/agritheory/beam/commit/54f6766ca9d7c6f42bac78573896370b70ff47b6))

### Documentation

* docs: fix readme ([`999eb22`](https://github.com/agritheory/beam/commit/999eb22d4927ff706eb2c44f8117ac10826b0401))

### Feature

* feat: handle scanning of non-handling units ([`048aee3`](https://github.com/agritheory/beam/commit/048aee35b9c28805ce06abb72f1c8a16f0a0e3b1))

### Fix

* fix: remove reference to client code ([`ef74169`](https://github.com/agritheory/beam/commit/ef741698a78fd989332e9e6867600898cccd42ec))

* fix: set basic rate for item in Stock Entry ([`36d5381`](https://github.com/agritheory/beam/commit/36d5381b5a520badd615893892910c88d022e64e))

* fix: setup stock entry scanning ([`56b089a`](https://github.com/agritheory/beam/commit/56b089ab7988ad89753cfc6475d42e61cd9a2b92))

* fix: add stub for Stock Entry-Item barcode scans ([`5468600`](https://github.com/agritheory/beam/commit/54686005ef8d962f45704289b565f750cbf8ebd9))

* fix: convert tuple to dict ([`62179a4`](https://github.com/agritheory/beam/commit/62179a4949354b3db82c0182d84219965b65239d))

### Unknown

* Merge pull request #18 from agritheory/fix-non-handling-unit-scan

feat: handle scanning of non-handling units ([`db158dc`](https://github.com/agritheory/beam/commit/db158dccd3cc19d61c17ae0669ec99152a8ff411))

* Merge pull request #11 from agritheory/fix_readme

docs: fix readme ([`087158b`](https://github.com/agritheory/beam/commit/087158bd68c0a9a608ffd8bf225616e12c106502))


## v14.0.1 (2023-05-27)

### Ci

* ci: fix some mypy errors ([`a6e0361`](https://github.com/agritheory/beam/commit/a6e0361326fc03515e8cbdc0606f3679401299c0))

### Fix

* fix: fix mypy errors and doc testing documentation ([`4bd8267`](https://github.com/agritheory/beam/commit/4bd8267942d1d39c9b9590dd26f158a13dee6fc5))

* fix: stock entry override ([`3209684`](https://github.com/agritheory/beam/commit/3209684ad2cd3bad9a55edb349e7cf677ab132a4))

* fix: simplify get_handling_unit ([`d393654`](https://github.com/agritheory/beam/commit/d3936547dd42a760807d4674f1e4a94845391ca1))

* fix: restructure form and list decision matrix ([`44e15df`](https://github.com/agritheory/beam/commit/44e15dfb2c2ca1086637c8429846f4bb47706a01))

* fix: remove Asset scanning features ([`24f0fdb`](https://github.com/agritheory/beam/commit/24f0fdbb610dde45677bd6c30b58911dc6a9816b))

* fix: remove Job Card APIs ([`cd0864f`](https://github.com/agritheory/beam/commit/cd0864fbf8ce5c235b3b4e323479ff0e5e301289))

* fix: typing syntax for py3.8 ([`d62974d`](https://github.com/agritheory/beam/commit/d62974df174df4aede2c7a03cf0e72391526c806))

* fix: sle query ([`7f53c0e`](https://github.com/agritheory/beam/commit/7f53c0ea72976d4bf8c3738b49b196ea88a26a14))

* fix: sle query ([`ea7f3c4`](https://github.com/agritheory/beam/commit/ea7f3c43a1404bfe3ba1c7894a190c53ffc87ab9))

### Style

* style: add typing ([`aadc989`](https://github.com/agritheory/beam/commit/aadc98943f86fb3c7e8ed3d72e0de3df931708ba))

* style: black formatting ([`32a8cfa`](https://github.com/agritheory/beam/commit/32a8cfa38e672b31b2a22ddd302fb9967f2dd141))

### Unknown

* Merge pull request #3 from agritheory/v14_update

V14 update ([`d2480f4`](https://github.com/agritheory/beam/commit/d2480f4463614741a068f5290374553bedb6447c))

* cust: remove asset customization file ([`69947e0`](https://github.com/agritheory/beam/commit/69947e04965b2387e82edff26b0ac36857f7072b))

* cust: add customize file ([`f12faa7`](https://github.com/agritheory/beam/commit/f12faa742c56711f0271793e4b799c46a41a1123))

* tests: separate fixtures into a separate file, make compatibale with production plan ([`ca67807`](https://github.com/agritheory/beam/commit/ca67807f9d62fcfc77164041015aacc7c9b3e5c1))

* wip: test fixtures ([`7b3c865`](https://github.com/agritheory/beam/commit/7b3c865748bfb8ddb4f85786ba8ab5f22320994c))


## v14.0.0 (2023-05-19)

### Feature

* feat: Initialize App ([`40674e1`](https://github.com/agritheory/beam/commit/40674e1f3e4296f2dcc702eeecef92c6b6db7d42))

### Unknown

* wip: test fixtures and port basic functionality ([`5c0824a`](https://github.com/agritheory/beam/commit/5c0824af9950473588f2f82bd9daa2fb4237e01d))
