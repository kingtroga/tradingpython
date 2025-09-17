from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'backtests', views.BacktestResultViewSet)
router.register(r'trades', views.TradeViewSet)
router.register(r'snapshots', views.DailyPortfolioSnapshotViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]