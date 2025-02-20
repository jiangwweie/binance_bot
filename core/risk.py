# 风险管理
from config.settings import Settings


class RiskManager:
    def __init__(self):
        self.total_capital = Settings.TOTAL_CAPITAL
        self.max_drawdown = 0.2  # 最大回撤20%

    def calculate_position(self, timeframe, confidence):
        """
        计算仓位参数
        :return: (position_size, leverage)
        """
        params = Settings.RISK_PARAMS.get(timeframe, {})

        # 基础仓位比例
        base_ratio = params.get('position_ratio', 0.01)
        # 根据置信度调整
        adjusted_ratio = base_ratio * (0.8 + confidence * 0.2)

        # 计算仓位金额
        position_size = self.total_capital * adjusted_ratio
        leverage = min(
            params.get('max_leverage', 3),
            int(3 * confidence)  # 置信度0.6对应1.8倍杠杆
        )

        return round(position_size, 2), leverage

    def check_dropdown(self, current_capital):
        """检查回撤是否超限"""
        draw_down = (self.total_capital - current_capital) / self.total_capital
        return draw_down > self.max_drawdown