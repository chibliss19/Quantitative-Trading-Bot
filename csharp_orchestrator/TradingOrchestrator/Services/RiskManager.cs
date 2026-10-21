// namespace TradingOrchestrator.Services
// {
//     public class RiskManager
//     {
//         private readonly decimal _startingDailyBalance;
//         private decimal _currentAccountEquity;
//         private const decimal MaxDailyLossPercent = 2.0m; // Hard 2% Prop Firm Daily Kill-Switch Limit
//         private const decimal RiskPerTradePercent = 0.35m; // 0.35% Turtle Volatility Risk Cap
        
//         public bool IsKillSwitchTriggered { get; private set; } = false;

//         public RiskManager(decimal initialBalance)
//         {
//             _startingDailyBalance = initialBalance;
//             _currentAccountEquity = initialBalance;
//         }

//         public void UpdateEquity(decimal liveEquity)
//         {
//             _currentAccountEquity = liveEquity;
//             CheckDailyKillSwitch();
//         }

//         private void CheckDailyKillSwitch()
//         {
//             decimal dollarLoss = _startingDailyBalance - _currentAccountEquity;
//             decimal percentageLoss = (dollarLoss / _startingDailyBalance) * 100m;

//             if (percentageLoss >= MaxDailyLossPercent)
//             {
//                 IsKillSwitchTriggered = true;
//                 Console.WriteLine($"[CRITICAL ALERT] 2% Daily Loss Limit Breached ({percentageLoss:F2}%). KILL SWITCH ENGAGED. Flattening all positions.");
//             }
//         }

//         public decimal CalculatePositionSize(decimal entryPrice, decimal stopLossPrice, decimal pipValuePerStandardLot = 10m, decimal pipSize = 0.0001m)
// {
//     if (IsKillSwitchTriggered) return 0m;

//     decimal allowableRiskDollars = _currentAccountEquity * (RiskPerTradePercent / 100m); // $35 on $10k
//     decimal priceDistance = Math.Abs(entryPrice - stopLossPrice);

//     if (priceDistance == 0) return 0m;

//     // Convert raw price distance to pips (e.g., 0.0090 / 0.0001 = 90 pips)
//     decimal riskInPips = priceDistance / pipSize;

//     // Total dollar risk per 1.0 standard lot
//     decimal riskPerStandardLot = riskInPips * pipValuePerStandardLot;

//     // Calculate exact lot size
//     decimal lotSize = allowableRiskDollars / riskPerStandardLot;

//     // Return rounded to 2 decimal places (standard micro-lot precision)
//     return Math.Round(lotSize, 2);
// }
//     }
// }

using System;

namespace TradingOrchestrator.Services
{
    public class RiskManager
    {
        private readonly decimal _initialAccountBalance;
        private decimal _startingDailyBalance;
        private decimal _currentAccountEquity;
        
        // Prop Firm Rule Constants (FundingPips Standards)
        private const decimal MaxDailyLossPercent = 3.0m;      // Hard daily limit safety threshold
        private const decimal MaxOverallLossPercent = 5.0m;    // Overall trailing/static drawdown limit
        private const decimal MaxOpenRiskPercent = 1.0m;       // Max allowable open floating risk per trade/session
        private const decimal RiskPerTradePercent = 0.35m;     // Target Turtle Volatility Risk Cap per trade

        public bool IsKillSwitchTriggered { get; private set; } = false;
        public string KillSwitchReason { get; private set; } = string.Empty;

        public RiskManager(decimal initialBalance)
        {
            _initialAccountBalance = initialBalance;
            _startingDailyBalance = initialBalance;
            _currentAccountEquity = initialBalance;
        }

        /// <label>Updates equity dynamically to account for both closed balance and open floating PnL.</label>
        public void UpdateEquity(decimal liveEquity, decimal openingBalanceToday)
        {
            _startingDailyBalance = openingBalanceToday;
            _currentAccountEquity = liveEquity;
            EvaluateComplianceRules();
        }

        private void EvaluateComplianceRules()
        {
            // 1. Check Daily Loss Limit (Calculated from the higher of balance or equity reset)
            decimal dailyDollarLoss = _startingDailyBalance - _currentAccountEquity;
            decimal dailyPercentageLoss = (dailyDollarLoss / _startingDailyBalance) * 100m;

            if (dailyPercentageLoss >= MaxDailyLossPercent)
            {
                TriggerKillSwitch($"[BREACH PREvention] Max Daily Loss Limit reached ({dailyPercentageLoss:F2}% >= {MaxDailyLossPercent}%).");
                return;
            }

            // 2. Check Overall Account Drawdown Limit
            decimal totalDollarLoss = _initialAccountBalance - _currentAccountEquity;
            decimal totalPercentageLoss = (totalDollarLoss / _initialAccountBalance) * 100m;

            if (totalPercentageLoss >= MaxOverallLossPercent)
            {
                TriggerKillSwitch($"[BREACH PREVENTION] Max Overall Drawdown Limit reached ({totalPercentageLoss:F2}% >= {MaxOverallLossPercent}%).");
            }
        }

        private void TriggerKillSwitch(string reason)
        {
            IsKillSwitchTriggered = true;
            KillSwitchReason = reason;
            Console.WriteLine($"\n🚨 {reason} KILL SWITCH ENGAGED. System locked and flattening terminal.");
        }

        public decimal CalculatePositionSize(decimal entryPrice, decimal stopLossPrice, decimal pipValuePerStandardLot = 10m, decimal pipSize = 0.0001m)
        {
            if (IsKillSwitchTriggered)
            {
                Console.WriteLine("[BLOCKED] Position sizing denied: Risk Manager Kill Switch is active.");
                return 0m;
            }

            // Calculate allowable risk dollars based on fixed-fractional model
            decimal allowableRiskDollars = _currentAccountEquity * (RiskPerTradePercent / 100m);
            decimal priceDistance = Math.Abs(entryPrice - stopLossPrice);

            if (priceDistance == 0) return 0m;

            decimal riskInPips = priceDistance / pipSize;
            decimal riskPerStandardLot = riskInPips * pipValuePerStandardLot;

            if (riskPerStandardLot <= 0) return 0m;

            decimal lotSize = allowableRiskDollars / riskPerStandardLot;

            // Enforce FundingPips Max Open Risk constraint check (floating risk cannot exceed 1% of equity)
            decimal maxOpenRiskDollars = _currentAccountEquity * (MaxOpenRiskPercent / 100m);
            decimal calculatedTradeRiskDollars = lotSize * riskPerStandardLot;

            if (calculatedTradeRiskDollars > maxOpenRiskDollars)
            {
                Console.WriteLine("[WARNING] Calculated risk exceeds Max Open Risk rule. Scaling down lot size.");
                lotSize = maxOpenRiskDollars / riskPerStandardLot;
            }

            // Return rounded to micro-lot precision (2 decimal places)
            return Math.Round(lotSize, 2);
        }
    }
}