// using System.Net.Http.Json;
// using TradingOrchestrator.Models;

// namespace TradingOrchestrator.Services
// {
//     public class PythonApiClient
//     {
//         private readonly HttpClient _httpClient;

//         public PythonApiClient(HttpClient httpClient)
//         {
//             _httpClient = httpClient;
//             // Connects to your running local Python FastAPI engine
//             _httpClient.BaseAddress = new Uri("http://localhost:8000/");
//         }

//         public async Task<MarketContextDto?> GetMarketContextAsync(string pair)
//         {
//             try
//             {
//                 var response = await _httpClient.GetFromJsonAsync<MarketContextDto>($"api/market-context?pair={pair}");
//                 return response;
//             }
//             catch (Exception ex)
//             {
//                 Console.WriteLine($"[API Error] Failed to connect to Python engine: {ex.Message}");
//                 return null;
//             }
//         }
//     }
// }



using System;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

namespace TradingOrchestrator.Services
{
    public class PythonApiClient
    {
        private readonly HttpClient _httpClient;
        private readonly ILogger<PythonApiClient> _logger;

        public PythonApiClient(HttpClient httpClient, ILogger<PythonApiClient> logger)
        {
            _httpClient = httpClient;
            // Point directly to your local FastAPI bridge
            _httpClient.BaseAddress = new Uri("http://127.0.0.1:8000");
            _logger = logger;
        }

        public async Task<MarketContextDto?> GetMarketContextAsync(string pair = "GBPUSD")
        {
            try
            {
                var response = await _httpClient.GetAsync($"/api/v1/market-context?pair={pair}");
                if (response.IsSuccessStatusCode)
                {
                    return await response.Content.ReadFromJsonAsync<MarketContextDto>();
                }
                
                _logger.LogWarning("[API Warning] Failed to fetch market context. Status: {Status}", response.StatusCode);
                return null;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "[API Error] Network failure while pinging Python FastAPI bridge.");
                return null;
            }
        }

        public async Task<bool> ExecuteOrderAsync(string symbol, decimal volume, decimal price, decimal stopLoss)
        {
            try
            {
                var payload = new
                {
                    symbol = symbol,
                    volume = volume,
                    price = price,
                    sl = stopLoss
                };

                var response = await _httpClient.PostAsJsonAsync("/api/v1/execute-order", payload);
                if (response.IsSuccessStatusCode)
                {
                    var result = await response.Content.ReadFromJsonAsync<OrderExecutionResultDto>();
                    return result != null && result.Success;
                }

                _logger.LogWarning("[Broker Rejection] Order execution payload was rejected.");
                return false;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "[API Error] Failed to transmit order payload to local MT5 bridge.");
                return false;
            }
        }

        // --- NEW: Telemetry & Lifecycle Monitor ---
        public async Task MonitorAccountAsync()
        {
            try
            {
                // Pings Python FastAPI bridge to inspect MT5 deals and trigger trade closure alerts
                await _httpClient.GetAsync("/api/v1/monitor-account");
            }
            catch (Exception ex)
            {
                // Catch silently to avoid crashing the background worker on transient drops, 
                // but log it at a trace level for debugging if needed
                _logger.LogTrace(ex, "[Monitor] Transient failure reaching monitor endpoint.");
            }
        }
    }

    public class MarketContextDto
    {
        public string Status { get; set; } = string.Empty;
        public string Pair { get; set; } = string.Empty;
        public decimal LondonOpenPrice { get; set; }
        public decimal StretchValue { get; set; }
        public decimal BuyTrigger { get; set; }
        public decimal StopLoss { get; set; }
        public string TimestampIso { get; set; } = string.Empty;
    }

    public class OrderExecutionResultDto
    {
        public bool Success { get; set; }
        public ulong OrderTicket { get; set; }
        public decimal ExecutedPrice { get; set; }
        public decimal StopLoss { get; set; }
        public string Error { get; set; } = string.Empty;
    }
}