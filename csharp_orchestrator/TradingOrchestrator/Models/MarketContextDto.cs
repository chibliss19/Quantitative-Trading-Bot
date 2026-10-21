using System.Text.Json.Serialization;

namespace TradingOrchestrator.Models
{
    public class MarketContextDto
    {
        [JsonPropertyName("pair")]
        public string Pair { get; set; } = string.Empty;

        [JsonPropertyName("date")]
        public string Date { get; set; } = string.Empty;

        [JsonPropertyName("is_nr4")]
        public bool IsNr4 { get; set; }

        [JsonPropertyName("is_nr7")]
        public bool IsNr7 { get; set; }

        [JsonPropertyName("stretch_value")]
        public decimal StretchValue { get; set; }

        [JsonPropertyName("prev_close")]
        public decimal PrevClose { get; set; }

        [JsonPropertyName("status")]
        public string Status { get; set; } = string.Empty;
    }
}