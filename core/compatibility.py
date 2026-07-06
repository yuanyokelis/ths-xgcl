"""
Compatibility 层骨架（占位）。

在同花顺公式环境下，部分功能需要以 THS 公式实现；在 Python 层则使用近似算法或跳过。
"""

class CompatibilityPlaceholder:
    def __init__(self):
        self.winner_available = False
        self.cost_available = False
        self.finance_available = False

    def detect(self):
        # 检测逻辑在同花顺环境中实现
        self.winner_available = False
        self.cost_available = False
        self.finance_available = False

    def winner(self):
        if self.winner_available:
            raise NotImplementedError
        return None

    def cost(self):
        if self.cost_available:
            raise NotImplementedError
        return None

    def finance(self):
        if self.finance_available:
            raise NotImplementedError
        return None
