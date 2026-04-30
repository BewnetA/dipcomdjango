from decimal import Decimal

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from .models import (
    User,
    MarketingAgent,
    Customer,
    Sale,
    SaleItem,
    EditRequest,
    CommissionPayoutBatch,
    CommissionPayoutLine,
)


# ─────────────────────────────────────────────
# User
# ─────────────────────────────────────────────
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'name')
        read_only_fields = ('id', 'role')

    def validate_username(self, value):
        instance = getattr(self, 'instance', None)
        if instance and instance.username == value:
            return value  # No change
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'name', 'password')
        read_only_fields = ('id',)

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            name=validated_data.get('name', ''),
            role=validated_data.get('role', 'agent'),
        )


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True, write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


# ─────────────────────────────────────────────
# Marketing Agent
# ─────────────────────────────────────────────
class MarketingAgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingAgent
        fields = '__all__'
        read_only_fields = (
            'id',
            'created_at',
            'total_sales',
            'total_revenue',
            'customers_referred',
            'pending_commission_total',
        )


class CommissionPayoutLineSerializer(serializers.ModelSerializer):
    sale_id = serializers.IntegerField(source='sale.id', read_only=True)

    class Meta:
        model = CommissionPayoutLine
        fields = ('id', 'sale_id', 'commission_amount')
        read_only_fields = ('id', 'sale_id', 'commission_amount')


class CommissionPayoutBatchSerializer(serializers.ModelSerializer):
    lines = CommissionPayoutLineSerializer(many=True, read_only=True)

    class Meta:
        model = CommissionPayoutBatch
        fields = (
            'id',
            'marketing_agent',
            'agent_name',
            'created_at',
            'total_commission',
            'sale_count',
            'note',
            'lines',
        )
        read_only_fields = (
            'id',
            'marketing_agent',
            'agent_name',
            'created_at',
            'total_commission',
            'sale_count',
            'note',
            'lines',
        )


class CommissionPayoutBatchSummarySerializer(serializers.ModelSerializer):
    """List payout batches without nested lines (use detail for full audit)."""

    class Meta:
        model = CommissionPayoutBatch
        fields = (
            'id',
            'marketing_agent',
            'agent_name',
            'created_at',
            'total_commission',
            'sale_count',
            'note',
        )
        read_only_fields = (
            'id',
            'marketing_agent',
            'agent_name',
            'created_at',
            'total_commission',
            'sale_count',
            'note',
        )


# ─────────────────────────────────────────────
# Customer
# ─────────────────────────────────────────────
class CustomerSerializer(serializers.ModelSerializer):
    marketing_agent_name = serializers.CharField(source='marketing_agent.name', read_only=True)

    class Meta:
        model = Customer
        fields = '__all__'

class CustomerCreateSerializer(serializers.ModelSerializer):
    """Minimal payload used when creating a customer as part of a sale transaction."""
    class Meta:
        model = Customer
        fields = (
            'first_name', 'last_name', 'email', 'phone',
            'customer_type', 'company_name', 'position', 'business_type', 'address',
            'hear_about_us', 'marketing_agent', 'referred_by',
        )


# ─────────────────────────────────────────────
# EditRequest
# ─────────────────────────────────────────────
class EditRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = EditRequest
        fields = '__all__'
        read_only_fields = ('id', 'requested_at', 'resolved_at')


# ─────────────────────────────────────────────
# Sale Items
# ─────────────────────────────────────────────
class SaleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaleItem
        fields = ('id', 'category_name', 'model', 'condition', 'item_description', 'quantity', 'price', 'subtotal')

    def to_internal_value(self, data):
        # Strip leading zeros from numeric string inputs
        for field in ['quantity', 'price', 'subtotal']:
            if field in data and isinstance(data[field], str):
                data[field] = data[field].lstrip('0') or '0'
        return super().to_internal_value(data)


# ─────────────────────────────────────────────
# Sale (full)
# ─────────────────────────────────────────────
class SaleSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)
    customer_name = serializers.SerializerMethodField(read_only=True)
    edit_request = EditRequestSerializer(read_only=True)
    commission_paid = serializers.SerializerMethodField(read_only=True)
    customer_create = CustomerCreateSerializer(write_only=True, required=False)
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Sale
        fields = '__all__'
        read_only_fields = ('id', 'sale_date', 'agent', 'agent_name')
        extra_kwargs = {
            # allow create via customer_create, and compute money server-side
            'customer': {'required': False, 'allow_null': True},
            'total_amount_before_vat': {'required': False},
            'vat_amount': {'required': False},
            'total_amount': {'required': False},
            'number_of_products': {'required': False},
            'commission_rate': {'required': False},
            'commission_amount': {'required': False},
            'sales_person_name': {'required': False, 'allow_null': True},
        }

    def get_customer_name(self, obj):
        if obj.customer.customer_type == 'company' and obj.customer.company_name:
            return obj.customer.company_name
        return f"{obj.customer.first_name} {obj.customer.last_name}"

    def get_commission_paid(self, obj):
        v = getattr(obj, 'commission_paid', None)
        if v is not None:
            return bool(v)
        return CommissionPayoutLine.objects.filter(sale_id=obj.pk).exists()

    def validate_total_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Total amount cannot be negative.")
        return value

    def validate(self, attrs):
        # Create-only: updates (PATCH) may omit customer entirely.
        if self.instance is None:
            if not attrs.get('customer') and not attrs.get('customer_create'):
                raise serializers.ValidationError({'customer': 'Provide customer or customer_create.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        customer_create = validated_data.pop('customer_create', None)

        if customer_create is not None:
            customer = Customer.objects.create(**customer_create)
            validated_data['customer'] = customer

        customer = validated_data['customer']
        # Purchases already completed before this sale (repeat buyer = no commission / no attribution).
        is_repeat_buyer = customer.total_purchases >= 1

        # Always compute totals from line items (never trust client totals).
        total_before_vat = sum(Decimal(str(d.get('subtotal', 0))) for d in items_data)
        vat = (total_before_vat * Decimal('0.15'))
        validated_data['total_amount_before_vat'] = total_before_vat
        validated_data['vat_amount'] = vat
        validated_data['total_amount'] = total_before_vat + vat
        validated_data['number_of_products'] = sum(int(d.get('quantity', 0) or 0) for d in items_data)

        if is_repeat_buyer:
            validated_data['sales_person'] = None
            validated_data['commission_rate'] = Decimal('0')
            validated_data['commission_amount'] = Decimal('0')
            validated_data['sales_person_name'] = None
        else:
            sp = validated_data.get('sales_person')
            if sp:
                validated_data['sales_person_name'] = sp.name
                # Pull commission rate from DB (MarketingAgent.commission_rate)
                validated_data['commission_rate'] = Decimal(str(sp.commission_rate))
                validated_data['commission_amount'] = (total_before_vat * (validated_data['commission_rate'] / Decimal('100')))
            else:
                validated_data['sales_person_name'] = None
                validated_data['commission_rate'] = Decimal('0')
                validated_data['commission_amount'] = Decimal('0')

        sale = Sale.objects.create(**validated_data)

        for item_data in items_data:
            SaleItem.objects.create(sale=sale, **item_data)

        # Update customer stats only. Do not clear marketing_agent / hear_about_us on repeat
        # purchases — the first sale still references sales_person; clearing the customer FK
        # would hide historical attribution in admin UIs and is incorrect for audit.
        customer = sale.customer
        customer.total_purchases += 1
        customer.save()

        if sale.sales_person:
            sale.sales_person.recalculate_stats()

        return sale

    @transaction.atomic
    def update(self, instance, validated_data):
        old_sales_person_id = instance.sales_person_id
        items_data = validated_data.pop('items', None)

        # Recalculate totals from provided items
        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                SaleItem.objects.create(sale=instance, **item_data)

            total_before_vat = sum(d['subtotal'] for d in items_data)
            # Use Decimal for VAT rate (15/100 is a float and breaks Decimal * float on approve-edit).
            vat = total_before_vat * Decimal('0.15')
            validated_data['total_amount_before_vat'] = total_before_vat
            validated_data['vat_amount'] = vat
            validated_data['total_amount'] = total_before_vat + vat
            validated_data['number_of_products'] = sum(d['quantity'] for d in items_data)
            rate = Decimal(str(validated_data.get('commission_rate', instance.commission_rate)))
            validated_data['commission_rate'] = rate
            validated_data['commission_amount'] = total_before_vat * (rate / Decimal('100'))

        # Partial PATCH: commission rate only (no items) — keep totals, recompute commission.
        if items_data is None and 'commission_rate' in validated_data:
            rate = Decimal(str(validated_data['commission_rate']))
            validated_data['commission_amount'] = instance.total_amount_before_vat * (rate / Decimal('100'))

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Re-sync marketing-agent counters (unsettled sales only).
        sp_old, sp_new = old_sales_person_id, instance.sales_person_id
        if sp_old and sp_old != sp_new:
            prev = MarketingAgent.objects.filter(pk=sp_old).first()
            if prev:
                prev.recalculate_stats()
        if sp_new:
            instance.sales_person.recalculate_stats()

        return instance


# ─────────────────────────────────────────────
# Sale (lightweight list view)
# ─────────────────────────────────────────────
class SaleListSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField(read_only=True)
    edit_request = EditRequestSerializer(read_only=True)

    class Meta:
        model = Sale
        fields = (
            'id', 'customer', 'customer_name', 'agent_name',
            'total_amount', 'sales_type', 'payment_method',
            'status', 'sale_date', 'number_of_products',
            'edit_request',
        )

    def get_customer_name(self, obj):
        if obj.customer.customer_type == 'company' and obj.customer.company_name:
            return obj.customer.company_name
        return f"{obj.customer.first_name} {obj.customer.last_name}"
