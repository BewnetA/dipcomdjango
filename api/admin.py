from django.contrib import admin
from django.contrib import messages
from django.db import transaction
from .models import User, MarketingAgent, Customer, Sale, SaleItem, EditRequest, CommissionPayoutBatch, CommissionPayoutLine


def cleanup_and_delete_sales(queryset):
    sale_ids = list(queryset.values_list('id', flat=True))
    if not sale_ids:
        return 0, 0

    payout_lines = CommissionPayoutLine.objects.filter(sale_id__in=sale_ids)
    batch_ids = set(payout_lines.values_list('batch_id', flat=True))
    payout_line_count = payout_lines.count()
    payout_lines.delete()

    sale_count = queryset.count()
    queryset.delete()

    for batch in CommissionPayoutBatch.objects.filter(id__in=batch_ids):
        lines = batch.lines.all()
        if not lines.exists():
            batch.delete()
            continue

        batch.sale_count = lines.count()
        batch.total_commission = sum(line.commission_amount for line in lines)
        batch.save(update_fields=('sale_count', 'total_commission'))

    return sale_count, payout_line_count

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'name', 'role', 'email', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'name', 'email')
    actions = ('cleanup_delete_users_with_sales',)

    @admin.action(description='Cleanup delete selected users and their sales')
    def cleanup_delete_users_with_sales(self, request, queryset):
        protected_self = queryset.filter(pk=request.user.pk).exists()
        queryset = queryset.exclude(pk=request.user.pk)

        with transaction.atomic():
            sales = Sale.objects.filter(agent__in=queryset)
            sale_count, payout_line_count = cleanup_and_delete_sales(sales)
            user_count = queryset.count()
            queryset.delete()

        message = (
            f"Deleted {user_count} user(s), {sale_count} related sale(s), "
            f"and {payout_line_count} payout line(s)."
        )
        if protected_self:
            message += " Your own logged-in user was skipped."

        self.message_user(request, message, messages.WARNING)

@admin.register(MarketingAgent)
class MarketingAgentAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'commission_rate',
        'pending_commission_total',
        'total_sales',
        'total_revenue',
        'customers_referred',
    )
    search_fields = ('name',)


class CommissionPayoutLineInline(admin.TabularInline):
    model = CommissionPayoutLine
    extra = 0
    readonly_fields = ('sale', 'commission_amount')


@admin.register(CommissionPayoutBatch)
class CommissionPayoutBatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'agent_name', 'marketing_agent', 'total_commission', 'sale_count', 'created_at')
    list_filter = ('created_at',)
    inlines = [CommissionPayoutLineInline]
    readonly_fields = ('created_at',)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'phone', 'customer_type', 'total_purchases', 'created_at')
    list_filter = ('customer_type', 'hear_about_us')
    search_fields = ('phone', 'first_name', 'last_name', 'company_name')
    actions = ('cleanup_delete_customers_with_sales',)

    @admin.action(description='Cleanup delete selected customers and their sales')
    def cleanup_delete_customers_with_sales(self, request, queryset):
        with transaction.atomic():
            sales = Sale.objects.filter(customer__in=queryset)
            sale_count, payout_line_count = cleanup_and_delete_sales(sales)
            customer_count = queryset.count()
            queryset.delete()

        self.message_user(
            request,
            (
                f"Deleted {customer_count} customer(s), {sale_count} related sale(s), "
                f"and {payout_line_count} payout line(s)."
            ),
            messages.WARNING,
        )

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'agent_name', 'invoice_number', 'total_amount', 'sales_type', 'payment_method', 'status', 'sale_date')
    list_filter = ('status', 'sales_type', 'payment_method')
    search_fields = ('customer__first_name', 'customer__last_name', 'agent_name')
    inlines = [SaleItemInline]
    readonly_fields = ('sale_date',)
    actions = ('cleanup_delete_sales',)

    @admin.action(description='Cleanup delete selected sales, including payout links')
    def cleanup_delete_sales(self, request, queryset):
        with transaction.atomic():
            sale_count, payout_line_count = cleanup_and_delete_sales(queryset)

        self.message_user(
            request,
            f"Deleted {sale_count} sale(s) and {payout_line_count} payout line(s).",
            messages.WARNING,
        )


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'sale', 'category_name', 'model', 'condition', 'quantity', 'price', 'subtotal')
    list_filter = ('condition', 'category_name')
    search_fields = ('model', 'category_name', 'sale__invoice_number')


@admin.register(CommissionPayoutLine)
class CommissionPayoutLineAdmin(admin.ModelAdmin):
    list_display = ('id', 'batch', 'sale', 'commission_amount')
    search_fields = ('sale__invoice_number', 'sale__agent_name', 'batch__agent_name')

@admin.register(EditRequest)
class EditRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'requested_at', 'resolved_at')
    list_filter = ('status',)
