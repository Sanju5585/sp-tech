"""
Management command: populate_sample_data
Run: python manage.py populate_sample_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.utils import timezone

from products.models import ProductCategory, Product, ProductFeature
from blog.models import Tag, Post


PRODUCTS = [
    {
        'name': 'SanjivaniOne ERP',
        'slug': 'sanjivanione-erp',
        'tagline': 'The complete ERP for growing companies—finance, inventory, HR, sales, and operations in one system.',
        'short_description': (
            'SanjivaniOne ERP is the flagship product of SP-Tech Software Solution. '
            'Run accounts, stock, purchases, sales, payroll, and reporting from a single platform.'
        ),
        'full_description': (
            'SanjivaniOne ERP is the main product of SP-Tech Software Solution—a unified '
            'enterprise platform built for Indian SMBs that want one system instead of '
            'scattered spreadsheets and disconnected tools.\n\n'
            'Finance, inventory, purchasing, sales, invoicing, HR, and payroll sit on '
            'the same data so every team works from a live picture of the business. '
            'GST-ready books, role-based access, and AI-assisted workflows help you '
            'close the books faster, keep stock accurate, and grow without adding '
            'headcount to chase reports.\n\n'
            'Specialised SP-Tech tools for logistics, quoting, and attendance plug into '
            'the same ecosystem when you need extra depth—while SanjivaniOne ERP remains '
            'the system of record.'
        ),
        'icon_class': 'bi-building-gear',
        'is_featured': True,
        'order': 0,
        'meta_title': 'SanjivaniOne ERP – Flagship ERP | SP-Tech Software Solution',
        'meta_description': (
            'SanjivaniOne ERP is the flagship product of SP-Tech Software Solution: '
            'finance, inventory, HR, sales, and operations in one GST-ready platform.'
        ),
        'meta_keywords': (
            'SanjivaniOne ERP, SP-Tech Software Solution, ERP software India, '
            'SMB ERP, GST ERP, inventory accounting HR'
        ),
        'features': [
            ('Unified Finance & GST', 'Ledgers, invoices, bank reconciliation, and GST-ready reports in one books of record.', 'bi-calculator'),
            ('Inventory & Purchasing', 'Stock, warehouses, purchase orders, and supplier bills stay in sync with sales.', 'bi-boxes'),
            ('Sales to Cash', 'Quotes, orders, GST invoices, and receivables in a single customer timeline.', 'bi-graph-up-arrow'),
            ('HR & Payroll', 'Attendance, salaries, PF/ESI, and payslips connected to the same employee master.', 'bi-people'),
            ('Live Business Dashboards', 'Profit, stock, collections, and team KPIs without exporting to Excel.', 'bi-bar-chart-fill'),
            ('Role-Based Access', 'Owners, accountants, store, and HR see only what they need—secure and auditable.', 'bi-shield-lock-fill'),
        ],
    },
    {
        'name': 'Logistics Management System',
        'slug': 'logistics-management-software',
        'tagline': 'End-to-end freight tracking, route optimisation, and warehouse management in one platform.',
        'short_description': (
            'Gain complete visibility over your supply chain with real-time shipment '
            'tracking, intelligent route planning, and integrated warehouse management.'
        ),
        'full_description': (
            'SP-Tech Software Solution Logistics Management System (LMS) is a comprehensive platform '
            'designed for logistics companies, 3PLs, and manufacturers who need full '
            'visibility over their supply chain operations.\n\n'
            'From the moment an order is placed to the final delivery confirmation, '
            'our LMS tracks every step, automates manual workflows, and surfaces '
            'actionable insights so you can optimise costs and delight customers.\n\n'
            'With dedicated mobile apps for drivers and warehouse staff, integration '
            'APIs for ERPs, and a powerful analytics dashboard, LMS puts your '
            'operations on auto-pilot.'
        ),
        'icon_class': 'bi-truck',
        'is_featured': False,
        'order': 1,
        'meta_title': 'Logistics Management System – SP-Tech Software Solution | Real-time Freight Tracking Software',
        'meta_description': (
            'SP-Tech Software Solution LMS delivers real-time shipment tracking, route optimisation, '
            'and warehouse management. Reduce costs by 30% and improve on-time delivery rates.'
        ),
        'meta_keywords': 'logistics management system, freight tracking software, warehouse management India',
        'features': [
            ('Real-time Shipment Tracking', 'Track every consignment from pickup to delivery with live GPS updates and automated customer notifications.', 'bi-geo-alt-fill'),
            ('Fleet & Driver Management', 'Manage your entire fleet, assign drivers, monitor vehicle health, and reduce idle time with smart scheduling.', 'bi-truck-front-fill'),
            ('Warehouse Inventory Control', 'Barcode/RFID-based stock management with bin-level tracking, cycle counting, and automatic replenishment alerts.', 'bi-boxes'),
            ('Route Optimisation', 'AI-powered route planning saves fuel costs by up to 25% and ensures timely deliveries even with last-minute changes.', 'bi-signpost-2-fill'),
            ('E-POD & Digital Documentation', 'Capture proof of delivery, e-signatures, and photos digitally—eliminate paper and disputes.', 'bi-clipboard-check-fill'),
            ('Custom Analytics Dashboard', 'Live KPI dashboards with drill-down reports on delivery performance, fleet utilisation, and cost per km.', 'bi-bar-chart-fill'),
        ],
    },
    {
        'name': 'Quote & Sales Management System',
        'slug': 'quote-sales-management-software',
        'tagline': 'Generate professional quotes, manage leads, and close deals 3× faster.',
        'short_description': (
            'Automate your entire sales cycle—from lead capture to signed quotation—'
            'with a CRM and quoting engine built for B2B teams.'
        ),
        'full_description': (
            'SP-Tech Software Solution Quote & Sales Management System (QSMS) eliminates the '
            'frustration of manually building quotes in Excel and chasing approvals '
            'over email.\n\n'
            'Your sales team gets a professional branded quoting engine, a built-in '
            'CRM pipeline, automated follow-up sequences, and one-click conversion '
            'to purchase order—all in a single web and mobile application.\n\n'
            'Finance gets accurate revenue forecasts. Management gets pipeline '
            'visibility. Customers get polished, GST-compliant proposals in minutes.'
        ),
        'icon_class': 'bi-graph-up-arrow',
        'is_featured': False,
        'order': 2,
        'meta_title': 'Quote & Sales Management System – SP-Tech Software Solution | B2B CRM & Quoting Software',
        'meta_description': (
            'SP-Tech Software Solution QSMS helps sales teams generate GST-compliant quotes, manage '
            'CRM pipelines, and automate follow-ups. Close deals 3× faster.'
        ),
        'meta_keywords': 'quote management software, sales CRM India, quotation software, B2B sales tool',
        'features': [
            ('One-Click Quote Generation', 'Build professional, branded quotations with line items, taxes, and discounts in under 60 seconds.', 'bi-file-earmark-text-fill'),
            ('CRM & Pipeline Management', 'Track leads, opportunities, and deal stages visually. Never let a hot prospect go cold.', 'bi-funnel-fill'),
            ('Email Automation', 'Schedule follow-up emails, payment reminders, and renewal notices automatically based on deal stage.', 'bi-envelope-check-fill'),
            ('GST & Multi-currency Support', 'Auto-calculate GST, IGST, CGST with built-in tax rules. Supports INR and foreign currencies.', 'bi-currency-rupee'),
            ('Digital Signature & e-Approval', 'Clients can review and digitally approve quotations from any device—no printing required.', 'bi-pen-fill'),
            ('Revenue Forecasting', 'Real-time sales forecasts based on pipeline value and close probability to guide planning.', 'bi-graph-up'),
        ],
    },
    {
        'name': 'Invoice Generator',
        'slug': 'invoice-generator-software',
        'tagline': 'Create GST-compliant invoices in seconds. Track payments. Get paid faster.',
        'short_description': (
            'Professional invoice creation, payment tracking, and automated reminders—'
            'designed for SMEs and freelancers operating in India.'
        ),
        'full_description': (
            'Stop wasting hours on invoicing. SP-Tech Software Solution Invoice Generator lets you '
            'create beautiful, GST-compliant invoices in under a minute, send them by '
            'email or WhatsApp, and track payment status in real time.\n\n'
            'Stay compliant with GST regulations without any extra effort—generate '
            'professional invoices, validate GSTIN, and keep your books tidy.'
        ),
        'icon_class': 'bi-receipt',
        'is_featured': False,
        'order': 3,
        'meta_title': 'GST Invoice Generator Software – SP-Tech Software Solution | Billing Made Simple',
        'meta_description': (
            'Generate GST-compliant invoices instantly. Track payments and send '
            'automated reminders with SP-Tech Software Solution Invoice Generator.'
        ),
        'meta_keywords': 'GST invoice software, billing software SME, invoice generator India',
        'features': [
            ('GST Compliant Invoicing', 'Full GST compliance with GSTIN validation and auto-calculated CGST, SGST, and IGST.', 'bi-check-circle-fill'),
            ('PDF Export & Email Delivery', 'Download invoices as polished PDFs or send them directly from the app via email or WhatsApp.', 'bi-file-pdf-fill'),
            ('Payment Tracking', 'Mark invoices as paid/partially paid, record payment methods, and view outstanding receivables at a glance.', 'bi-cash-stack'),
            ('Automated Reminders', 'Schedule payment reminders via email at due date, 3 days before, and 7 days after to reduce late payments.', 'bi-bell-fill'),
        ],
    },
    {
        'name': 'Accounting Software',
        'slug': 'accounting-software',
        'tagline': 'Complete books, ledgers, and financial reports—built for Indian SMEs.',
        'short_description': (
            'Manage ledgers, journals, bank reconciliation, and GST-ready financial '
            'reports from a single, easy-to-use accounting platform.'
        ),
        'full_description': (
            'SP-Tech Software Solution Accounting Software gives growing businesses a clear view of '
            'their finances without the complexity of traditional ERP systems.\n\n'
            'Record day-to-day transactions, maintain ledgers and journals, reconcile '
            'bank accounts, and generate profit & loss, balance sheet, and trial balance '
            'reports in minutes. Designed for Indian GST workflows, it keeps your '
            'accounts accurate and audit-ready.'
        ),
        'icon_class': 'bi-calculator',
        'is_featured': False,
        'order': 4,
        'meta_title': 'Accounting Software for SMEs – SP-Tech Software Solution | GST-Ready Books',
        'meta_description': (
            'SP-Tech Software Solution Accounting Software: ledgers, bank reconciliation, and '
            'GST-ready financial reports for Indian businesses.'
        ),
        'meta_keywords': 'accounting software India, SME accounting, GST accounting software',
        'features': [
            ('Ledgers & Journals', 'Maintain general ledger, cash book, and journal entries with automatic double-entry balancing.', 'bi-journal-text'),
            ('Bank Reconciliation', 'Import statements and match transactions quickly to keep your books in sync with the bank.', 'bi-bank2'),
            ('Financial Reports', 'One-click Profit & Loss, Balance Sheet, Trial Balance, and cash-flow summaries.', 'bi-file-earmark-bar-graph-fill'),
            ('GST-Ready Books', 'Track input/output tax and generate reports that align with your GST filing process.', 'bi-receipt-cutoff'),
        ],
    },
    {
        'name': 'Payroll Management System',
        'slug': 'payroll-management-system',
        'tagline': 'Automate salary processing, statutory compliance, and payslips for your team.',
        'short_description': (
            'Run payroll with confidence—salary calculation, PF/ESI compliance, '
            'payslips, and direct bank transfers in one system.'
        ),
        'full_description': (
            'SP-Tech Software Solution Payroll Management System takes the stress out of monthly '
            'payroll for growing teams.\n\n'
            'Configure salary structures, process attendance-linked pay, handle PF, ESI, '
            'and professional tax, and generate payslips and bank transfer files in a '
            'few clicks. Integrates with attendance data so you pay accurately every month.'
        ),
        'icon_class': 'bi-cash-coin',
        'is_featured': False,
        'order': 5,
        'meta_title': 'Payroll Management System – SP-Tech Software Solution | Salary & Compliance',
        'meta_description': (
            'Automate salary processing, PF/ESI compliance, and payslips with '
            'SP-Tech Software Solution Payroll Management System for Indian SMEs.'
        ),
        'meta_keywords': 'payroll management system India, salary software, PF ESI payroll',
        'features': [
            ('Salary Processing', 'Flexible salary structures with allowances, deductions, and attendance-based calculations.', 'bi-wallet-fill'),
            ('Statutory Compliance', 'Built-in PF, ESI, and professional tax calculations aligned with Indian regulations.', 'bi-shield-check'),
            ('Payslips & Reports', 'Generate employee payslips and payroll summaries for finance and HR in one click.', 'bi-file-earmark-person-fill'),
            ('Bank Transfer Ready', 'Export salary disbursement files compatible with major banks for faster payouts.', 'bi-bank'),
        ],
    },
    {
        'name': 'HR Attendance Manager',
        'slug': 'hr-attendance-manager',
        'tagline': 'Biometric-ready attendance tracking and leave management for growing teams.',
        'short_description': (
            'Automate employee attendance, manage leave requests, and export payroll '
            'data—all from a single, mobile-friendly platform.'
        ),
        'full_description': (
            'SP-Tech Software Solution HR Attendance Manager integrates with biometric devices '
            'and RFID readers to capture accurate clock-in/out data, manage complex '
            'shift schedules, and process leave requests through a streamlined '
            'approval workflow.\n\n'
            'Export payroll-ready reports in CSV format compatible with Tally, '
            'SAP, and other payroll systems—eliminating manual data entry every month.'
        ),
        'icon_class': 'bi-people',
        'is_featured': False,
        'order': 6,
        'meta_title': 'HR Attendance Management Software – SP-Tech Software Solution | Biometric Integration',
        'meta_description': (
            'SP-Tech Software Solution HR Attendance Manager integrates with biometric systems, '
            'manages leave approvals, and exports payroll data for SMEs.'
        ),
        'meta_keywords': 'HR attendance software India, biometric attendance management, leave management system',
        'features': [
            ('Biometric / RFID Integration', 'Compatible with all major biometric brands. Auto-sync clock-in/out data with zero manual entry.', 'bi-fingerprint'),
            ('Leave & Holiday Calendar', 'Configurable holiday lists, comp-off tracking, and multi-level leave approval workflows.', 'bi-calendar-event-fill'),
            ('Payroll CSV Export', 'One-click export of attendance summaries in Tally, SAP, and custom payroll formats.', 'bi-file-earmark-spreadsheet-fill'),
        ],
    },
    {
        'name': 'Expense Tracker',
        'slug': 'expense-tracker-software',
        'tagline': 'Capture, categorise, and report business expenses in real time.',
        'short_description': (
            'Mobile-first expense management with receipt scanning, multi-level '
            'approvals, and budget vs. actual reporting for finance teams.'
        ),
        'full_description': (
            'SP-Tech Software Solution Expense Tracker gives employees a simple mobile app to '
            'snap receipts, categorise spend, and submit claims—while giving finance '
            'teams full visibility, policy controls, and automated reimbursement exports.\n\n'
            'Say goodbye to crumpled paper receipts and month-end spreadsheet chaos.'
        ),
        'icon_class': 'bi-wallet2',
        'is_featured': False,
        'order': 7,
        'meta_title': 'Business Expense Tracker Software – SP-Tech Software Solution | Receipt Scanning & Approval',
        'meta_description': (
            'SP-Tech Software Solution Expense Tracker: mobile receipt scanning, multi-level approval workflows, '
            'and budget vs. actual reports for Indian businesses.'
        ),
        'meta_keywords': 'expense management software India, receipt scanner app, business expense tracker',
        'features': [
            ('Receipt Scanning & OCR', 'Snap a photo of any receipt and our OCR auto-fills vendor, amount, and date.', 'bi-camera-fill'),
            ('Multi-level Approval Workflow', 'Configure up to 4 approval levels with automatic escalations and email notifications.', 'bi-diagram-3-fill'),
            ('Budget vs. Actual Reports', 'Set department and project budgets; get real-time alerts when spend crosses thresholds.', 'bi-pie-chart-fill'),
        ],
    },
]


BLOG_POSTS = [
    {
        'title': 'How Business Automation Helps SMBs Grow Faster',
        'slug': 'business-automation-for-smb-growth',
        'excerpt': (
            'Discover how automating logistics, sales, and finance frees your team '
            'to focus on revenue—and why SMBs cannot afford to wait.'
        ),
        'content': (
            'Small and medium businesses often run on spreadsheets, phone calls, and '
            'outdated desktop software. That may work at a small scale—but it quickly '
            'becomes a bottleneck.\n\n'
            'Business automation replaces repetitive work with reliable systems: '
            'shipment tracking updates itself, quotes generate in minutes, and invoices '
            'go out on time. The result is fewer errors, faster turnaround, and more '
            'time for selling and serving customers.\n\n'
            'Start with one high-pain process—logistics, sales, or accounting—and expand. '
            'Modern cloud tools from SP-Tech Software Solution are built for SMBs that want growth '
            'without enterprise complexity.'
        ),
        'tags': ['business-automation', 'smb'],
        'meta_title': 'Business Automation for SMB Growth | SP-Tech Software Solution',
        'meta_description': (
            'Learn how business automation helps small and medium businesses increase '
            'revenue and replace slow, outdated systems.'
        ),
        'meta_keywords': 'business automation SMB, automate business processes, SMB growth software',
    },
    {
        'title': 'AI in SMBs: Practical Ways to Use Artificial Intelligence Today',
        'slug': 'ai-in-smbs-practical-guide',
        'excerpt': (
            'AI is no longer only for large enterprises. Here is how small businesses '
            'can use AI-enabled software to work smarter right now.'
        ),
        'content': (
            'Artificial intelligence can help SMBs forecast demand, prioritise leads, '
            'spot anomalies in expenses, and answer routine customer questions—without '
            'hiring a data science team.\n\n'
            'The key is practical AI: features embedded inside the tools you already '
            'need (CRM, logistics, accounting), not separate science projects. '
            'SP-Tech Software Solution builds AI enablement into its products so you get smarter '
            'workflows from day one.\n\n'
            'Begin with clear goals—faster quotes, fewer stockouts, cleaner books—'
            'and choose platforms that deliver measurable results for your industry.'
        ),
        'tags': ['ai', 'smb'],
        'meta_title': 'AI in SMBs: A Practical Guide | SP-Tech Software Solution',
        'meta_description': (
            'Practical ways small and medium businesses can use AI-enabled software '
            'to improve operations and grow revenue.'
        ),
        'meta_keywords': 'AI for SMBs, artificial intelligence small business, AI software India',
    },
    {
        'title': 'Software Trends SMBs Should Watch in 2025',
        'slug': 'software-trends-smbs-2025',
        'excerpt': (
            'From cloud-first platforms to mobile access and AI, these software trends '
            'will shape how growing businesses compete this year.'
        ),
        'content': (
            'The gap between businesses on modern platforms and those stuck on old '
            'software is widening. In 2025, winning SMBs share a few habits: they run '
            'in the cloud, work from any device, and expect AI to assist—not replace—'
            'their teams.\n\n'
            'Other trends include tighter GST and compliance tooling, real-time '
            'operations dashboards, and after-sales support that keeps systems running. '
            'If your current stack is slow or desktop-only, it is time to plan a move.\n\n'
            'SP-Tech Software Solution helps SMBs make that transition with fast, AI-enabled products '
            'and on-call support so you stay productive after go-live.'
        ),
        'tags': ['software-trends', 'smb'],
        'meta_title': 'Software Trends for SMBs in 2025 | SP-Tech Software Solution',
        'meta_description': (
            'Key software trends for small and medium businesses in 2025—cloud, mobile, '
            'AI, and replacing outdated systems.'
        ),
        'meta_keywords': 'SMB software trends 2025, cloud software SMBs, business software India',
    },
]


class Command(BaseCommand):
    help = 'Populate the database with sample products, blog posts, and update the Site record.'

    def handle(self, *args, **kwargs):
        # Update the default site
        site, _ = Site.objects.get_or_create(pk=1)
        site.domain = 'sanjivani.com'
        site.name = 'SP-Tech Software Solution'
        site.save()
        self.stdout.write(self.style.SUCCESS('Site updated.'))

        # Category
        cat, _ = ProductCategory.objects.get_or_create(
            slug='enterprise-software',
            defaults={'name': 'Enterprise Software'}
        )

        for i, raw in enumerate(PRODUCTS):
            data = dict(raw)
            features = data.pop('features', [])
            order = data.pop('order', i)
            product, created = Product.objects.update_or_create(
                slug=data['slug'],
                defaults={**data, 'category': cat, 'order': order},
            )
            action = 'Created' if created else 'Updated'
            self.stdout.write(f'{action}: {product.name}')

            # Features
            product.features.all().delete()
            for i, (title, desc, icon) in enumerate(features):
                ProductFeature.objects.create(
                    product=product,
                    title=title,
                    description=desc,
                    icon_class=icon,
                    order=i,
                )

        # Sample blog posts for SEO
        User = get_user_model()
        author = User.objects.filter(is_superuser=True).first() or User.objects.first()
        for post_data in BLOG_POSTS:
            tag_slugs = post_data.pop('tags', [])
            post, created = Post.objects.update_or_create(
                slug=post_data['slug'],
                defaults={
                    **post_data,
                    'author': author,
                    'status': Post.STATUS_PUBLISHED,
                    'published_at': timezone.now(),
                },
            )
            tag_objs = []
            for slug in tag_slugs:
                tag, _ = Tag.objects.get_or_create(
                    slug=slug,
                    defaults={'name': slug.replace('-', ' ').title()},
                )
                tag_objs.append(tag)
            post.tags.set(tag_objs)
            self.stdout.write(f'{"Created" if created else "Updated"}: Blog – {post.title}')

        Product.objects.filter(slug='sanjivanione-erp').update(is_featured=True, order=0)
        Product.objects.exclude(slug='sanjivanione-erp').update(is_featured=False)

        self.stdout.write(self.style.SUCCESS('Sample data populated successfully!'))
