from decimal import Decimal

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import Sum
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('agent', 'Agent'),
        ('accountant', 'Accountant'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='agent')
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.username} ({self.role})"


class MarketingAgent(models.Model):
    name = models.CharField(max_length=255, unique=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=1.5)
    created_at = models.DateTimeField(auto_now_add=True)

    # Denormalized stats for **unsettled** sales only (not yet in a commission payout).
    # After an admin records a payout, settled sales drop out so totals reflect the next pay period.
    total_sales = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    customers_referred = models.PositiveIntegerField(default=0)
    pending_commission_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def __str__(self):
        return self.name

    def unsettled_sales(self):
        """Sales attributed to this marketing agent that are not yet marked paid (payout line)."""
        paid_ids = CommissionPayoutLine.objects.values_list('sale_id', flat=True)
        return self.sales.exclude(id__in=paid_ids)

    def recalculate_stats(self):
        """Recalculate denormalized counters from live unsettled sales only."""
        qs = self.unsettled_sales()
        self.total_sales = qs.count()
        agg = qs.aggregate(
            rev=Sum('total_amount'),
            comm=Sum('commission_amount'),
        )
        self.total_revenue = agg['rev'] or Decimal('0')
        self.pending_commission_total = agg['comm'] or Decimal('0')
        self.customers_referred = qs.values('customer_id').distinct().count()
        self.save(
            update_fields=(
                'total_sales',
                'total_revenue',
                'customers_referred',
                'pending_commission_total',
            ),
        )


class CommissionPayoutBatch(models.Model):
    """
    One admin action: \"paid this sales person for all currently unsettled attributed sales\".
    Lines link each settled sale for audit (no customer or sale row deletion).
    """
    marketing_agent = models.ForeignKey(
        MarketingAgent,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payout_batches',
    )
    agent_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    total_commission = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    sale_count = models.PositiveIntegerField(default=0)
    note = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payout {self.agent_name} @ {self.created_at:%Y-%m-%d} (${self.total_commission})"


class CommissionPayoutLine(models.Model):
    """Immutable audit row: this sale was included in a commission payout."""
    batch = models.ForeignKey(
        CommissionPayoutBatch,
        on_delete=models.CASCADE,
        related_name='lines',
    )
    sale = models.ForeignKey(
        'Sale',
        on_delete=models.PROTECT,
        related_name='commission_payout_lines',
    )
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('sale',), name='commission_payoutline_unique_sale'),
        ]

    def __str__(self):
        return f"PayoutLine batch={self.batch_id} sale={self.sale_id}"


class Customer(models.Model):
    CUSTOMER_TYPE_CHOICES = (
        ('individual', 'Individual'),
        ('company', 'Company'),
        ('government', 'Government'),
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, unique=True)
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPE_CHOICES, default='individual')
    company_name = models.CharField(max_length=255, blank=True, null=True)
    position = models.CharField(max_length=100, blank=True, null=True)
    business_type = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    # Marketing Attribution ("Connection With Us" / "Connection Through")
    hear_about_us = models.CharField(max_length=50, default='other')   # Connection Through (category)
    marketing_agent = models.ForeignKey(                                 # Connection Through (agent)
        MarketingAgent, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='referred_customers'
    )
    referred_by = models.CharField(max_length=255, blank=True, null=True)  # Connection With Us (free text)

    created_at = models.DateTimeField(auto_now_add=True)
    total_visits = models.PositiveIntegerField(default=0)
    total_purchases = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class EditRequest(models.Model):
    """Tracks accountant audit/correction requests on a sale."""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    details = models.TextField()
    requested_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"EditRequest [{self.status}] - {self.requested_at.date()}"


class Sale(models.Model):
    SALES_TYPE_CHOICES = (
        ('Direct', 'Direct'),
        ('RV', 'RV'),
    )
    STATUS_CHOICES = (
        ('completed', 'Completed'),
        ('pending', 'Pending'),
        ('cancelled', 'Cancelled'),
    )
    PAYMENT_CHOICES = (
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('transfer', 'Transfer'),
    )

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='sales')
    agent = models.ForeignKey(User, on_delete=models.PROTECT, related_name='sales_processed')
    agent_name = models.CharField(max_length=255)  # Snapshot of agent name at time of sale

    sold_by = models.CharField(max_length=255, default='DIPCOM Technologies')
    sales_person = models.ForeignKey(
        MarketingAgent, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sales'
    )
    sales_person_name = models.CharField(max_length=255, blank=True, null=True)  # Snapshot

    sales_type = models.CharField(max_length=20, choices=SALES_TYPE_CHOICES, default='Direct')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cash')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')

    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    total_amount_before_vat = models.DecimalField(max_digits=15, decimal_places=2)
    vat_amount = models.DecimalField(max_digits=15, decimal_places=2)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)

    number_of_products = models.PositiveIntegerField(default=0)
    sale_date = models.DateTimeField(auto_now_add=True)

    # Accountant Audit Request (one-to-one embedded)
    edit_request = models.OneToOneField(
        EditRequest, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sale'
    )

    def __str__(self):
        return f"Sale #{self.id} – {self.customer}"


class SaleItem(models.Model):
    CONDITION_CHOICES = (
        ('New', 'New'),
        ('Used', 'Used'),
    )
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    category_name = models.CharField(max_length=100)
    model = models.CharField(max_length=255)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='New')
    item_description = models.TextField(blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=15, decimal_places=2)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)

    def __str__(self):
        return f"{self.model} (×{self.quantity})"
