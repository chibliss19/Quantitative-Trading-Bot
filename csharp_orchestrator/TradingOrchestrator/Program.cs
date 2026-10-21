// using TradingOrchestrator.Services;

// var builder = WebApplication.CreateBuilder(args);

// builder.Services.AddHttpClient<PythonApiClient>();
// builder.Services.AddSingleton(new RiskManager(10000.00m)); // $10,000 Demo Account
// builder.Services.AddControllers();

// var app = builder.Build();

// var pythonClient = app.Services.GetRequiredService<PythonApiClient>();
// var riskManager = app.Services.GetRequiredService<RiskManager>();

// // Background worker simulation loop
// _ = Task.Run(async () =>
// {
//     while (true)
//     {
//         if (riskManager.IsKillSwitchTriggered)
//         {
//             Console.WriteLine("[System Halted] Kill switch is active. Waiting for manual reset.");
//             await Task.Delay(60000);
//             continue;
//         }

//         Console.WriteLine("\n[Orchestrator] Pinging Python engine for daily setup...");
//         var context = await pythonClient.GetMarketContextAsync("GBPUSD");

//         if (context != null)
//         {
//             Console.WriteLine($"[Data Received] Pair: {context.Pair} | NR4: {context.IsNr4} | Stretch: {context.StretchValue}");

//             if (context.IsNr4 || context.IsNr7)
//             {
//                 Console.WriteLine("[Setup Confirmed] Volatility compression detected. Calculating Turtle position size...");
                
//                 decimal entryPrice = context.PrevClose + context.StretchValue; 
//                 decimal stopLoss = context.PrevClose - context.StretchValue;   
                
//                 decimal lotSize = riskManager.CalculatePositionSize(entryPrice, stopLoss, 10m);
//                 Console.WriteLine($"[Execution Ready] Calculated Safe Lot Size (0.35% risk): {lotSize} lots.");
//             }
//             else
//             {
//                 Console.WriteLine("[Standby] No compression setup met today. Bot going back to sleep.");
//             }
//         }

//         // Wait before next loop check
//         await Task.Delay(15000); 
//     }
// });

// app.MapGet("/", () => "C# Trading Orchestrator is Running Safely.");
// app.Run();

// using TradingOrchestrator.Services;
// using TradingOrchestrator.Workers;

// var builder = WebApplication.CreateBuilder(args);

// builder.Services.AddHttpClient<PythonApiClient>();
// builder.Services.AddSingleton(new RiskManager(25000.00m)); // $25,000 Demo Account
// builder.Services.AddHostedService<TradingExecutionWorker>();
// builder.Services.AddControllers();

// var app = builder.Build();
// app.MapGet("/", () => "C# Trading Orchestrator & MT5 Local Bridge Active.");
// app.Run();

// var pythonClient = app.Services.GetRequiredService<PythonApiClient>();
// var riskManager = app.Services.GetRequiredService<RiskManager>();

// // Simulation state variables
// decimal simulatedLiveEquity = 10000.00m;
// int tradeCounter = 1;

// // Background worker simulation loop
// _ = Task.Run(async () =>
// {
//     while (true)
//     {
//         if (riskManager.IsKillSwitchTriggered)
//         {
//             Console.WriteLine("\n[SYSTEM HALTED] 2.0% Daily Prop-Firm Limit Reached. Kill Switch Active. System Locked.");
//             await Task.Delay(60000); 
//             continue;
//         }

//         Console.WriteLine($"\n--- Trade Loop #{tradeCounter} ---");
//         Console.WriteLine("[Orchestrator] Pinging Python engine for live CSV setup...");
        
//         var context = await pythonClient.GetMarketContextAsync("GBPUSD");

//         if (context != null && context.Status == "SUCCESS_LIVE_DATA")
//         {
//             Console.WriteLine($"[Data Received] Date: {context.Date} | Pair: {context.Pair} | NR4: {context.IsNr4}");

//             if (context.IsNr4 || context.IsNr7)
//             {
//                 Console.WriteLine("[Setup Confirmed] Live compression detected. Calculating Turtle position size...");
                
//                 decimal entryPrice = context.PrevClose + context.StretchValue; 
//                 decimal stopLoss = context.PrevClose - context.StretchValue;   
                
//                 decimal lotSize = riskManager.CalculatePositionSize(entryPrice, stopLoss, 10m, 0.0001m);
//                 Console.WriteLine($"[Execution] Calculated Safe Lot Size: {lotSize} lots.");
                
//                 // --- SIMULATING A LOSING TRADE ---
//                 Console.WriteLine("[Simulation] Executing Trade... MARKET REVERSED! Stop Loss Hit (-0.35%).");
//                 simulatedLiveEquity -= 35.00m; // Subtract strict $35 loss from the equity
                
//                 Console.WriteLine($"[Account] Equity dropping to: ${simulatedLiveEquity}");
//                 riskManager.UpdateEquity(simulatedLiveEquity);
                
//                 tradeCounter++;
//             }
//             else
//             {
//                 Console.WriteLine("[Standby] No compression setup met today. Bot going back to sleep.");
//             }
//         }
//         else
//         {
//             Console.WriteLine("[Error] Did not receive live data payload. Retrying...");
//         }

//         // Wait 3 seconds before the next iteration for fast testing
//         await Task.Delay(3000); 
//     }
// });

// app.MapGet("/", () => "C# Trading Orchestrator is Running Safely.");
// app.Run();#

// using Microsoft.AspNetCore.Builder;
// using Microsoft.Extensions.DependencyInjection;
// using Microsoft.Extensions.Hosting;
// using System;
// using System.Threading.Tasks;
// using TradingOrchestrator.Services;

// var builder = WebApplication.CreateBuilder(args);

// // Register dependencies
// builder.Services.AddHttpClient<PythonApiClient>();
// builder.Services.AddSingleton(new RiskManager(25000.00m)); // $25,000 Demo Account
// builder.Services.AddControllers();

// var app = builder.Build();

// app.MapGet("/", () => "C# Trading Orchestrator & MT5 Local Bridge Active.");

// // Launch background simulation loop asynchronously before app.Run()
// var scopeFactory = app.Services.GetRequiredService<IServiceScopeFactory>();

// _ = Task.Run(async () =>
// {
//     // Allow the web server a moment to spin up completely
//     await Task.Delay(2000);

//     using var scope = scopeFactory.CreateScope();
//     var pythonClient = scope.ServiceProvider.GetRequiredService<PythonApiClient>();
//     var riskManager = scope.ServiceProvider.GetRequiredService<RiskManager>();

//     decimal simulatedLiveEquity = 25000.00m;
//     int tradeCounter = 1;

//     while (true)
//     {
//         if (riskManager.IsKillSwitchTriggered)
//         {
//             Console.WriteLine("\n[SYSTEM HALTED] 2.0% Daily Prop-Firm Limit Reached. Kill Switch Active. System Locked.");
//             await Task.Delay(60000); 
//             continue;
//         }

//         Console.WriteLine($"\n--- Trade Loop #{tradeCounter} ---");
//         Console.WriteLine("[Orchestrator] Pinging Python FastAPI bridge for London Open context...");
        
//         var context = await pythonClient.GetMarketContextAsync("GBPUSD");

//         if (context != null && context.Status == "SUCCESS_LIVE_DATA")
//         {
//             Console.WriteLine($"[Data Received] Time: {context.TimestampIso} | Pair: {context.Pair} | London Open: {context.LondonOpenPrice}");

//             Console.WriteLine("[Setup Confirmed] London Open window active. Calculating ATR stretch position size...");
            
//             decimal entryPrice = context.BuyTrigger; 
//             decimal stopLoss = context.StopLoss;   
            
//             // Calculate lot size using your risk parameters
//             decimal lotSize = riskManager.CalculatePositionSize(entryPrice, stopLoss, 10m, 0.0001m);
//             Console.WriteLine($"[Execution] Calculated Safe Lot Size: {lotSize} lots.");
            
//             // --- SIMULATING A TEST ORDER EXECUTION ---
//             bool orderSuccess = await pythonClient.ExecuteOrderAsync(context.Pair, lotSize, entryPrice, stopLoss);
            
//             if (orderSuccess)
//             {
//                 Console.WriteLine("[Simulation] Pending Stop Order transmitted successfully to MT5 via Python bridge.");
//             }
            
//             tradeCounter++;
//         }
//         else
//         {
//             Console.WriteLine("[Standby] Waiting for 08:00 UTC London Open window or data unavailable. Retrying...");
//         }

//         // Wait 5 seconds before the next iteration
//         await Task.Delay(5000); 
//     }
// });

// // Start the web application cleanly
// app.Run();

using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using TradingOrchestrator.Services;
using TradingOrchestrator.Workers; // Ensures Program.cs can find your new worker

var builder = WebApplication.CreateBuilder(args);

// 1. Register Standard Dependencies
builder.Services.AddHttpClient<PythonApiClient>();
builder.Services.AddSingleton(new RiskManager(25000.00m)); 
builder.Services.AddControllers();

// 2. Register your continuous background loop worker
builder.Services.AddHostedService<TradingWorker>();

var app = builder.Build();

app.MapGet("/", () => "C# Trading Orchestrator & MT5 Local Bridge Active.");

// Run the application cleanly
app.Run();