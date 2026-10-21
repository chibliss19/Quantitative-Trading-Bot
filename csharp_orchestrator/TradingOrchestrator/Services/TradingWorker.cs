using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.DependencyInjection;
using System;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using TradingOrchestrator.Services;

namespace TradingOrchestrator.Workers
{
    public class TradingWorker : BackgroundService
    {
        private readonly IServiceProvider _serviceProvider;

        public TradingWorker(IServiceProvider serviceProvider)
        {
            _serviceProvider = serviceProvider;
        }

        protected override async Task ExecuteAsync(CancellationToken stoppingToken)
        {
            // Allow the web server to boot fully before starting the loop
            await Task.Delay(2000, stoppingToken);

            int tradeCounter = 1;

            // Loop continues safely until the application shuts down
            while (!stoppingToken.IsCancellationRequested)
            {
                // Create a fresh scope for each iteration to resolve scoped HTTP Clients safely
                using var scope = _serviceProvider.CreateScope();
                var pythonClient = scope.ServiceProvider.GetRequiredService<PythonApiClient>();
                var riskManager = scope.ServiceProvider.GetRequiredService<RiskManager>();

                try
                {
                    if (riskManager.IsKillSwitchTriggered)
                    {
                        Console.WriteLine("\n[SYSTEM HALTED] Daily Prop-Firm Limit Reached. Kill Switch Active.");
                        await Task.Delay(60000, stoppingToken);
                        continue;
                    }

                    Console.WriteLine($"\n--- Trade Loop #{tradeCounter} ---");

                    // 1. Ping the Monitor Endpoint to detect manual/auto closures & push Telegram Alerts
                    await pythonClient.MonitorAccountAsync(); 

                    // 2. Poll for Market Context
                    Console.WriteLine("[Orchestrator] Pinging Python FastAPI bridge for London Open context...");
                    var context = await pythonClient.GetMarketContextAsync("GBPUSD");

                    if (context != null && context.Status == "SUCCESS_LIVE_DATA")
                    {
                        Console.WriteLine($"[Data Received] Time: {context.TimestampIso} | Pair: {context.Pair} | London Open: {context.LondonOpenPrice}");
                        Console.WriteLine("[Setup Confirmed] London Open window active. Calculating ATR stretch...");

                        decimal lotSize = riskManager.CalculatePositionSize(context.BuyTrigger, context.StopLoss, 10m, 0.0001m);
                        Console.WriteLine($"[Execution] Calculated Safe Lot Size: {lotSize} lots.");

                        // 3. Execute Order
                        bool orderSuccess = await pythonClient.ExecuteOrderAsync(context.Pair, lotSize, context.BuyTrigger, context.StopLoss);
                        
                        if (orderSuccess)
                            Console.WriteLine("[Execution Success] Pending Stop Order transmitted successfully.");
                        
                        tradeCounter++;
                    }
                    else
                    {
                        Console.WriteLine("[Standby] Waiting for 08:00 UTC London Open window or data unavailable.");
                    }
                }
                catch (HttpRequestException ex)
                {
                    // Prevents orchestrator crash if Python restarts or socket drops mid-request
                    Console.WriteLine($"[Network Error] FastAPI bridge offline or restarting. Retrying... ({ex.Message})");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[Critical Error] Unexpected exception in loop: {ex.Message}");
                }

                // Wait 5 seconds before next polling cycle
                await Task.Delay(5000, stoppingToken);
            }
        }
    }
}