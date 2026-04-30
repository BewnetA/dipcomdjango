from django.contrib import admin
from .models import User, MarketingAgent, Customer, Sale, SaleItem, EditRequest, CommissionPayoutBatch, CommissionPayoutLine

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'name', 'role', 'email', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'name', 'email')

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

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'agent_name', 'total_amount', 'sales_type', 'payment_method', 'status', 'sale_date')
    list_filter = ('status', 'sales_type', 'payment_method')
    search_fields = ('customer__first_name', 'customer__last_name', 'agent_name')
    inlines = [SaleItemInline]
    readonly_fields = ('sale_date',)

@admin.register(EditRequest)
class EditRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'requested_at', 'resolved_at')
    list_filter = ('status',)
