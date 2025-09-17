from rest_framework import serializers
from .models import BacktestResult, Trade, DailyPortfolioSnapshot

class BacktestResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = BacktestResult
        fields = '__all__'

class TradeSerializer(serializers.ModelSerializer):
    profit = serializers.SerializerMethodField()
    is_open = serializers.SerializerMethodField()

    class Meta:
        model = Trade
        fields = '__all__'
    
    def get_profit(self, obj):
        return obj.get_profit()
    
    def get_is_open(self, obj):
        return obj.is_open()

class DailyPortfolioSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyPortfolioSnapshot
        fields = '__all__'

class BacktestCreateSerializer(serializers.Serializer):
    stock_symbol = serializers.CharField(max_length=10)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    short_period = serializers.IntegerField(default=20)
    long_period = serializers.IntegerField(default=50)
    stop_loss_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    take_profit_percentage = serializers.DecimalField(max_digits=5, decimal_places=2, default=50.00)
    starting_amount = serializers.DecimalField(max_digits=12, decimal_places=2, default=10000.00)