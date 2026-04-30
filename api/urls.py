from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    UserViewSet,
    MarketingAgentViewSet,
    CustomerViewSet,
    SaleViewSet,
    SalesExportDataView,
    InactiveCustomersDataView,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'marketing-agents', MarketingAgentViewSet, basename='marketingagent')
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'sales', SaleViewSet, basename='sale')

urlpatterns = [
    path('export-data/sales/', SalesExportDataView.as_view(), name='export-data-sales'),
    path('export-data/inactive-customers/', InactiveCustomersDataView.as_view(), name='export-data-inactive-customers'),

    # Explicit export endpoints (kept outside router for compatibility/reliability)
    path(
        'customers/inactive-export/',
        CustomerViewSet.as_view({'get': 'inactive_export'}),
        name='customer-inactive-export',
    ),
    path(
        'sales/export/',
        SaleViewSet.as_view({'get': 'export'}),
        name='sale-export',
    ),

    path('', include(router.urls)),

    # Authentication
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
